#!/usr/bin/env bash
set -euo pipefail

# Basit smoke test: lokal ortamda gunicorn ile backend.wsgi:app'ı ayağa kaldırır,
# /healthz endpoint'ine tekrar tekrar istek atar.

PORT="${PORT:-8000}"
HOST="${HOST:-127.0.0.1}"
APP_IMPORT_CANDIDATES="${APP_IMPORT_CANDIDATES:-backend.app:create_app,backend.app:app,app:create_app,app:app}"
export APP_IMPORT_CANDIDATES

echo "==> Installing test deps (if any)"
python -m pip install --upgrade pip >/dev/null
if [ -f backend/requirements.txt ]; then pip install -r backend/requirements.txt; fi
# Sağlam olsun diye temel paketler:
pip install flask gunicorn >/dev/null

echo "==> Starting gunicorn on ${HOST}:${PORT}"
GUNICORN_CMD_ARGS="--bind ${HOST}:${PORT} --workers=2 --threads=2 --timeout 60 --access-logfile - --error-logfile -" \
  gunicorn backend.wsgi:app &
PID=$!
trap 'kill ${PID} || true' EXIT

echo "==> Probing /healthz"
ATTEMPTS=30
until curl -fsS "http://${HOST}:${PORT}/healthz" >/dev/null 2>&1; do
  ATTEMPTS=$((ATTEMPTS-1))
  if [ $ATTEMPTS -le 0 ]; then
    echo "!! service did not become healthy"
    echo "--- gunicorn recent logs ---"
    # Eğer journald yoksa en azından proses yaşıyor mu bak:
    ps -p ${PID} -o pid,cmd=
    exit 1
  fi
  echo "waiting healthz... attempts left: $ATTEMPTS"
  sleep 2
done
echo "✔ healthz OK"

curl -fsS "http://${HOST}:${PORT}/readiness" || true
kill ${PID} || true
wait || true
echo "✔ smoke test finished"
