#!/bin/bash

# Production startup script for Azerbaijan Legal RAG API

# Set environment variables
export TOKENIZERS_PARALLELISM=false
export PYTHONUNBUFFERED=1

# Check if running with multiple workers
WORKERS=${WORKERS:-4}
HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8000}

echo "Starting Azerbaijan Legal RAG API..."
echo "Workers: $WORKERS"
echo "Host: $HOST:$PORT"

# For production with multiple workers, use gunicorn with uvicorn workers
if [ "$WORKERS" -gt 1 ]; then
    echo "Running with gunicorn (multiple workers)..."
    exec gunicorn app.main:app \
        --workers $WORKERS \
        --worker-class uvicorn.workers.UvicornWorker \
        --bind $HOST:$PORT \
        --access-logfile - \
        --error-logfile - \
        --log-level info
else
    echo "Running with uvicorn (single worker)..."
    exec uvicorn app.main:app \
        --host $HOST \
        --port $PORT \
        --log-level info
fi 