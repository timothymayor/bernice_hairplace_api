# syntax=docker/dockerfile:1.7
# One image, two roles:
#   API:    (default CMD) gunicorn with uvicorn workers on :8000
#   worker: arq app.workers.settings.WorkerSettings

FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project
COPY README.md ./
COPY app ./app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

FROM python:3.12-slim
RUN useradd --system --uid 10001 --no-create-home app \
    && mkdir -p /tmp/prometheus && chown app /tmp/prometheus
WORKDIR /app
COPY --from=build --chown=app /app/.venv /app/.venv
COPY --from=build --chown=app /app/app /app/app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus \
    WEB_CONCURRENCY=2
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4)"]
# gunicorn reads WEB_CONCURRENCY for the worker count. With a read-only root filesystem, mount
# /tmp as tmpfs (gunicorn heartbeat files and the Prometheus multiprocess dir live there).
CMD ["gunicorn", "app.main:create_app()", \
     "-c", "python:app.gunicorn_conf", \
     "-k", "uvicorn_worker.UvicornWorker", \
     "-b", "0.0.0.0:8000", \
     "--worker-tmp-dir", "/tmp", \
     "--graceful-timeout", "30", \
     "--timeout", "60", \
     "--keep-alive", "5", \
     "--forwarded-allow-ips", "*"]
