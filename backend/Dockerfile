# syntax=docker/dockerfile:1
#
# Backend image for the Compliance-Cost Computer (CCC).
# Build context MUST be the repository root (requirements.txt lives there):
#   docker build -f backend/Dockerfile -t ccc-backend .
#
FROM python:3.12-slim

# Standard Python container hygiene.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install only what some wheels may need to build, then clean up.
# Most dependencies ship manylinux wheels, but build-essential keeps the
# build robust for any source-only package. curl is used by the healthcheck.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first for better layer caching.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend package.
COPY backend/ ./backend/

# Create a non-root user and a persistent data directory it owns.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /data \
    && chown -R appuser:appuser /data /app

ENV DB_PATH=/data/ccc.db \
    REGULATIONS_PATH=/data/regulations

USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:5000/health || exit 1

# Single worker by design (the workflow holds in-process state).
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "5000"]
