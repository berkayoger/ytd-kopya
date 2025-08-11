# --- Builder ---
FROM python:3.11-slim AS builder
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*
COPY backend/ /app/backend/
# Opsiyonel: kökte requirements varsa da kur
RUN python -m pip install --upgrade pip \
 && ( [ -f /app/backend/requirements.txt ] && pip wheel -r /app/backend/requirements.txt --wheel-dir /wheels || true ) \
 && pip wheel gunicorn flask flask-cors alembic psycopg2-binary --wheel-dir /wheels

# --- Runtime ---
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd -ms /bin/bash appuser
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*
COPY backend/ /app/backend/
ENV PORT=8000
EXPOSE 8000
# Günlükleri JSON benzeri tek satırda tutmak için basit arglar
ENV GUNICORN_CMD_ARGS="--bind 0.0.0.0:${PORT} --workers=${GUNICORN_WORKERS:-2} --threads=${GUNICORN_THREADS:-2} --access-logfile - --error-logfile - --timeout 120"
USER appuser
CMD ["bash", "-lc", "python -c 'import os,sys;print(\"APP_IMPORT_CANDIDATES=\",os.getenv(\"APP_IMPORT_CANDIDATES\"))' >/dev/null 2>&1; gunicorn wsgi:app"]
