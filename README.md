# Справочник банкоматов

Веб-приложение для учёта сети банкоматов банка: паспорта моделей, комплектация, узлы, подключения к процессингам, размещения на карте, ремонты, сертификаты, гарантии. Заменяет учёт в Excel.

Все данные в репозитории и на демо-стенде вымышленные.

Технический план — [docs/tech-plan.md](docs/tech-plan.md).

## Стек

- **backend** — Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16
- **frontend** — React 18, TypeScript, Vite, Ant Design, Leaflet
- **web** — Caddy: раздаёт фронтенд и проксирует `/api`

## Локальный запуск

```bash
cp .env.example .env            # задать пароли
docker compose up -d --build    # http://localhost
```

Разработка с горячей перезагрузкой:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d db   # Postgres на localhost:55432
cd backend
python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt
# в backend/.env: DATABASE_URL=postgresql+psycopg://<user>:<password>@localhost:55432/<db>
alembic upgrade head && python -m app.cli bootstrap
uvicorn app.main:app --reload    # API на :8000, документация /api/docs

cd ../frontend
npm install && npm run dev       # http://localhost:5173, /api проксируется на :8000
```

Тесты: `cd backend && pytest`, `cd frontend && npm run lint && npm run build`.

## Автодеплой

Каждый push в `main` проходит через GitHub Actions ([.github/workflows/ci-deploy.yml](.github/workflows/ci-deploy.yml)):

1. Тесты и линтеры бэкенда и фронтенда.
2. Сборка образов `bank-erp-api` и `bank-erp-web`.
3. Образы по SSH переносятся на сервер (`docker save | docker load`), затем `docker compose up -d` и проверка `/api/health`.

Сервер не обращается к GitHub, поэтому деплой продолжит работать и после перевода репозитория в приватный.

Секреты репозитория (Settings → Secrets and variables → Actions):

| Секрет | Значение |
|---|---|
| `DEPLOY_HOST` | IP сервера |
| `DEPLOY_USER` | `deploy` |
| `DEPLOY_SSH_KEY` | приватный ключ пользователя `deploy` |
| `DEPLOY_KNOWN_HOSTS` | вывод `ssh-keyscan <IP>` |

Пока секретов нет, шаг деплоя пропускается с предупреждением.

Подготовка нового сервера (Ubuntu 22.04, от root): `ssh root@<IP> 'bash -s' < deploy/server-setup.sh "<публичный ключ deploy>"`. Скрипт ставит Docker, создаёт пользователя `deploy`, включает firewall (22/80/443) и генерирует `/opt/bank-erp/.env` с паролями. Секреты хранятся только на сервере.
