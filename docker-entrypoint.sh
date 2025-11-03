#!/usr/bin/env bash
set -e

# -------------------------------------------------
# Docker entrypoint for a Django project
# -------------------------------------------------

# Default values (can be overridden via env vars)
DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-wheel_analyzer.settings}
DJANGO_MANAGEPY=${DJANGO_MANAGEPY:-manage.py}
HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8000}
WORKERS=${WORKERS:-2}

# Helper: run a Django management command and exit on failure
run_manage() {
    uv run "$DJANGO_MANAGEPY" "$@"
}

# -------------------------------------------------
# 1. Wait for the database to become reachable
# -------------------------------------------------
if [ -n "$DATABASE_URL" ]; then
    echo "Waiting for database..."
    # Extract host and port from DATABASE_URL (expects postgres://user:pass@host:port/db)
    DB_HOST=$(echo "$DATABASE_URL" | sed -E 's|postgres://[^:]+:[^@]+@([^:]+):([0-9]+)/.*|\1|')
    DB_PORT=$(echo "$DATABASE_URL" | sed -E 's|postgres://[^:]+:[^@]+@([^:]+):([0-9]+)/.*|\2|')
    # Simple retry loop
    until nc -z "$DB_HOST" "$DB_PORT"; do
        echo "  → DB not ready at $DB_HOST:$DB_PORT, retrying in 2s..."
        sleep 2
    done
    echo "Database is reachable."
fi

# -------------------------------------------------
# 2. Apply migrations
# -------------------------------------------------
echo "Applying database migrations..."
run_manage migrate --noinput

# -------------------------------------------------
# 3. Collect static files (optional)
# -------------------------------------------------
if [ "$COLLECTSTATIC" = "1" ]; then
    echo "Collecting static files..."
    run_manage collectstatic --noinput
fi

# -------------------------------------------------
# 4. Create a superuser if credentials are provided
# -------------------------------------------------
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "Ensuring superuser exists..."
    uv run python <<EOF
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', '$DJANGO_SETTINGS_MODULE')
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
username = os.getenv('DJANGO_SUPERUSER_USERNAME')
email = os.getenv('DJANGO_SUPERUSER_EMAIL', '')
password = os.getenv('DJANGO_SUPERUSER_PASSWORD')
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"Superuser '{username}' created.")
else:
    print(f"Superuser '{username}' already exists.")
EOF
fi

# -------------------------------------------------
# 5. Execute the command passed to the container
# -------------------------------------------------
# If no command is provided, default to running uvicorn
if [ $# -eq 0 ]; then
    exec uv run uvicorn wheel_analyzer.asgi:application \
        --host 0.0.0.0 \
        --port 8000 \
        --workers 4 \
        --log-level info
else
    exec "$@"
fi
