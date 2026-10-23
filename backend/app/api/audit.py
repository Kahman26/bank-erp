"""Журнал изменений для суперадмина: кто, что и когда менял, входы в систему."""

from datetime import date, datetime, time, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import require
from app.auth.permissions import Perm
from app.db import get_db
from app.models import (
    Atm,
    AtmModel,
    AuditLog,
    Branch,
    DictItem,
    Manufacturer,
    PaymentScheme,
    Processing,
    Region,
    User,
    Vendor,
)

router = APIRouter(prefix="/audit", tags=["audit"])
superadmin = require(Perm.SUPERADMIN)

ENTITY_LABELS = {
    "atm": "Банкомат",
    "atm_model": "Модель",
    "module": "Узел",
    "software": "ПО",
    "atm_processing": "Процессинг",
    "location": "Место установки",
    "placement": "Размещение",
    "service_event": "Ремонт",
    "certificate": "Сертификат",
    "contract": "Договор",
    "dict_item": "Справочник",
    "branch": "Филиал",
    "vendor": "Вендор",
    "manufacturer": "Производитель",
    "app_user": "Пользователь",
    "auth": "Вход в систему",
}
ACTION_LABELS = {
    "create": "Создание",
    "update": "Изменение",
    "delete": "Удаление",
    "login": "Вход",
    "login_fail": "Неудачный вход",
    "lock": "Блокировка входа",
}
FIELD_LABELS = {
    "atm_code": "Код банкомата",
    "serial_number": "Серийный номер",
    "inventory_number": "Инвентарный номер",
    "model_id": "Модель",
    "device_type_id": "Тип устройства",
    "install_format_id": "Формат установки",
    "status_id": "Статус",
    "purchase_date": "Дата покупки",
    "commissioning_date": "Ввод в эксплуатацию",
    "decommission_date": "Вывод из эксплуатации",
    "branch_id": "Филиал",
    "notes": "Примечание",
    "screen_size_in": "Диагональ экрана",
    "screen_resolution": "Разрешение",
    "cassette_count": "Кассет",
    "contactless": "NFC",
    "atm_id": "Банкомат",
    "location_id": "Место",
    "placed_from": "Установлен с",
    "placed_to": "Снят",
    "move_reason_id": "Причина перемещения",
    "basis_document": "Основание",
    "module_type_id": "Тип узла",
    "installed_at": "Установлен",
    "removed_at": "Снят",
    "is_faulty": "Неисправен",
    "firmware_version": "Прошивка",
    "software_type_id": "Тип ПО",
    "version": "Версия",
    "name": "Название",
    "processing_id": "Процессинг",
    "terminal_id": "Terminal ID",
    "merchant_id": "Merchant ID",
    "ip_address": "IP-адрес",
    "event_type_id": "Тип события",
    "ticket_number": "Номер заявки",
    "started_at": "Начало",
    "finished_at": "Окончание",
    "problem": "Неисправность",
    "work_done": "Работы",
    "vendor_id": "Исполнитель",
    "by_bank_engineer": "Инженер банка",
    "cost": "Стоимость",
    "cert_type_id": "Вид сертификата",
    "payment_scheme_id": "Платёжная система",
    "cert_number": "Номер",
    "issued_at": "Выдан",
    "valid_until": "Действует до",
    "manual_status": "Ручной статус",
    "needs_review": "Требует проверки",
    "document_path": "Скан",
    "supplier_id": "Поставщик",
    "warranty_until": "Окончание гарантии",
    "service_vendor_id": "Сервисный вендор",
    "service_sla_hours": "SLA, ч",
    "purchase_price": "Стоимость покупки",
    "purchase_contract": "Договор поставки",
    "region_id": "Регион",
    "city_district": "Город / район",
    "address": "Адрес",
    "latitude": "Широта",
    "longitude": "Долгота",
    "place_type_id": "Тип места",
    "working_hours": "Режим работы",
    "login": "Логин",
    "full_name": "ФИО",
    "department": "Подразделение",
    "role": "Роль",
    "is_active": "Активен",
    "ip": "IP",
    "code": "Код",
    "sort": "Порядок",
    "manufacturer_id": "Производитель",
}
# поля-ссылки, которые показываем названием, а не числом
DICT_FIELDS = {
    "device_type_id",
    "install_format_id",
    "status_id",
    "move_reason_id",
    "module_type_id",
    "software_type_id",
    "event_type_id",
    "cert_type_id",
    "place_type_id",
    "source_id",
    "screen_orientation_id",
    "input_method_id",
    "safe_class_id",
    "safe_lock_id",
    "service_access_id",
    "host_protocol_id",
    "connection_type_id",
    "access_type_id",
}
HIDDEN = {"id"}


