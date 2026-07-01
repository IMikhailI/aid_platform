#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
until python - <<'PY'
import os, psycopg
try:
    psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "db"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    ).close()
    print("DB ready")
except Exception:
    raise SystemExit(1)
PY
do
  sleep 2
done

python manage.py migrate
python manage.py runserver 0.0.0.0:8000
