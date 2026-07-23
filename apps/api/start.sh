#!/bin/bash
set -e

# Limit Celery concurrency to 2 worker processes to avoid memory exhaustion (OOM)
celery -A app.core.celery worker --loglevel=info --concurrency=2 &

# Exec Uvicorn as primary container process listening on Railway target port 8000
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
