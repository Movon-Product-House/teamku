# Single stage, following uv's "Using uv in Docker" guide.
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"
WORKDIR /app

# Dependencies first, in their own layer: only rebuilt when uv.lock changes.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-install-project

COPY pyproject.toml uv.lock alembic.ini ./
COPY alembic ./alembic
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

USER nobody
EXPOSE 8000
# Prestart: migrate, seed the demo company on an empty database, then serve.
CMD ["sh", "-c", "alembic upgrade head && python -m movon_hr.seed --if-empty && uvicorn movon_hr.main:app --host 0.0.0.0 --port 8000"]
