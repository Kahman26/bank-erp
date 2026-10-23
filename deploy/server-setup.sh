#!/usr/bin/env bash
# Подготовка чистого Ubuntu 22.04 под bank-erp. Запускать от root, повторный запуск безопасен.
#   ssh root@<host> 'bash -s' < deploy/server-setup.sh "<публичный ключ deploy>"
set -euo pipefail

APP_DIR=/opt/bank-erp
DEPLOY_USER=deploy
DEPLOY_PUBKEY="${1:?usage: server-setup.sh '<deploy public key>'}"

export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -y -q ca-certificates curl ufw openssl

if ! command -v docker >/dev/null; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -q
  apt-get install -y -q docker-ce docker-ce-cli containerd.io docker-compose-plugin
fi

# Логи контейнеров не должны съесть диск
cat > /etc/docker/daemon.json <<'EOF'
{"log-driver": "json-file", "log-opts": {"max-size": "10m", "max-file": "3"}}
EOF
systemctl restart docker

# Пользователь для деплоя: только ключ из GitHub Actions
id "$DEPLOY_USER" >/dev/null 2>&1 || useradd -m -s /bin/bash -G docker "$DEPLOY_USER"
install -d -m 700 -o "$DEPLOY_USER" -g "$DEPLOY_USER" "/home/$DEPLOY_USER/.ssh"
echo "$DEPLOY_PUBKEY" > "/home/$DEPLOY_USER/.ssh/authorized_keys"
chown "$DEPLOY_USER:$DEPLOY_USER" "/home/$DEPLOY_USER/.ssh/authorized_keys"
chmod 600 "/home/$DEPLOY_USER/.ssh/authorized_keys"

install -d -o "$DEPLOY_USER" -g "$DEPLOY_USER" "$APP_DIR"

# Секреты создаются один раз и живут только на сервере
if [ ! -f "$APP_DIR/.env" ]; then
  gen() { openssl rand -base64 64 | tr -dc 'A-Za-z0-9' | head -c "$1"; }
  cat > "$APP_DIR/.env" <<EOF
POSTGRES_DB=bank_erp
POSTGRES_USER=bank_erp
POSTGRES_PASSWORD=$(gen 32)
INITIAL_ADMIN_LOGIN=admin
INITIAL_ADMIN_PASSWORD=$(gen 16)
COOKIE_SECURE=false
EOF
  chown "$DEPLOY_USER:$DEPLOY_USER" "$APP_DIR/.env"
  chmod 600 "$APP_DIR/.env"
fi

ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "server ready"
