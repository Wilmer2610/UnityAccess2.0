#!/usr/bin/env sh
set -o errexit
python manage.py migrate --noinput
if [ -n "${DJANGO_SUPERUSER_EMAIL:-}" ]; then
  if [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
    python manage.py reset_admin --username "${DJANGO_SUPERUSER_USERNAME:-admin}" --email "$DJANGO_SUPERUSER_EMAIL" --password "$DJANGO_SUPERUSER_PASSWORD"
  else
    python manage.py reset_admin --username "${DJANGO_SUPERUSER_USERNAME:-admin}" --email "$DJANGO_SUPERUSER_EMAIL"
  fi
fi
gunicorn unity.wsgi:application --bind "0.0.0.0:${PORT:-8000}"
