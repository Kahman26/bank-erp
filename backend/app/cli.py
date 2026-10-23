"""Служебные команды: python -m app.cli <команда>."""

import sys

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import audit  # noqa: F401 — включает журнал изменений
from app.auth.security import hash_password, password_problem
from app.config import settings
from app.db import SessionLocal
from app.models import Currency, DictItem, PaymentScheme, Processing, Region, Role, User
from app.reference_data import CURRENCIES, DICTS, PAYMENT_SCHEMES, PROCESSINGS, REGIONS


def load_reference(db: Session) -> None:
    """Добавляет недостающие значения; изменённые администратором не трогает."""
    existing = {(k, c) for k, c in db.execute(select(DictItem.kind, DictItem.code))}
    for kind, items in DICTS.items():
        for sort, (code, name, *extra) in enumerate(items):
            if (kind.value, code) not in existing:
                db.add(DictItem(kind=kind.value, code=code, name=name, sort=sort, extra=extra[0] if extra else {}))

    def add_missing(model, key: str, rows: list[dict]) -> None:
        have = set(db.scalars(select(getattr(model, key))))
        for row in rows:
            if row[key] not in have:
                db.add(model(**row))

    add_missing(
        Region,
        "code",
        [
            {"code": c, "name": n, "sort": i, "center_lat": lat, "center_lon": lon}
            for i, (c, n, lat, lon) in enumerate(REGIONS)
        ],
    )
    add_missing(Currency, "code", [{"code": c, "name": n, "sort": i} for i, (c, n) in enumerate(CURRENCIES)])
    add_missing(PaymentScheme, "code", [{"code": c, "name": n, "sort": i} for i, (c, n) in enumerate(PAYMENT_SCHEMES)])
    add_missing(Processing, "code", [{"code": c, "name": n, "sort": i} for i, (c, n) in enumerate(PROCESSINGS)])


def ensure_superadmin(db: Session) -> None:
    if db.scalar(select(func.count(User.id))):
        return
    password = settings.initial_admin_password
    if problem := password_problem(password):
        sys.exit(f"INITIAL_ADMIN_PASSWORD: {problem}")
    db.add(
        User(
            login=settings.initial_admin_login,
            full_name="Суперадминистратор",
            role=Role.SUPERADMIN,
            password_hash=hash_password(password),
        )
    )
    print(f"created superadmin '{settings.initial_admin_login}'")


def bootstrap() -> None:
    """Начальные данные, без которых система не работает. Идемпотентно."""
    with SessionLocal() as db:
        load_reference(db)
        ensure_superadmin(db)
        db.commit()


COMMANDS = {"bootstrap": bootstrap}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        sys.exit(f"usage: python -m app.cli [{'|'.join(COMMANDS)}]")
    COMMANDS[sys.argv[1]]()
