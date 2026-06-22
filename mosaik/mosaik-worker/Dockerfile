FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim

WORKDIR /app

COPY mosaik/mosaik-worker/ ./

RUN uv sync --no-dev

CMD ["uv", "run", "python", "mosaik_worker.py"]