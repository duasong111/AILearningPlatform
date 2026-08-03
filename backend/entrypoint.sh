#!/bin/bash
set -e

ROLE="${1:-web}"

echo "Installing python dependencies..."
pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

echo "Waiting for db..."
sleep 2

if [ "$ROLE" = "web" ]; then
  echo "Running migrations..."
  python manage.py migrate --noinput

  echo "Starting daphne for ASGI/SSH support..."
  exec daphne -b 0.0.0.0 -p 8000 config.asgi:application
fi

if [ "$ROLE" = "celery" ]; then
  echo "Starting celery worker..."
  exec celery -A config worker -l info
fi

echo "Unknown role: $ROLE"
exit 1
