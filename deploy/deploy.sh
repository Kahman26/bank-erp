#!/usr/bin/env bash
# Выкладка собранных образов на сервер. Используется в GitHub Actions; можно запускать вручную
# после `docker compose build`.
#   DEPLOY_HOST=<ip> [DEPLOY_USER=deploy] [SSH_OPTS="-i key"] deploy/deploy.sh
set -euo pipefail

: "${DEPLOY_HOST:?set DEPLOY_HOST}"
DEPLOY_USER="${DEPLOY_USER:-deploy}"
SSH_OPTS="${SSH_OPTS:-}"
APP_DIR=/opt/bank-erp
TARGET="$DEPLOY_USER@$DEPLOY_HOST"
ARCHIVE="$(mktemp -d)/bank-erp-images.tar.gz"

docker save bank-erp-api:latest bank-erp-web:latest | gzip -1 > "$ARCHIVE"

# shellcheck disable=SC2086
scp $SSH_OPTS docker-compose.yml "$ARCHIVE" "$TARGET:$APP_DIR/"
# shellcheck disable=SC2086
ssh $SSH_OPTS "$TARGET" "set -e
  cd $APP_DIR
  gunzip -c bank-erp-images.tar.gz | docker load
  rm bank-erp-images.tar.gz
  docker compose up -d --remove-orphans
  docker image prune -f
  for i in \$(seq 1 30); do
    if curl -fsS http://localhost/api/health; then echo; echo deployed; exit 0; fi
    sleep 2
  done
  docker compose ps
  docker compose logs --tail=80 api
  exit 1"
