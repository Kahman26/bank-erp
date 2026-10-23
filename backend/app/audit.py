"""Журнал изменений: кто, что и когда поменял. Пишется автоматически при flush."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import event, insert, inspect
from sqlalchemy.orm import Session

from app.models import (
    Atm,
    AtmModel,
    AtmProcessing,
    AuditLog,
    Branch,
    Certificate,
    Contract,
    DictItem,
    Location,
    Manufacturer,
    Module,
    Placement,
    ServiceEvent,
    Software,
    User,
    Vendor,
)

AUDITED = (
    Atm,
    AtmModel,
    AtmProcessing,
    Branch,
    Certificate,
    Contract,
    DictItem,
    Location,
    Manufacturer,
    Module,
    Placement,
    ServiceEvent,
    Software,
    User,
    Vendor,
)
SKIP = {
    "created_at",
    "updated_at",
    "password_hash",
    "failed_logins",
    "locked_until",
    "last_login_at",
    "must_change_password",
}


def _plain(value: Any) -> Any:
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, list | tuple):
        return [_plain(v) for v in value]
    return value


def _columns(obj: Any) -> list[str]:
    return [c.key for c in inspect(obj).mapper.column_attrs if c.key not in SKIP]


def _atm_id(session: Session, obj: Any) -> int | None:
    """Банкомат, к которому относится изменение: сам банкомат, его узел, ремонт, сертификат узла и т. п."""
    if isinstance(obj, Atm):
        return obj.id
    if atm_id := getattr(obj, "atm_id", None):
        return atm_id
    if module_id := getattr(obj, "module_id", None):
        with session.no_autoflush:
            module = session.get(Module, module_id)
        return module.atm_id if module else None
    return None


@event.listens_for(Session, "after_flush")
def _write_audit(session: Session, _ctx: Any) -> None:
    if session.info.get("skip_audit"):
        return
    user_id = session.info.get("user_id")
    rows: list[dict[str, Any]] = []
    for obj in session.new:
        if isinstance(obj, AUDITED):
            snap = {k: _plain(getattr(obj, k)) for k in _columns(obj)}
            rows.append(
                {
                    "entity": obj.__tablename__,
                    "entity_id": obj.id,
                    "action": "create",
                    "changes": snap,
                    "atm_id": _atm_id(session, obj),
                }
            )
    for obj in session.dirty:
        if not isinstance(obj, AUDITED) or not session.is_modified(obj, include_collections=False):
            continue
        state = inspect(obj)
        diff = {}
        for key in _columns(obj):
            hist = state.attrs[key].history
            if hist.has_changes():
                old = hist.deleted[0] if hist.deleted else None
                new = hist.added[0] if hist.added else None
                if old != new:
                    diff[key] = [_plain(old), _plain(new)]
        if diff:
            rows.append(
                {
                    "entity": obj.__tablename__,
                    "entity_id": obj.id,
                    "action": "update",
                    "changes": diff,
                    "atm_id": _atm_id(session, obj),
                }
            )
    for obj in session.deleted:
        if isinstance(obj, AUDITED):
            snap = {k: _plain(getattr(obj, k)) for k in _columns(obj)}
            rows.append(
                {
                    "entity": obj.__tablename__,
                    "entity_id": obj.id,
                    "action": "delete",
                    "changes": snap,
                    "atm_id": _atm_id(session, obj),
                }
            )
    if rows:
        for r in rows:
            r["user_id"] = user_id
        session.connection().execute(insert(AuditLog), rows)
