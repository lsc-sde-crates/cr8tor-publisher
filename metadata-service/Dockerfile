FROM python:3.12-slim

# Install Git (required for fetching cr8tor from Git repositories)
RUN apt-get update && apt-get install -y git

# Create a non-root user and group
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set the working directory
WORKDIR /home/appuser

# Change ownership of the application directory
RUN chown -R appuser:appuser /home/appuser

# Keyvault secrets are mounted at K8S pod level
ENV SECRETS_MNT_PATH="./secrets"

# Install uv
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#installing-uv
COPY --from=ghcr.io/astral-sh/uv:0.5.29 /uv /uvx /bin/

# Place executables in the environment at the front of the path
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#using-the-environment
ENV PATH="/home/appuser/.venv/bin:$PATH"

# Compile bytecode
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#compiling-bytecode
ENV UV_COMPILE_BYTECODE=1

# uv Cache
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#caching
ENV UV_LINK_MODE=copy

# ensures that the python output i.e. the stdout and stderr streams 
# are sent straight to terminal (e.g. your container log) without being first buffered
ENV PYTHONUNBUFFERED=1
 
ENV PYTHONPATH=/home/appuser

# Install dependencies
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#intermediate-layers
RUN --mount=type=cache,target=/home/appuser/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

COPY ./pyproject.toml ./uv.lock /home/appuser/

COPY ./app /home/appuser/app

# Sync the project
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#intermediate-layers
RUN --mount=type=cache,target=/home/appuser/.cache/uv \
    uv sync --frozen --no-dev

# Switch to the non-root user
USER appuser

EXPOSE 8002

CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "4"]