FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY unity/requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY unity/ /app/

RUN python manage.py collectstatic --noinput

EXPOSE 8000

RUN chmod +x /app/start.sh
CMD ["./start.sh"]
