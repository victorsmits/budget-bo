# syntax=docker/dockerfile:1
FROM python:3.12-slim as base

WORKDIR /app

# Install system dependencies for Woob and PostgreSQL
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libxml2-dev \
    libxslt1-dev \
    libffi-dev \
    libssl-dev \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Configure Poetry
RUN poetry config virtualenvs.in-project true \
    && poetry config virtualenvs.create true

# Install dependencies (without root package to avoid README.md requirement)
RUN poetry install --no-interaction --no-ansi --no-root

# Initialize woob and install required modules
RUN poetry run pip install prettytable && \
    poetry run woob config modules cragr

# Development stage
FROM base as development

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    PATH="/app/.venv/bin:$PATH"

# Production stage
FROM base as production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    PATH="/app/.venv/bin:$PATH" \
    ENVIRONMENT=production

COPY ./app ./app
COPY ./worker ./worker
COPY ./scripts ./scripts

RUN poetry install --no-interaction --no-ansi --only main --no-root

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
