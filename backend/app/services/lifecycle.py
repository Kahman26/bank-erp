"""Операции жизненного цикла банкомата: статус, установка и перемещение, ремонты, узлы, ПО.

Каждая операция — одна транзакция с проверками бизнес-правил (tech-plan, раздел 4.2).
"""

from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Atm,
    AtmStatusHistory,
    Certificate,
    DictItem,
    Location,
    Module,
    ModuleReplacement,
    Placement,
    ServiceEvent,
    Software,
)

# Допустимые переходы между статусами (коды справочника). Статусы, которые администратор добавит сам,
# в таблице не описаны — для них переход разрешён в любую сторону.
TRANSITIONS: dict[str, set[str]] = {
    "in_stock": {"in_delivery", "installing", "on_farm", "to_writeoff"},
    "in_delivery": {"in_stock", "installing"},
    "installing": {"in_service", "in_stock"},
    "in_service": {"repair", "vendor_repair", "on_farm", "in_stock", "to_writeoff"},
    "repair": {"in_service", "vendor_repair", "to_writeoff"},
    "vendor_repair": {"in_service", "repair", "to_writeoff"},
    "on_farm": {"in_stock", "installing", "to_writeoff"},
    "to_writeoff": {"written_off", "in_stock"},
    "written_off": set(),
}
# в этих статусах банкомат стоит на месте
NEEDS_PLACE = {"installing", "in_service", "repair", "vendor_repair"}
# при переходе в эти статусы банкомат снимают с места
LEAVES_PLACE = {"in_stock", "in_delivery", "on_farm", "written_off"}


def _bad(msg: str) -> HTTPException:
    return HTTPException(status.HTTP_400_BAD_REQUEST, msg)


def allowed_statuses(db: Session, atm: Atm) -> list[int]:
    items = db.scalars(select(DictItem).where(DictItem.kind == "atm_status", DictItem.is_active)).all()
    current = atm.status.code
    if current not in TRANSITIONS:
        return [d.id for d in items if d.id != atm.status_id]
    return [d.id for d in items if d.code in TRANSITIONS[current] or d.code not in TRANSITIONS]


def current_placement(db: Session, atm_id: int) -> Placement | None:
    return db.scalar(select(Placement).where(Placement.atm_id == atm_id, Placement.placed_to.is_(None)))


def _record_status(db: Session, atm: Atm, status_id: int, user_id: int, comment: str | None, when: date) -> None:
    atm.status_id = status_id
    changed_at = datetime.combine(when, datetime.now().time(), tzinfo=UTC) if when != date.today() else None
    entry = AtmStatusHistory(atm_id=atm.id, status_id=status_id, changed_by_id=user_id, comment=comment)
    if changed_at:
        entry.changed_at = changed_at
    db.add(entry)


# --- статус --------------------------------------------------------------------------------------------------


class StatusChange(BaseModel):
    status_id: int
    comment: str | None = Field(default=None, max_length=1000)
    effective_date: date | None = None  # по умолчанию сегодня


def change_status(db: Session, atm: Atm, data: StatusChange, user_id: int) -> None:
    target = db.get(DictItem, data.status_id)
    if target is None or target.kind != "atm_status":
        raise _bad("Неизвестный статус")
    if target.id == atm.status_id:
        raise _bad("Банкомат уже в этом статусе")
    if target.id not in allowed_statuses(db, atm):
        raise _bad(f"Из статуса «{atm.status.name}» нельзя перейти в «{target.name}»")
    when = data.effective_date or date.today()
    if when > date.today():
        raise _bad("Дата смены статуса не может быть в будущем")

    place = current_placement(db, atm.id)
    if target.code in NEEDS_PLACE and place is None:
        raise _bad(f"Для статуса «{target.name}» сначала укажите место установки")
    if target.code in LEAVES_PLACE and place is not None:
        if when < place.placed_from:
            raise _bad("Дата раньше начала текущего размещения")
        place.placed_to = when
    if target.code == "in_service" and atm.commissioning_date is None:
        atm.commissioning_date = when
    if target.code == "written_off":
        atm.decommission_date = when
    _record_status(db, atm, target.id, user_id, data.comment, when)


# --- установка и перемещение ----------------------------------------------------------------------------------


class LocationIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    region_id: int
    city_district: str = Field(min_length=1, max_length=150)
    address: str = Field(min_length=1, max_length=300)
    landmark: str | None = Field(default=None, max_length=300)
    latitude: Decimal = Field(ge=37, le=46)
    longitude: Decimal = Field(ge=55, le=74)
    place_type_id: int
    indoor: bool = True
    access_type_id: int | None = None
    is_24h: bool = False
    working_hours: str = Field(min_length=1, max_length=200)
    premises_owner: str | None = Field(default=None, max_length=200)
    site_contact: str | None = Field(default=None, max_length=200)


class MoveIn(BaseModel):
    location: LocationIn
    placed_from: date
    move_reason_id: int | None = None
    basis_document: str | None = Field(default=None, max_length=200)
    # установить сразу в эксплуатацию (для нового банкомата со склада)
    set_status_id: int | None = None


def move(db: Session, atm: Atm, data: MoveIn, user_id: int) -> Placement:
    if atm.status.code == "written_off":
        raise _bad("Списанный банкомат нельзя установить")
    if data.placed_from > date.today():
        raise _bad("Дата установки не может быть в будущем")
    place = current_placement(db, atm.id)
    if place is not None:
        if data.placed_from <= place.placed_from:
            raise _bad(f"Дата перемещения должна быть позже начала текущего размещения ({place.placed_from:%d.%m.%Y})")
        place.placed_to = data.placed_from
    else:
        last = db.scalar(
            select(Placement.placed_to).where(Placement.atm_id == atm.id).order_by(Placement.placed_to.desc()).limit(1)
        )
        if last and data.placed_from < last:
            raise _bad(f"Дата установки раньше окончания прошлого размещения ({last:%d.%m.%Y})")
    db.flush()
    loc = Location(**data.location.model_dump())
    db.add(loc)
    db.flush()
    new = Placement(
        atm_id=atm.id,
        location_id=loc.id,
        placed_from=data.placed_from,
        move_reason_id=data.move_reason_id,
        basis_document=data.basis_document,
        created_by_id=user_id,
    )
    db.add(new)
    db.flush()
    if data.set_status_id and data.set_status_id != atm.status_id:
        change_status(
            db,
            atm,
            StatusChange(status_id=data.set_status_id, comment="Установка на место", effective_date=data.placed_from),
            user_id,
        )
    return new


# --- узлы и ПО ---------------------------------------------------------------------------------------------


class ModuleIn(BaseModel):
    module_type_id: int
    vendor: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    serial_number: str = Field(min_length=1, max_length=80)
    firmware_version: str | None = Field(default=None, max_length=50)
    installed_at: date | None = None
    attributes: dict = Field(default_factory=dict)


def add_module(db: Session, atm: Atm, data: ModuleIn) -> Module:
    mtype = db.get(DictItem, data.module_type_id)
    if mtype is None or mtype.kind != "module_type":
        raise _bad("Неизвестный тип узла")
    module = Module(
        atm_id=atm.id, **data.model_dump(exclude={"installed_at"}), installed_at=data.installed_at or date.today()
    )
    db.add(module)
    db.flush()
    return module


class SoftwareIn(BaseModel):
    software_type_id: int
    name: str = Field(min_length=1, max_length=100)
    version: str = Field(min_length=1, max_length=50)
    installed_at: date | None = None


def add_software(db: Session, atm: Atm, data: SoftwareIn) -> Software:
    """Каждое обновление — новая запись: так сохраняется история версий."""
    sw = Software(
        atm_id=atm.id, **data.model_dump(exclude={"installed_at"}), installed_at=data.installed_at or date.today()
    )
    db.add(sw)
    return sw


# --- ремонты ------------------------------------------------------------------------------------------------


class ReplacementIn(BaseModel):
    removed_module_id: int
    serial_number: str = Field(min_length=1, max_length=80)
    model: str | None = Field(default=None, max_length=100)
    vendor: str | None = Field(default=None, max_length=100)
    firmware_version: str | None = Field(default=None, max_length=50)


