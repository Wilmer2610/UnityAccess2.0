#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
# Las migraciones se ejecutan en el startCommand para garantizar que
# la base de datos esté disponible en el entorno de ejecución.
