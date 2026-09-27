# mrmkt engine image: runs `mrmkt engine start`.
#
# Build:  docker build -t mrmkt-engine .
# Run:    docker run --rm \
#           -v "$PWD/alpaca.yaml:/app/alpaca.yaml:ro" \
#           -v "$PWD/dbschema.yml:/app/dbschema.yml:ro" \
#           -e RABBITMQ_URL=amqp://mrmkt:mrmkt@rabbitmq:5672/ \
#           --network mrmkt_default \
#           mrmkt-engine
#
# alpaca.yaml / dbschema.yml are git-ignored locals: mount them, never bake them in.

FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Dependencies first for layer caching. NOTE: syncs the full lock (incl. dev
# group) because the runtime imports vectorbt at startup via
# composition -> backtest_run, and vectorbt currently lives in dev deps.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

# App source (+ README: hatchling uses it as the package readme).
COPY src/ ./src/
COPY README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

CMD ["mrmkt", "engine", "start"]
