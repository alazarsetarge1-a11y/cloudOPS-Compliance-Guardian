# syntax=docker/dockerfile:1

# ---- Stage 1: builder — install deps into an isolated venv we copy later ----
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# A venv keeps deps in one movable directory (/opt/venv) we lift into the runtime stage.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy ONLY requirements first → this slow pip-install layer caches and is reused
# unless requirements.txt itself changes. Code edits below won't bust it.
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
# (hardening step, later: swap to `pip install --require-hashes` once we generate
#  a hash-locked file, and run pip-audit in CI.)

# ---- Stage 2: runtime — slim, non-root, only what actually runs ----
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app

# Bring over the finished venv — no pip downloads, no build tools in the final image.
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
# The three sibling packages the backend imports (verified via grep):
COPY backend/app ./app
COPY detective ./detective
COPY corrective ./corrective

# Non-root: a container escape shouldn't start life as root.
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000

# Liveness on the no-AWS /health route. Uses python (already present) so we don't
# install curl into the slim image.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"

# uvicorn serves the ASGI app; 0.0.0.0 so it's reachable from outside the container.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
