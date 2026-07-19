FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc git libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY apps/api/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

RUN useradd --create-home --shell /bin/sh appuser
RUN mkdir -p /var/lib/codna/repositories && \
    chown -R appuser:appuser /var/lib/codna

COPY apps/api /app

USER appuser

CMD ["celery", "-A", "app.core.celery:celery_app", "worker", "--loglevel=INFO"]
