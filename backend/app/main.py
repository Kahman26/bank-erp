from fastapi import FastAPI
from sqlalchemy import text

from app.db import engine

app = FastAPI(title="Справочник банкоматов", docs_url="/api/docs", openapi_url="/api/openapi.json")


@app.get("/api/health")
def health() -> dict[str, str]:
    with engine.connect() as conn:
        conn.execute(text("select 1"))
    return {"status": "ok"}
