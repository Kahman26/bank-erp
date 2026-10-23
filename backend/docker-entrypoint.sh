#!/bin/sh
set -e
alembic upgrade head
python -m app.cli bootstrap
# Caddy — единственный, кто ходит в api, поэтому доверяем его X-Forwarded-For
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'
