from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app import audit as _audit_listener  # noqa: F401 — включает журнал изменений
from app.api import atm_models, atms, audit, auth, certificates, imports, lifecycle, reference, reports, users
from app.db import engine

app = FastAPI(title="Справочник банкоматов", docs_url="/api/docs", openapi_url="/api/openapi.json")

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


@app.middleware("http")
async def require_fetch_header(request: Request, call_next):
    """Защита от CSRF в дополнение к SameSite=Strict: изменяющие запросы шлёт только наш фронтенд."""
    if request.method in UNSAFE_METHODS and request.headers.get("x-requested-with") != "fetch":
        return JSONResponse({"detail": "Запрос отклонён"}, status_code=403)
    return await call_next(request)


@app.exception_handler(IntegrityError)
async def integrity_error(_: Request, exc: IntegrityError) -> JSONResponse:
    msg = str(exc.orig)
    if "violates foreign key" in msg:
        detail = "Запись используется в других данных — сначала уберите ссылки на неё"
    elif "duplicate key" in msg or "unique" in msg.lower():
        detail = "Такая запись уже существует"
    else:
        detail = "Данные не прошли проверку целостности"
    return JSONResponse({"detail": detail}, status_code=409)


@app.get("/api/health")
def health() -> dict[str, str]:
    with engine.connect() as conn:
        conn.execute(text("select 1"))
    return {"status": "ok"}


for module in (auth, users, reference, atm_models, atms, imports, lifecycle, certificates, reports, audit):
    app.include_router(module.router, prefix="/api/v1")
