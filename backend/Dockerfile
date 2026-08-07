# syntax=docker/dockerfile:1

# --- Builder: install dependencies into a virtualenv --------------------
FROM python:3.12-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --upgrade pip

# No PyTorch-specific install step needed here anymore: the embedding
# model runs on fastembed (ONNX Runtime) instead of PyTorch/
# sentence-transformers as of the low-memory optimization for Render's
# 512MB instance tier -- see app/knowledge_engine/embeddings/
# embedding_model.py's docstring for the full story. This also means
# this Dockerfile no longer has any platform-specific wheel-availability
# concerns (the previous PyTorch step existed partly to sidestep
# PyTorch's lack of macOS x86_64/Intel wheels since 2.2.2 -- moot now
# that nothing in requirements.txt needs one).
RUN pip install -r requirements.txt

# --- Runtime: slim image, non-root user ----------------------------------
FROM python:3.12-slim AS runtime

RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

COPY --from=builder /opt/venv /opt/venv
COPY --chown=appuser:appuser . .

RUN chmod +x docker-entrypoint.sh

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
