"""Embedding model factory.

Builds a LlamaIndex ``BaseEmbedding`` for ``BAAI/bge-small-en-v1.5`` via
``FastEmbedEmbedding`` (ONNX Runtime), not PyTorch.

This replaced an earlier ``HuggingFaceEmbedding`` (sentence-transformers
+ torch) implementation after confirming in production (Render logs) that
it was exceeding a 512MB instance's memory limit and getting SIGKILLed by
the OS during model loading. The dominant memory cost there was PyTorch's
own import/runtime overhead (300-500MB+, independent of any model size)
-- not the embedding model itself, which was already one of the smaller
BGE variants. Swapping the runtime (ONNX Runtime instead of PyTorch)
while keeping the *same* model addresses that directly: confirmed via a
clean install that this pulls in only numpy + onnxruntime as its heavy
dependencies, with torch and sentence-transformers never imported at all
(checked ``sys.modules`` after import to confirm).

Same model, same 384-dim embedding space as before -- EMBEDDING_DIMENSION
in app/core/config.py is unchanged, so the existing Qdrant collection
needs no migration. The actual weights are a quantized ONNX export
(``qdrant/bge-small-en-v1.5-onnx-q``, ~67MB vs. the original ~130MB
float32 weights) rather than a different or smaller model -- see the
retrieval quality note below.

Downloading the model requires network access on first use (from
Hugging Face Hub, via fastembed's own download mechanism) -- where
that's unavailable (this sandbox included, and any CI environment
without external network), inject ``llama_index.core.embeddings.
MockEmbedding`` instead. Both implement the same ``BaseEmbedding``
interface, so nothing downstream (indexing, retrieval) needs to know or
care which one it got.

Retrieval quality trade-off: INT8 quantization (the "-q" in the source
model name above) typically causes a small reduction in embedding
precision compared to the original float32 weights -- in practice this
is usually a minor, often not perceptible difference in retrieval
quality for semantic search use cases like this one, not a different or
degraded model architecture. The realistic alternative on a 512MB
instance isn't "full precision vs. slightly reduced precision" -- it's
"slightly reduced precision that actually runs vs. full precision that
gets killed by the OS and indexes nothing at all."
"""

from __future__ import annotations

import resource

from llama_index.core.base.embeddings.base import BaseEmbedding

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _peak_rss_mb() -> float:
    """Peak resident set size of this process so far, in MB.

    Stdlib-only (no new dependency) diagnostic. Kept from the previous
    version of this module: even with the much lighter fastembed/ONNX
    Runtime stack, logging peak RSS around model loading is still the
    fastest way to confirm actual memory headroom on a given deployment
    tier, and remains the only way to distinguish an OOM kill (a
    SIGKILL from the OS, uncatchable by any try/except) from a normal
    Python-catchable failure after the fact: if this is the last line
    in the logs with nothing after it, that's the signature of the
    former, not the latter.
    """
    # ru_maxrss is KB on Linux, bytes on macOS -- this service only ever
    # runs on Linux (the Dockerfile's runtime is python:3.12-slim), so
    # no platform branching needed here.
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def build_embedding_model(settings: Settings) -> BaseEmbedding:
    """Build the real fastembed (ONNX Runtime) embedding model for production use.

    Downloads ``settings.EMBEDDING_MODEL_NAME`` on first use — requires
    network access.
    """
    logger.info(
        "Loading embedding model: %s (peak RSS before load: %.0f MB)",
        settings.EMBEDDING_MODEL_NAME,
        _peak_rss_mb(),
    )
    try:
        # Deliberately imported here, inside the try block, not at
        # module level or before this point -- an earlier version of
        # this function had the equivalent import before the
        # try/except, so an import-time failure (missing/corrupt
        # package, not just a runtime construction failure) would have
        # bypassed this logging entirely. Confirmed by testing at the
        # time: moving it fixed a real gap, not a hypothetical one.
        from llama_index.embeddings.fastembed import FastEmbedEmbedding

        model = FastEmbedEmbedding(model_name=settings.EMBEDDING_MODEL_NAME)
    except Exception:
        # This is the actual point of failure the original version of
        # this module (before either exception-handling pass) had zero
        # exception handling around -- and nothing calling it
        # (IndexingService.index_document's own try/except included)
        # can catch a failure here either, because this runs during
        # FastAPI dependency resolution, *before* that try/except block
        # even exists yet (see app/core/dependencies.py
        # get_indexing_service -> EmbedModelDep -> get_embed_model ->
        # this function, all resolved before the endpoint body runs).
        # logger.exception (not logger.error) is deliberate: it
        # includes the full traceback, not just the exception's string
        # message, which is what actually distinguishes "network error
        # downloading the model" from "corrupt cache" from "out of disk
        # space" etc. in the logs.
        logger.exception(
            "Failed to load embedding model %s (peak RSS at failure: %.0f MB). "
            "If nothing appears after this in the logs, the process was "
            "likely killed by the OS for exceeding its memory limit while "
            "loading this model -- Python cannot catch that (it's a "
            "SIGKILL, not an exception), so this log line is the last "
            "signal available. Check your deployment's memory limit "
            "against actual usage. Note: this stack no longer uses "
            "PyTorch (see this module's docstring) -- if you're still "
            "seeing this on a 512MB instance, the issue is something "
            "other than the embedding model load",
            settings.EMBEDDING_MODEL_NAME,
            _peak_rss_mb(),
        )
        raise

    logger.info(
        "Embedding model %s loaded (peak RSS after load: %.0f MB)",
        settings.EMBEDDING_MODEL_NAME,
        _peak_rss_mb(),
    )
    return model
