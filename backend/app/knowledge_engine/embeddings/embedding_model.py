"""Embedding model factory.

Builds a LlamaIndex ``BaseEmbedding`` for ``BAAI/bge-small-en-v1.5`` via
``FastEmbedEmbedding`` (ONNX Runtime), not PyTorch.

This replaced an earlier ``HuggingFaceEmbedding`` (sentence-transformers
+ torch) implementation after confirming in production (Render logs) that
it was exceeding a 512MB instance's memory limit and getting SIGKILLed by the
OS during model loading. The dominant memory cost there was PyTorch's own
import/runtime overhead (300-500MB+, independent of any model size)
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
    tier, and remains the only way to distinguish an OOM kill (a SIGKILL
    from the OS, uncatchable by any try/except) from a normal Python
    catchable failure after the fact: if this is the last line
    in the logs with nothing after it, that's the signature of the
    former, not the latter.
    """
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
        from llama_index.embeddings.fastembed import FastEmbedEmbedding

        model = FastEmbedEmbedding(
            model_name=settings.EMBEDDING_MODEL_NAME,
            threads=1,
            extra_session_options={
                "enable_cpu_mem_arena": False,
                "enable_mem_pattern": False,
            },
            # Cloud Run has 1 GiB available to this service. Start with a
            # conservative increase from the old Render-tuned value of 4
            # and measure production embedding latency before considering
            # a further increase.
            embed_batch_size=8,
        )
    except Exception:
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
