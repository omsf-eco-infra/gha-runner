FROM python:3.10-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1
ADD . /app
WORKDIR /app
RUN uv sync --locked # This installs the dependencies
CMD ["uv", "run", "src/gha_runner"]
