#!/bin/bash
set -e

# Start Celery worker in background for repository indexing & embeddings
celery -A app.core.celery worker --loglevel=info &
CELERY_PID=$!

# Start FastAPI Uvicorn web server in background
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} &
UVICORN_PID=$!

# Trap termination signals for graceful container shutdown
trap "kill -TERM $CELERY_PID $UVICORN_PID 2>/dev/null || true" SIGTERM SIGINT

wait -n $CELERY_PID $UVICORN_PID
