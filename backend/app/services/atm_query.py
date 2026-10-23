"""Выборка банкоматов с фильтрами — общая для списка, карты и (позже) выгрузки в Excel."""

from datetime import date, datetime, timedelta
from typing import Annotated, Literal

from fastapi import Query
from pydantic import BaseModel, Field
from sqlalchemy import Select, and_, exists, func, literal, or_, select, union
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.orm import aliased

from app.models import (
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
    Processing,
    Region,
    ServiceEvent,
    atm_currency,
)


class AtmFilter(BaseModel):
    q: str | None = None
    region_id: list[int] = []
    branch_id: list[int] = []
    status_id: list[int] = []
    manufacturer_id: list[int] = []
    model_id: list[int] = []
    device_type_id: list[int] = []
    install_format_id: list[int] = []
    place_type_id: list[int] = []
    processing_id: list[int] = []
    vendor_id: list[int] = []
    currency: list[str] = []
    contactless: bool | None = None
    cash_in: bool | None = None
    is_24h: bool | None = None
    has_location: bool | None = None
    warranty_expiring_days: int | None = Field(default=None, ge=0, le=3650)
    cert_expiring_days: int | None = Field(default=None, ge=0, le=3650)
    repair_over_days: int | None = Field(default=None, ge=0, le=3650)


SortKey = Literal["atm_code", "status", "region", "model", "branch", "commissioning_date", "warranty_until"]


class AtmListParams(AtmFilter):
    sort: SortKey = "atm_code"
    order: Literal["asc", "desc"] = "asc"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)


FilterQuery = Annotated[AtmFilter, Query()]
ListQuery = Annotated[AtmListParams, Query()]

Status = aliased(DictItem, name="status")
DeviceType = aliased(DictItem, name="device_type")
PlaceType = aliased(DictItem, name="place_type")
Current = aliased(Placement, name="current")

# регион банкомата — по текущему месту, а если места нет (склад, списан) — по филиалу
REGION_ID = func.coalesce(Location.region_id, Branch.region_id)


def own_terminal_id():
    return (
        select(AtmProcessing.terminal_id)
        .join(Processing, Processing.id == AtmProcessing.processing_id)
        .where(AtmProcessing.atm_id == Atm.id, Processing.code == "own")
        .scalar_subquery()
    )


def currencies_agg():
    return (
        select(
            func.string_agg(
                atm_currency.c.currency_code, aggregate_order_by(literal(", "), atm_currency.c.currency_code)
            )
        )
        .where(atm_currency.c.atm_id == Atm.id)
        .scalar_subquery()
    )


def base_select(*columns) -> Select:
    return (
        select(*columns)
        .select_from(Atm)
        .join(AtmModel, AtmModel.id == Atm.model_id)
        .join(Manufacturer, Manufacturer.id == AtmModel.manufacturer_id)
        .join(Status, Status.id == Atm.status_id)
        .join(DeviceType, DeviceType.id == Atm.device_type_id)
        .join(Branch, Branch.id == Atm.branch_id)
        .outerjoin(Current, and_(Current.atm_id == Atm.id, Current.placed_to.is_(None)))
        .outerjoin(Location, Location.id == Current.location_id)
        .outerjoin(PlaceType, PlaceType.id == Location.place_type_id)
        .join(Region, Region.id == REGION_ID)
        .outerjoin(Contract, Contract.atm_id == Atm.id)
    )


def apply_filters(stmt: Select, f: AtmFilter) -> Select:
    conds = []
    if f.q and f.q.strip():
        like = f"%{f.q.strip()}%"
        conds.append(
            or_(
                Atm.atm_code.ilike(like),
                Atm.serial_number.ilike(like),
                Atm.inventory_number.ilike(like),
                Location.address.ilike(like),
                Location.name.ilike(like),
                Location.city_district.ilike(like),
                exists().where(
                    AtmProcessing.atm_id == Atm.id,
                    or_(AtmProcessing.terminal_id.ilike(like), AtmProcessing.merchant_id.ilike(like)),
                ),
            )
        )
    for values, column in (
        (f.region_id, REGION_ID),
        (f.branch_id, Atm.branch_id),
        (f.status_id, Atm.status_id),
        (f.manufacturer_id, AtmModel.manufacturer_id),
        (f.model_id, Atm.model_id),
        (f.device_type_id, Atm.device_type_id),
        (f.install_format_id, Atm.install_format_id),
        (f.place_type_id, Location.place_type_id),
        (f.vendor_id, Contract.service_vendor_id),
    ):
        if values:
            conds.append(column.in_(values))
    if f.processing_id:
        conds.append(exists().where(AtmProcessing.atm_id == Atm.id, AtmProcessing.processing_id.in_(f.processing_id)))
    if f.currency:
        conds.append(exists().where(atm_currency.c.atm_id == Atm.id, atm_currency.c.currency_code.in_(f.currency)))
    if f.contactless is not None:
        conds.append(Atm.contactless.is_(f.contactless))
    if f.cash_in is not None:
        conds.append(AtmModel.cash_in.is_(f.cash_in))
    if f.is_24h is not None:
        conds.append(Location.is_24h.is_(f.is_24h))
    if f.has_location is not None:
        conds.append(Location.id.is_not(None) if f.has_location else Location.id.is_(None))

    today = date.today()
    if f.warranty_expiring_days is not None:
        conds.append(Contract.warranty_until.between(today, today + timedelta(days=f.warranty_expiring_days)))
    if f.cert_expiring_days is not None:
        until = today + timedelta(days=f.cert_expiring_days)
        expiring = and_(Certificate.valid_until <= until, Certificate.manual_status.is_distinct_from("revoked"))
        # id банкоматов с истекающим сертификатом на сам банкомат, установленный узел или модель
        atm_ids = union(
            select(Certificate.atm_id).where(Certificate.atm_id.is_not(None), expiring),
            select(Module.atm_id)
            .join(Certificate, Certificate.module_id == Module.id)
            .where(Module.removed_at.is_(None), expiring),
            select(Atm.id).join(Certificate, Certificate.atm_model_id == Atm.model_id).where(expiring),
        )
        conds.append(Atm.id.in_(select(atm_ids.subquery().c[0])))
    if f.repair_over_days is not None:
        since = datetime.now().astimezone() - timedelta(days=f.repair_over_days)
        conds.append(
            exists().where(
                ServiceEvent.atm_id == Atm.id, ServiceEvent.finished_at.is_(None), ServiceEvent.started_at <= since
            )
        )
    return stmt.where(*conds) if conds else stmt


SORT_COLUMNS = {
    "atm_code": Atm.atm_code,
    "status": Status.sort,
    "region": Region.sort,
    "model": AtmModel.model_name,
    "branch": Branch.name,
    "commissioning_date": Atm.commissioning_date,
    "warranty_until": Contract.warranty_until,
}


def list_columns():
    return (
        Atm.id,
        Atm.atm_code,
        Status.code.label("status_code"),
        Status.name.label("status"),
        Manufacturer.name.label("manufacturer"),
        AtmModel.model_name.label("model"),
        DeviceType.name.label("device_type"),
        Branch.name.label("branch"),
        Region.name.label("region"),
        Location.city_district,
        Location.address,
        PlaceType.name.label("place_type"),
        Location.latitude,
        Location.longitude,
        Location.is_24h,
        Atm.contactless,
        Atm.commissioning_date,
        Contract.warranty_until,
        own_terminal_id().label("terminal_id"),
        currencies_agg().label("currencies"),
    )
