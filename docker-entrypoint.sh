#!/bin/bash
set -e

if [[ $DATABASE_URL =~ "postgres" ]]; then
    until psql $DATABASE_URL -c '\l'; do
        >&2 echo "Postgres is unavailable - sleeping"
        sleep 1
    done
    >&2 echo "Postgres is up - continuing"
fi

if [ "x$DJANGO_MANAGEPY_MIGRATE" = 'xon' ]; then
    uv run manage.py migrate --noinput
fi

exec docker-entrypoint.sh "$@"
