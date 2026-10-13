#!/bin/sh
set -e

if [ "$APP_MODE" = "api" ]; then
    ./scripts/generate_database.sh
    echo "Starting API server..."
    exec uvicorn main:app --host 0.0.0.0 --port 8000

elif [ "$APP_MODE" = "worker" ]; then
    echo "Starting worker..."
    CELERY_POOL="${CELERY_POOL:-prefork}"
    CELERY_CONCURRENCY="${CELERY_CONCURRENCY:-2}"
    exec celery -A app.queue.celery_app:celery_app worker \
        --pool="$CELERY_POOL" \
        --concurrency="$CELERY_CONCURRENCY" \
        --loglevel=INFO

else
    echo "Invalid APP_MODE: $APP_MODE. Use 'api' or 'worker'."
    exit 1
fi
