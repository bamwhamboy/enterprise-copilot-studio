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

# Install the CPU-only PyTorch build first, from PyTorch's own index,
# using the exact version pinned in requirements.txt (extracted here, not
# duplicated, so there's nothing to keep in sync manually). This container
# never has GPU access — no CUDA runtime, no device passthrough in
# docker-compose.yml — so the default PyPI Linux wheel (which bundles the
# full CUDA 12 runtime as ~2GB of nvidia-* packages) is pure waste here.
# Once this exact version is installed, the `pip install -r requirements.txt`
# below sees torch already satisfied and leaves it alone rather than
# pulling the CUDA build over it.
#
# Note: this Linux/CPU install path is *also* what makes this Dockerfile
# work at all on an Intel Mac host — PyTorch has not published macOS
# x86_64 (Intel) wheels since 2.2.2 (deprecated starting with the 2.3.0
# release; see https://github.com/pytorch/pytorch/issues/114602). Building
# inside this Linux container sidesteps that entirely: the host never
# installs torch itself, only Docker does.
RUN TORCH_VERSION=$(grep '^torch==' requirements.txt | sed 's/torch==//') \
    && pip install "torch==${TORCH_VERSION}" --index-url https://download.pytorch.org/whl/cpu

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

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
