FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# шрифт с кириллицей для PDF-карточек
RUN apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
# CRLF из Windows-редакторов ломает shebang — нормализуем на всякий случай.
# /data/uploads — том для сканов документов, пишет в него пользователь app.
RUN sed -i "s/\r$//" docker-entrypoint.sh && chmod +x docker-entrypoint.sh \
    && useradd --system --uid 10001 app \
    && mkdir -p /data/uploads && chown app /data/uploads
USER app

EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
