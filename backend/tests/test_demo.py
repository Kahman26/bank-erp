from pathlib import Path

from conftest import Client
from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Atm, AuditLog, DictItem, Role, User
from seed.generator import Generator
from seed.writer import ensure_base, id_allocator, reset_demo, write_db


def test_reset_demo_keeps_users_and_reference(login_as, tmp_path: Path) -> None:
    admin = login_as(Role.ADMIN)
    with SessionLocal() as db:
        write_db(db, Generator(ensure_base(db), id_allocator(db), 3).run(10))
        db.commit()
    atm_id = admin.get("/api/v1/atms").json()["items"][0]["id"]
    admin.put(f"/api/v1/atms/{atm_id}/contract", json={"service_sla_hours": 12})  # запись журнала о банкомате
    (tmp_path / "certificates").mkdir()
    (tmp_path / "certificates" / "1-old.pdf").write_bytes(b"%PDF")

    with SessionLocal() as db:
        dicts = db.scalar(select(func.count(DictItem.id)))
        reset_demo(db, tmp_path)
        db.commit()
        assert db.scalar(select(func.count(Atm.id))) == 0
        assert db.scalar(select(func.count(AuditLog.id)).where(AuditLog.atm_id.is_not(None))) == 0
        assert db.scalar(select(func.count(User.id))) == 1
        assert db.scalar(select(func.count(DictItem.id))) == dicts
        # после сброса генератор снова наполняет базу, id начинаются с 1
        write_db(db, Generator(ensure_base(db), id_allocator(db), 3).run(5))
        db.commit()
        assert db.scalar(select(func.min(Atm.id))) == 1
    assert not any((tmp_path / "certificates").iterdir())
    assert admin.get("/api/v1/auth/me").status_code == 200  # сессия администратора жива


def test_meta_is_public() -> None:
    r = Client().get("/api/v1/meta")
    assert r.status_code == 200 and "demo" in r.json()
