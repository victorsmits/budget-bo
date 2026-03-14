# syntax=docker/dockerfile:1.7

FROM python:3.12-slim AS builder

WORKDIR /app

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=2.3.2 \
    POETRY_HOME=/opt/poetry \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

# Build-time dependencies only (not shipped in final image)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libxml2-dev \
        libxslt1-dev \
        libffi-dev \
        libssl-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --root-user-action=ignore "poetry==$POETRY_VERSION"

COPY pyproject.toml poetry.lock ./

RUN poetry install --only main --no-root

COPY ./scripts/setup_woob.py /app/scripts/setup_woob.py
RUN poetry run python /app/scripts/setup_woob.py

COPY ./app ./app
COPY ./worker ./worker
COPY ./scripts ./scripts
COPY ./alembic ./alembic
COPY ./alembic.ini ./alembic.ini

# Optional dev stage kept for docker-compose local usage
FROM builder AS development

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Ultra-light production runtime
FROM python:3.12-slim AS production

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production \
    PATH="/app/.venv/bin:$PATH"

# Runtime system libraries only
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        libxml2 \
        libxslt1.1 \
        libffi8 \
        libssl3 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 1001 appuser \
    && useradd --system --uid 1001 --gid 1001 --create-home appuser

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/app /app/app
COPY --from=builder /app/worker /app/worker
COPY --from=builder /app/scripts /app/scripts
COPY --from=builder /app/alembic /app/alembic
COPY --from=builder /app/alembic.ini /app/alembic.ini

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
