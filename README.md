# Unity Access - Organización del Proyecto

Este repositorio contiene:

- `unity/` → Proyecto Django principal (aplicación web Unity Access)
- `UnityAccess/` → Recursos estáticos y HTML independiente (no integrados en Django)

## Estructura del proyecto Django (`unity/`)

- `unity/manage.py` → Comandos de Django
- `unity/unity/` → Paquete del proyecto
  - `settings.py` → ÚNICO archivo de configuración activo
  - `urls.py`, `asgi.py`, `wsgi.py`
- `unity/appi/` → App principal
  - `models.py`, `views.py`, `forms.py`, `admin.py`, `urls.py`, `migrations/`
- `unity/templates/` → Plantillas
  - `base.html`, `registration/`, `appi/`, `usuarios/`, `control_qr/`, `accesos/`
- `unity/static/` → Archivos estáticos
  - `css/`, `imagen/`
- `unity/db.sqlite3` → Base de datos (desarrollo)

Configuración relevante en `unity/unity/settings.py`:

- `TEMPLATES['DIRS'] = [BASE_DIR / 'templates']`
- `STATIC_URL = 'static/'`
- `STATICFILES_DIRS = [BASE_DIR / 'static']`
- Autenticación: `LOGIN_URL = '/appi/login/'`, `LOGIN_REDIRECT_URL = '/appi/'`, `LOGOUT_REDIRECT_URL = '/appi/login/'`

## Limpiezas realizadas

- Eliminado `unity/settings.py` duplicado y no utilizado.
- Eliminada plantilla duplicada no referenciada `unity/templates/appi/login.html`.

## Recomendaciones de organización

- Mantener todos los recursos estáticos dentro de `unity/static/` (por ejemplo, imágenes en `imagen/`, estilos en `css/`, crear `js/` si se requiere).
- Mantener las plantillas dentro de `unity/templates/` utilizando subcarpetas por dominio (registro, usuarios, accesos, etc.).
- Si se desean integrar recursos de `UnityAccess/`, movelos a:
  - CSS → `unity/static/css/`
  - JS → `unity/static/js/` (crear si no existe)
  - Imágenes → `unity/static/imagen/`
  y referenciarlos con `{% load static %}` y `{% static '...' %}`.

## Cómo ejecutar en desarrollo

1. (Opcional) Activar el entorno virtual: `.venv\Scripts\activate`
2. Instalar dependencias: `pip install -r UnityAccess/requirements.txt` (si aplica) y las de Django.
3. Ejecutar servidor: `python unity/manage.py runserver`
4. Acceder a `http://127.0.0.1:8000/`

## Notas

- El módulo de configuración activo es `unity.unity.settings` (por `DJANGO_SETTINGS_MODULE = 'unity.settings'`).
- Si se renombra la estructura, ajustar `manage.py`, `asgi.py`, `wsgi.py` y `ROOT_URLCONF`.