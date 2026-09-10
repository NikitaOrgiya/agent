#!/bin/sh
# Apply DB migrations, then start the API. Schema is never changed by the app
# process itself.
set -e

echo "[entrypoint] running alembic migrations..."
alembic upgrade head

echo "[entrypoint] starting kernel..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8080
