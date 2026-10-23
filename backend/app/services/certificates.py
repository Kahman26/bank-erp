"""Реестр сертификатов: статусы по датам, фильтры, сводка, узлы без сертификата."""

from datetime import date, timedelta
from typing import Annotated, Literal

from fastapi import Query
from pydantic import BaseModel, Field
from sqlalchemy import Select, and_, case, exists, func, literal, or_, select
from sqlalchemy.orm import aliased

from app.models import (
    Atm,
    AtmModel,
    Certificate,
    DictItem,
    Manufacturer,
    Module,
    PaymentScheme,
)
from app.services.atm_card import EXPIRING_DAYS

CertStatus = Literal["valid", "expiring", "expired", "renewal", "revoked"]
# узлы, сертификаты которых проверяют платёжные системы
CERT_MODULE_TYPES = ("card_reader", "nfc_reader", "epp")


def status_expr(today: date | None = None):
    today = today or date.today()
    return case(
        (Certificate.manual_status.is_not(None), Certificate.manual_status),
        (Certificate.valid_until < today, literal("expired")),
        (Certificate.valid_until <= today + timedelta(days=EXPIRING_DAYS), literal("expiring")),
        else_=literal("valid"),
    )


class CertFilter(BaseModel):
    q: str | None = None
    status: list[CertStatus] = []
    cert_type_id: list[int] = []
    payment_scheme_id: list[int] = []
    object: list[Literal["model", "atm", "module"]] = []
    needs_review: bool | None = None
    expiring_days: int | None = Field(default=None, ge=0, le=3650)
    include_removed: bool = False  # сертификаты снятых узлов — история
    atm_id: int | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)


CertQuery = Annotated[CertFilter, Query()]

CertType = aliased(DictItem, name="cert_type")
Source = aliased(DictItem, name="source")
ModuleType = aliased(DictItem, name="module_type")
ModuleAtm = aliased(Atm, name="module_atm")
ModelOfCert = aliased(AtmModel, name="cert_model")
ModelMaker = aliased(Manufacturer, name="cert_model_maker")

OBJECT = case(
    (Certificate.atm_model_id.is_not(None), literal("model")),
    (Certificate.atm_id.is_not(None), literal("atm")),
    else_=literal("module"),
)
ATM_ID = func.coalesce(Certificate.atm_id, ModuleAtm.id)


def base_select(*columns) -> Select:
    return (
        select(*columns)
        .select_from(Certificate)
        .join(CertType, CertType.id == Certificate.cert_type_id)
        .outerjoin(Source, Source.id == Certificate.source_id)
        .outerjoin(PaymentScheme, PaymentScheme.id == Certificate.payment_scheme_id)
        .outerjoin(Module, Module.id == Certificate.module_id)
        .outerjoin(ModuleType, ModuleType.id == Module.module_type_id)
        .outerjoin(ModuleAtm, ModuleAtm.id == Module.atm_id)
        .outerjoin(Atm, Atm.id == Certificate.atm_id)
        .outerjoin(ModelOfCert, ModelOfCert.id == Certificate.atm_model_id)
        .outerjoin(ModelMaker, ModelMaker.id == ModelOfCert.manufacturer_id)
    )


