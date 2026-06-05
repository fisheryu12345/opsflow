#!/bin/bash
# ============================================================
# OPSflow Docker Entrypoint
# ============================================================
# Supports two modes:
#   SERVICE_MODE=web     → Django ASGI server (default)
#   SERVICE_MODE=celery  → Celery worker
# ============================================================

set -e

# Wait for MySQL
echo "[Docker] Waiting for MySQL at ${DATABASE_HOST:-mysql}:${DATABASE_PORT:-3306} ..."
for i in $(seq 1 30); do
    if python -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('${DATABASE_HOST:-mysql}', ${DATABASE_PORT:-3306})); s.close()" 2>/dev/null; then
        echo "[Docker] MySQL is ready."
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "[Docker] Warning: MySQL not ready after 30s, continuing anyway..."
    fi
    sleep 2
done

# Wait for Redis
echo "[Docker] Waiting for Redis at ${REDIS_HOST:-redis}:${REDIS_PORT:-6379} ..."
for i in $(seq 1 15); do
    if python -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('${REDIS_HOST:-redis}', ${REDIS_PORT:-6379})); s.close()" 2>/dev/null; then
        echo "[Docker] Redis is ready."
        break
    fi
    sleep 1
done

# ---- Celery Worker Mode ----
if [ "${SERVICE_MODE}" = "celery" ]; then
    echo "[Docker] Starting Celery worker..."
    exec celery -A application worker -l info -c 4 --max-tasks-per-child=100
fi

# ---- Web Server Mode (default) ----

# Run migrations
echo "[Docker] Running database migrations..."
python manage.py migrate --noinput || echo "[Docker] Migrations failed (maybe first run, continuing...)"

# Initialize (creates admin user, etc.)
echo "[Docker] Initializing platform..."
python manage.py init -y || echo "[Docker] Init skipped or already done."

# Seed connector definitions
echo "[Docker] Seeding connector definitions..."
python manage.py seed_connector_definitions || echo "[Docker] Seed skipped."

# Collect static files
echo "[Docker] Collecting static files..."
python manage.py collectstatic --noinput || echo "[Docker] Collectstatic skipped."

# Start ASGI server
echo "[Docker] Starting ASGI server on 0.0.0.0:8000..."
exec uvicorn application.asgi:application \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level info \
    --proxy-headers \
    --forwarded-allow-ips '*'
