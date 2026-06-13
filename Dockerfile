FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock alembic.ini README.md ./
COPY migrations ./migrations
COPY src ./src

RUN uv sync --frozen --no-dev

CMD ["uv", "run", "--no-sync", "health-observatory", "scheduler"]
