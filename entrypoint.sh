#!/bin/sh
set -e

# Only run migrations and collectstatic when starting the web server (gunicorn)
if [ "$1" = "gunicorn" ]; then
    echo "Running Django migrations..."
    python manage.py migrate --noinput

    echo "Collecting static files..."
    python manage.py collectstatic --noinput
fi

exec "$@"
