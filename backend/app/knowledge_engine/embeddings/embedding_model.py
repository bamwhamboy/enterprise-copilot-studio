"""Embedding model factory.

Builds a LlamaIndex ``BaseEmbedding`` for ``BAAI/bge-small-en-v1.5`` via
``HuggingFaceEmbedding``. Downloading the model weights requires network
access to huggingface.co — where that's unavailable (this sandbox
included, and any CI environment without external network), inject
``llama_index.core.embeddings.MockEmbedding`` instead. Both implement
the same ``BaseEmbedding`` interface, so nothing downstream (indexing,
retrieval) needs to know or care which one it got.
"""

from __future__ import annotations

import resource

from llama_index.core.base.embeddings.base import BaseEmbedding

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _peak_rss_mb() -> float:
    """Peak resident set size of this process so far, in MB.

    Stdlib-only (no new dependency) diagnostic for exactly the failure
    mode this module is most at risk of: torch + sentence-transformers
    loading this model is memory-intensive enough that on a
    memory-constrained deployment (e.g. Render's smaller instance
    tiers) it can trigger an out-of-memory kill -- which is a SIGKILL
    from the OS, not a Python exception, so it cannot be caught by any
    try/except here or anywhere else. Logging peak RSS immediately
    before the load is what makes that distinguishable after the fact:
    if this line is the last thing in the logs with nothing after it
    (no error, no traceback), that silence plus a peak RSS close to the
    deployment's memory limit is the signature of an OOM kill, not a
    normal Python-catchable failure.
    """
    # ru_maxrss is KB on Linux, bytes on macOS -- this service only ever
    # runs on Linux (the Dockerfile's runtime is python:3.12-slim), so
    # no platform branching needed here.
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def build_embedding_model(settings: Settings) -> BaseEmbedding:
    """Build the real HuggingFace embedding model for production use.

    Downloads ``settings.EMBEDDING_MODEL_NAME`` on first use — requires
    network access to huggingface.co.
    """
    logger.info(
        "Loading embedding model: %s (peak RSS before load: %.0f MB)",
        settings.EMBEDDING_MODEL_NAME,
        _peak_rss_mb(),
    )
    try:
        # Deliberately imported here, inside the try block, not at
        # module level or before this point -- an earlier version of
        # this function had the import before the try/except, so an
        # import-time failure (missing/corrupt package, not just a
        # runtime construction failure) would have bypassed this
        # logging entirely. Confirmed by testing: moving it fixed a
        # real gap, not a hypothetical one.
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding

        model = HuggingFaceEmbedding(model_name=settings.EMBEDDING_MODEL_NAME)
    except Exception:
        # This is the actual point of failure the previous version of
        # this module had zero exception handling around -- and
        # nothing calling it (IndexingService.index_document's own
        # try/except included) can catch a failure here either, because
        # this runs during FastAPI dependency resolution, *before* that
        # try/except block even exists yet (see app/core/dependencies.py
        # get_indexing_service -> EmbedModelDep -> get_embed_model ->
        # this function, all resolved before the endpoint body runs).
        # logger.exception (not logger.error) is deliberate: it includes
        # the full traceback, not just the exception's string message,
        # which is what actually distinguishes "network error
        # downloading from huggingface.co" from "corrupt cache" from
        # "out of disk space" etc. in the logs.
        logger.exception(
            "Failed to load embedding model %s (peak RSS at failure: %.0f MB). "
            "If nothing appears after this in the logs, the process was "
            "likely killed by the OS for exceeding its memory limit while "
            "loading torch + this model -- Python cannot catch that "
            "(it's a SIGKILL, not an exception), so this log line is the "
            "last signal available. Check your deployment's memory limit "
            "against actual usage",
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
