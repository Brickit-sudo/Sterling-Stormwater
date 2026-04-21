#!/bin/sh
echo "Running Alembic migrations..."
alembic upgrade head || echo "Migration warning (continuing anyway)"
echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
