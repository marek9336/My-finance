#!/bin/sh
set -e

python /app/scripts/run_migrations.py
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
