FROM python:3.12-slim

# Set the working directory
WORKDIR /app/

# Keyvault secrets are mounted at K8S pod level
ENV KEYVAULT_SECRETS_MNT_PATH="./secrets"

ENV METADATA_CONTAINER_NAME="metadata"
ENV METADATA_CONTAINER_PORT="8002"
ENV PUBLISH_CONTAINER_NAME="publish-container"
ENV PUBLISH_CONTAINER_PORT="8003"

# Install uv
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#installing-uv
COPY --from=ghcr.io/astral-sh/uv:0.5.29 /uv /uvx /bin/

# Place executables in the environment at the front of the path
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#using-the-environment
ENV PATH="/app/.venv/bin:$PATH"

# Compile bytecode
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#compiling-bytecode
ENV UV_COMPILE_BYTECODE=1

# uv Cache
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#caching
ENV UV_LINK_MODE=copy

# ensures that the python output i.e. the stdout and stderr streams 
# are sent straight to terminal (e.g. your container log) without being first buffered
ENV PYTHONUNBUFFERED=1
 
ENV PYTHONPATH=/app

# Install dependencies
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#intermediate-layers
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

COPY ./pyproject.toml ./uv.lock /app/

COPY ./app /app/app

# Sync the project
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#intermediate-layers
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

EXPOSE 8000

CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]