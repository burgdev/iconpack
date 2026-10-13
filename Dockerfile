# Minimal headless export image: iconpilot CLI + its Python stack only.
# Deliberately excludes Node (svgo) and spreet — none of the current export
# targets need them, and the image stays small. If svgo-backed export lands,
# add it as a build-arg variant (see cartoload's mkgmap pattern) or a -full tag.
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src/ src/
RUN uv sync --no-dev --frozen && uv cache clean

FROM python:3.12-slim

COPY --from=builder /app/.venv /venv

ENV PATH="/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /pack
ENTRYPOINT ["iconpilot"]
CMD ["--help"]
