# Dev image. Phase 9 replaces this with a multi-stage, non-root, healthchecked prod image.
FROM python:3.12-slim

# Keep the venv OUTSIDE /app so the docker-compose volume mount never shadows it.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Layer 1: dependencies only — cached as long as pyproject.toml + uv.lock don't change.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# Layer 2: our code — this layer re-builds on every change, the one above stays cached.
COPY . .
RUN uv sync --frozen

ENV PATH="/opt/venv/bin:$PATH"

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
