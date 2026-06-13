#!/bin/sh
set -e

echo "Running database initialization..."
python scripts/init_db.py

echo "Starting analytics service..."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 3006