class AuditFilter(BaseModel):
    entity: list[str] = []
    action: list[str] = []
    user_id: int | None = None
    atm_id: int | None = None
    date_from: date | None = None
    date_to: date | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


class Change(BaseModel):
    field: str
    label: str
    old: Any = None
    new: Any = None


class AuditRow(BaseModel):
    id: int
    at: datetime
    user: str | None
    entity: str
    entity_label: str
    entity_id: int | None
    atm_id: int | None
    atm_code: str | None
    action: str
    action_label: str
    changes: list[Change]


class AuditPage(BaseModel):
    items: list[AuditRow]
    total: int


class _Names:
    """Подписи для id в журнале — загружаются один раз на запрос."""

    def __init__(self, db: Session) -> None:
        self.dicts = dict(db.execute(select(DictItem.id, DictItem.name)).all())
        self.maps = {
            "branch_id": dict(db.execute(select(Branch.id, Branch.name)).all()),
            "region_id": dict(db.execute(select(Region.id, Region.name)).all()),
            "vendor_id": dict(db.execute(select(Vendor.id, Vendor.name)).all()),
            "manufacturer_id": dict(db.execute(select(Manufacturer.id, Manufacturer.name)).all()),
            "payment_scheme_id": dict(db.execute(select(PaymentScheme.id, PaymentScheme.name)).all()),
            "processing_id": dict(db.execute(select(Processing.id, Processing.name)).all()),
            "model_id": dict(db.execute(select(AtmModel.id, AtmModel.model_name)).all()),
        }
        self.maps["supplier_id"] = self.maps["service_vendor_id"] = self.maps["vendor_id"]

    def value(self, field: str, v: Any) -> Any:
        if v is None or not isinstance(v, int) or isinstance(v, bool):
            return v
        if field in DICT_FIELDS:
            return self.dicts.get(v, v)
        if field in self.maps:
            return self.maps[field].get(v, v)
        return v


def _changes(row: AuditLog, names: _Names) -> list[Change]:
    out = []
    for field, value in (row.changes or {}).items():
        if field in HIDDEN or value in (None, "", [], {}) and row.action in ("create", "delete"):
            continue
        label = FIELD_LABELS.get(field, field)
        if row.action == "update" and isinstance(value, list) and len(value) == 2:
            out.append(
                Change(field=field, label=label, old=names.value(field, value[0]), new=names.value(field, value[1]))
            )
        elif row.action == "delete":
            out.append(Change(field=field, label=label, old=names.value(field, value)))
        else:
            out.append(Change(field=field, label=label, new=names.value(field, value)))
    return out


@router.get("", response_model=AuditPage)
def list_audit(
    f: Annotated[AuditFilter, Query()], db: Session = Depends(get_db), _: User = Depends(superadmin)
) -> AuditPage:
    conds = []
    if f.entity:
        conds.append(AuditLog.entity.in_(f.entity))
    if f.action:
        conds.append(AuditLog.action.in_(f.action))
    if f.user_id is not None:
        conds.append(AuditLog.user_id == f.user_id)
    if f.atm_id is not None:
        conds.append(AuditLog.atm_id == f.atm_id)
    if f.date_from:
        conds.append(AuditLog.at >= datetime.combine(f.date_from, time.min).astimezone())
    if f.date_to:
        conds.append(AuditLog.at < datetime.combine(f.date_to + timedelta(days=1), time.min).astimezone())

    total = db.scalar(select(func.count(AuditLog.id)).where(*conds)) or 0
    rows = db.execute(
        select(AuditLog, User.full_name, Atm.atm_code)
        .outerjoin(User, User.id == AuditLog.user_id)
        .outerjoin(Atm, Atm.id == AuditLog.atm_id)
        .where(*conds)
        .order_by(AuditLog.at.desc(), AuditLog.id.desc())
        .offset((f.page - 1) * f.page_size)
        .limit(f.page_size)
    ).all()
    names = _Names(db)
    items = [
        AuditRow(
            id=log.id,
            at=log.at,
            user=user_name,
            entity=log.entity,
            entity_label=ENTITY_LABELS.get(log.entity, log.entity),
            entity_id=log.entity_id,
            atm_id=log.atm_id,
            atm_code=atm_code,
            action=log.action,
            action_label=ACTION_LABELS.get(log.action, log.action),
            changes=_changes(log, names),
        )
        for log, user_name, atm_code in rows
    ]
    return AuditPage(items=items, total=total)


@router.get("/meta")
def meta(db: Session = Depends(get_db), _: User = Depends(superadmin)) -> dict:
    return {
        "entities": [{"value": k, "label": v} for k, v in ENTITY_LABELS.items()],
        "actions": [{"value": k, "label": v} for k, v in ACTION_LABELS.items()],
        "users": [
            {"value": i, "label": n} for i, n in db.execute(select(User.id, User.full_name).order_by(User.full_name))
        ],
    }
