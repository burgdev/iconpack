# Minimal runtime: iconpilot CLI + its Python stack (resvg, svgpathtools,
# imagehash all ship as wheels). For headless export runs and CI.
# Node (svgo) and spreet (SDF sprites) are not bundled yet — add a stage
# when those export paths land.
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src/ src/
RUN uv sync --no-dev --frozen && uv cache clean

FROM python:3.12-slim

COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH"
WORKDIR /pack
ENTRYPOINT ["iconpilot"]
CMD ["--help"]
