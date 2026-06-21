# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies separately to leverage Docker layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code.
COPY src/ ./src/
COPY sql/ ./sql/

ENV PYTHONPATH=/app/src

# Default command runs the CLI help text.
ENTRYPOINT ["python", "-m", "inventory"]
CMD ["--help"]
