FROM ghcr.io/astral-sh/uv:debian-slim

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN uv python install 3.13

WORKDIR /app

COPY uv.lock pyproject.toml /app/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

ENV PYTHONPATH=/app

COPY ./api /app/api

RUN mkdir -p /app/data/raw /app/data/processed \
    && chmod -R 777 /app/data

CMD ["/app/.venv/bin/uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8220", "--reload"]