def apply_filters(stmt: Select, f: CertFilter) -> Select:
    conds = []
    if f.q and f.q.strip():
        like = f"%{f.q.strip()}%"
        conds.append(
            or_(
                Certificate.cert_number.ilike(like),
                Atm.atm_code.ilike(like),
                ModuleAtm.atm_code.ilike(like),
                Module.serial_number.ilike(like),
                ModelOfCert.model_name.ilike(like),
            )
        )
    if f.status:
        conds.append(status_expr().in_(f.status))
    if f.cert_type_id:
        conds.append(Certificate.cert_type_id.in_(f.cert_type_id))
    if f.payment_scheme_id:
        conds.append(Certificate.payment_scheme_id.in_(f.payment_scheme_id))
    if f.object:
        conds.append(OBJECT.in_(f.object))
    if f.needs_review is not None:
        conds.append(Certificate.needs_review.is_(f.needs_review))
    if f.expiring_days is not None:
        conds.append(Certificate.valid_until <= date.today() + timedelta(days=f.expiring_days))
        conds.append(Certificate.manual_status.is_distinct_from("revoked"))
    if f.atm_id is not None:
        model_id = select(Atm.model_id).where(Atm.id == f.atm_id).scalar_subquery()
        conds.append(or_(f.atm_id == ATM_ID, Certificate.atm_model_id == model_id))
    if not f.include_removed and not f.needs_review:
        conds.append(or_(Module.id.is_(None), Module.removed_at.is_(None), Certificate.needs_review))
    return stmt.where(*conds) if conds else stmt


def list_columns():
    atm_count = (
        select(func.count(Atm.id)).where(Atm.model_id == Certificate.atm_model_id).correlate(Certificate)
    ).scalar_subquery()
    return (
        Certificate.id,
        OBJECT.label("object"),
        Certificate.atm_model_id,
        ATM_ID.label("atm_id"),
        func.coalesce(Atm.atm_code, ModuleAtm.atm_code).label("atm_code"),
        func.concat(ModelMaker.name, " ", ModelOfCert.model_name).label("model"),
        Certificate.module_id,
        ModuleType.name.label("module_type"),
        Module.serial_number.label("module_serial"),
        Module.removed_at.label("module_removed_at"),
        CertType.id.label("cert_type_id"),
        CertType.name.label("cert_type"),
        Certificate.payment_scheme_id,
        PaymentScheme.name.label("payment_scheme"),
        Certificate.cert_number,
        Certificate.issued_at,
        Certificate.valid_until,
        Certificate.manual_status,
        status_expr().label("status"),
        Certificate.needs_review,
        Certificate.source_id,
        Source.name.label("source"),
        (Certificate.document_path.is_not(None)).label("has_document"),
        case((Certificate.atm_model_id.is_not(None), atm_count), else_=literal(1)).label("atm_count"),
    )


def summary(db) -> dict[str, int]:
    rows = db.execute(
        apply_filters(base_select(status_expr().label("s"), func.count()), CertFilter()).group_by("s")
    ).all()
    counts = {s: 0 for s in ("valid", "expiring", "expired", "renewal", "revoked")}
    counts.update({s: n for s, n in rows})
    counts["needs_review"] = db.scalar(select(func.count(Certificate.id)).where(Certificate.needs_review)) or 0
    counts["modules_without"] = db.scalar(select(func.count()).select_from(modules_without_cert().subquery())) or 0
    return counts


def modules_without_cert() -> Select:
    """Установленные картридеры, NFC-ридеры и EPP без действующего сертификата."""
    today = date.today()
    valid_cert = exists().where(
        Certificate.module_id == Module.id,
        Certificate.valid_until >= today,
        Certificate.manual_status.is_distinct_from("revoked"),
    )
    return (
        select(
            Module.id,
            Module.serial_number,
            Module.installed_at,
            ModuleType.name.label("module_type"),
            Atm.id.label("atm_id"),
            Atm.atm_code,
            func.concat(Manufacturer.name, " ", AtmModel.model_name).label("model"),
        )
        .join(ModuleType, ModuleType.id == Module.module_type_id)
        .join(Atm, Atm.id == Module.atm_id)
        .join(AtmModel, AtmModel.id == Atm.model_id)
        .join(Manufacturer, Manufacturer.id == AtmModel.manufacturer_id)
        .join(DictItem, and_(DictItem.id == Atm.status_id, DictItem.code != "written_off"))
        .where(Module.removed_at.is_(None), ModuleType.code.in_(CERT_MODULE_TYPES), ~valid_cert)
        .order_by(Atm.atm_code, ModuleType.sort)
    )
