# syntax=docker/dockerfile:1

##############################################
# Base image shared by dev and prod stages
##############################################
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# curl is handy for container health checks
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first for better layer caching
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Copy the application source
COPY . .

EXPOSE 8000

##############################################
# Development: uvicorn with auto-reload
##############################################
FROM base AS dev

HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

##############################################
# Production: gunicorn managing uvicorn workers
##############################################
FROM base AS prod

HEALTHCHECK --interval=15s --timeout=3s --retries=5 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["gunicorn", "app.main:app", "--worker-class", "uvicorn.workers.UvicornWorker", "--workers", "4", "--bind", "0.0.0.0:8000", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]
