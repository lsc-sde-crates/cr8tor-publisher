FROM ghcr.io/astral-sh/uv AS uv
FROM mcr.microsoft.com/vscode/devcontainers/base:ubuntu

COPY --from=uv --chown=vscode: /uv /uvx /bin/ 

RUN apt-get update && \
    apt-get install -y libpq-dev postgresql-client