class ServiceEventIn(BaseModel):
    event_type_id: int
    started_at: datetime
    finished_at: datetime | None = None
    ticket_number: str | None = Field(default=None, max_length=80)
    problem: str = Field(min_length=1)
    work_done: str | None = None
    module_id: int | None = None  # неисправный узел
    vendor_id: int | None = None
    by_bank_engineer: bool = False
    cost: Decimal | None = Field(default=None, ge=0)
    cost_currency: str | None = None
    replacements: list[ReplacementIn] = Field(default_factory=list)
    # открыть ремонт и сразу перевести банкомат в «На ремонте» / «На ремонте у вендора»
    set_repair_status: bool = False

    @model_validator(mode="after")
    def _check(self) -> "ServiceEventIn":
        if self.vendor_id is None and not self.by_bank_engineer:
            raise ValueError("Укажите исполнителя: сервисного вендора или инженера банка")
        if self.finished_at and self.finished_at < self.started_at:
            raise ValueError("Окончание раньше начала")
        return self


def register_event(db: Session, atm: Atm, data: ServiceEventIn, user_id: int) -> ServiceEvent:
    now = datetime.now(UTC)
    if data.started_at > now:
        raise _bad("Начало не может быть в будущем")
    event = ServiceEvent(
        atm_id=atm.id,
        created_by_id=user_id,
        **data.model_dump(exclude={"replacements", "set_repair_status", "by_bank_engineer", "vendor_id"}),
        vendor_id=None if data.by_bank_engineer else data.vendor_id,
        by_bank_engineer=data.by_bank_engineer,
    )
    if data.module_id is not None:
        faulty = db.get(Module, data.module_id)
        if faulty is None or faulty.atm_id != atm.id:
            raise _bad("Неисправный узел не принадлежит этому банкомату")
    db.add(event)
    db.flush()

    day = data.started_at.date()
    for r in data.replacements:
        old = db.get(Module, r.removed_module_id)
        if old is None or old.atm_id != atm.id:
            raise _bad("Заменяемый узел не принадлежит этому банкомату")
        if old.removed_at is not None:
            raise _bad(f"Узел {old.serial_number} уже снят")
        if day < old.installed_at:
            raise _bad(f"Узел {old.serial_number} установлен {old.installed_at:%d.%m.%Y} — позже даты ремонта")
        old.removed_at = day
        old.is_faulty = True
        new = Module(
            atm_id=atm.id,
            module_type_id=old.module_type_id,
            vendor=r.vendor if r.vendor is not None else old.vendor,
            model=r.model if r.model is not None else old.model,
            serial_number=r.serial_number,
            firmware_version=r.firmware_version,
            installed_at=day,
            attributes=old.attributes,
        )
        db.add(new)
        db.flush()
        db.add(ModuleReplacement(event_id=event.id, removed_module_id=old.id, installed_module_id=new.id))
        if event.module_id is None:
            event.module_id = old.id
        mtype = db.get(DictItem, old.module_type_id)
        if mtype.extra.get("affects_certification"):
            # замена картридера, NFC-ридера или EPP: сертификаты снятого узла больше не подтверждают банкомат
            event.affects_certification = True
            for cert in db.scalars(select(Certificate).where(Certificate.module_id == old.id)):
                cert.needs_review = True

    if data.set_repair_status and data.finished_at is None:
        code = "repair" if data.by_bank_engineer else "vendor_repair"
        target = db.scalar(select(DictItem).where(DictItem.kind == "atm_status", DictItem.code == code))
        if target and target.id != atm.status_id:
            change_status(db, atm, StatusChange(status_id=target.id, comment=f"Ремонт: {data.problem}"), user_id)
    return event


class CloseEventIn(BaseModel):
    finished_at: datetime
    work_done: str | None = None
    cost: Decimal | None = Field(default=None, ge=0)
    cost_currency: str | None = None
    return_to_service: bool = False


def close_event(db: Session, atm: Atm, event: ServiceEvent, data: CloseEventIn, user_id: int) -> None:
    if event.finished_at is not None:
        raise _bad("Ремонт уже закрыт")
    if data.finished_at < event.started_at:
        raise _bad("Окончание раньше начала ремонта")
    if data.finished_at > datetime.now(UTC):
        raise _bad("Окончание не может быть в будущем")
    event.finished_at = data.finished_at
    if data.work_done:
        event.work_done = data.work_done
    if data.cost is not None:
        event.cost, event.cost_currency = data.cost, data.cost_currency
    if data.return_to_service and atm.status.code != "in_service":
        target = db.scalar(select(DictItem).where(DictItem.kind == "atm_status", DictItem.code == "in_service"))
        change_status(
            db,
            atm,
            StatusChange(status_id=target.id, comment="Ремонт завершён", effective_date=data.finished_at.date()),
            user_id,
        )
