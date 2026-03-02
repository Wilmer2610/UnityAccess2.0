#!/usr/bin/env sh
set -o errexit
python manage.py migrate --noinput
gunicorn unity.wsgi:application --bind 0.0.0.0:8000
