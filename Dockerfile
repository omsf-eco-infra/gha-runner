FROM python:3.10-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1
ADD . /app
WORKDIR /app
RUN uv sync --frozen # This installs the dependencies
CMD ["uv", "run", "-m", "gha_runner"]
