"""Дашборд и отчёты. Каждая таблица дашборда выгружается в Excel тем же запросом."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import Row, extract, func, literal, select
from sqlalchemy.orm import Session

from app.models import (
    Atm,
    AtmModel,
    Branch,
    Contract,
    DictItem,
    Location,
    Manufacturer,
    Placement,
    Region,
    ServiceEvent,
    Vendor,
)
from app.services import certificates

ACTIVE = ("in_service", "repair", "vendor_repair", "installing")  # банкоматы «в сети»
REPAIR = ("repair", "vendor_repair")


def _status_code():
    return select(DictItem.code).where(DictItem.id == Atm.status_id).scalar_subquery()


def _region_id():
    current = (
        select(Location.region_id)
        .join(Placement, Placement.location_id == Location.id)
        .where(Placement.atm_id == Atm.id, Placement.placed_to.is_(None))
        .scalar_subquery()
    )
    branch = select(Branch.region_id).where(Branch.id == Atm.branch_id).scalar_subquery()
    return func.coalesce(current, branch)


def totals(db: Session) -> dict[str, int]:
    today = date.today()
    code = _status_code()
    row = db.execute(
        select(
            func.count(Atm.id),
            func.count().filter(code == "in_service"),
            func.count().filter(code.in_(REPAIR)),
            func.count().filter(code.in_(("in_stock", "in_delivery", "on_farm"))),
            func.count().filter(code.not_in(("written_off",))),
        )
    ).one()
    warranty = db.scalar(
        select(func.count(Contract.id)).where(Contract.warranty_until.between(today, today + timedelta(days=90)))
    )
    eos = db.scalar(
        select(func.count(Atm.id))
        .join(AtmModel, AtmModel.id == Atm.model_id)
        .where(AtmModel.end_of_support_date <= today + timedelta(days=365), _status_code() != "written_off")
    )
    cert = certificates.summary(db)
    return {
        "atms": row[0],
        "in_service": row[1],
        "in_repair": row[2],
        "not_placed": row[3],
        "in_network": row[4],
        "warranty_expiring_90": warranty or 0,
        "end_of_support_365": eos or 0,
        "certs_expiring": cert["expiring"],
        "certs_expired": cert["expired"],
        "certs_needs_review": cert["needs_review"],
        "modules_without_cert": cert["modules_without"],
    }


def by_status(db: Session) -> list[Row]:
    return db.execute(
        select(DictItem.code, DictItem.name, func.count(Atm.id))
        .join(Atm, Atm.status_id == DictItem.id)
        .group_by(DictItem.id)
        .order_by(DictItem.sort)
    ).all()


def by_region(db: Session) -> list[Row]:
    code = _status_code()
    region = _region_id().label("region_id")
    sub = select(region, code.label("code")).select_from(Atm).subquery()
    return db.execute(
        select(
            Region.name.label("region"),
            func.count(sub.c.region_id).filter(sub.c.code != "written_off").label("total"),
            func.count().filter(sub.c.code == "in_service").label("in_service"),
            func.count().filter(sub.c.code.in_(REPAIR)).label("in_repair"),
        )
        .join(sub, sub.c.region_id == Region.id)
        .group_by(Region.id)
        .order_by(func.count(sub.c.region_id).desc())
    ).all()


def by_model(db: Session) -> list[Row]:
    return db.execute(
        select(
            Manufacturer.name,
            AtmModel.model_name,
            func.count(Atm.id).label("total"),
            AtmModel.end_of_support_date,
        )
        .join(AtmModel, AtmModel.manufacturer_id == Manufacturer.id)
        .join(Atm, Atm.model_id == AtmModel.id)
        .where(_status_code() != "written_off")
        .group_by(Manufacturer.name, AtmModel.id)
        .order_by(func.count(Atm.id).desc())
    ).all()


def vendors(db: Session, days: int = 365) -> list[Row]:
    """Ремонты и простои по исполнителям за период."""
    since = datetime.now(UTC) - timedelta(days=days)
    hours = extract("epoch", ServiceEvent.finished_at - ServiceEvent.started_at) / 3600
    performer = func.coalesce(Vendor.name, literal("Инженер банка"))
    return db.execute(
        select(
            performer.label("performer"),
            func.count(ServiceEvent.id).label("events"),
            func.round(func.avg(hours), 1).label("avg_hours"),
            func.round(func.sum(hours), 0).label("total_hours"),
            func.count().filter(ServiceEvent.finished_at.is_(None)).label("open"),
            func.count().filter(ServiceEvent.affects_certification).label("cert_events"),
        )
        .outerjoin(Vendor, Vendor.id == ServiceEvent.vendor_id)
        .where(ServiceEvent.started_at >= since)
        .group_by(performer)
        .order_by(func.count(ServiceEvent.id).desc())
    ).all()


def repairs_by_month(db: Session, months: int = 12) -> list[Row]:
    today = date.today()
    y, m = divmod(today.year * 12 + today.month - 1 - (months - 1), 12)
    start = date(y, m + 1, 1)  # первое число месяца, ровно months месяцев с текущим включительно
    month = func.date_trunc("month", ServiceEvent.started_at)
    return db.execute(
        select(
            func.to_char(month, "YYYY-MM").label("month"),
            func.count(ServiceEvent.id).label("events"),
            func.count().filter(ServiceEvent.affects_certification).label("cert_events"),
        )
        .where(ServiceEvent.started_at >= datetime.combine(start, datetime.min.time(), tzinfo=UTC))
        .group_by(month)
        .order_by(month)
    ).all()


def end_of_support(db: Session, years: int = 2) -> list[Row]:
    until = date.today() + timedelta(days=365 * years)
    return db.execute(
        select(Manufacturer.name, AtmModel.model_name, AtmModel.end_of_support_date, func.count(Atm.id).label("total"))
        .join(AtmModel, AtmModel.manufacturer_id == Manufacturer.id)
        .join(Atm, Atm.model_id == AtmModel.id)
        .where(AtmModel.end_of_support_date <= until, _status_code() != "written_off")
        .group_by(Manufacturer.name, AtmModel.id)
        .order_by(AtmModel.end_of_support_date)
    ).all()


def warranty_expiring(db: Session, days: int = 90) -> list[Row]:
    today = date.today()
    return db.execute(
        select(Atm.atm_code, Manufacturer.name, AtmModel.model_name, Contract.warranty_until, Vendor.name)
        .join(Contract, Contract.atm_id == Atm.id)
        .join(AtmModel, AtmModel.id == Atm.model_id)
        .join(Manufacturer, Manufacturer.id == AtmModel.manufacturer_id)
        .outerjoin(Vendor, Vendor.id == Contract.service_vendor_id)
        .where(Contract.warranty_until.between(today, today + timedelta(days=days)))
        .order_by(Contract.warranty_until)
    ).all()


def dashboard(db: Session) -> dict:
    return {
        "totals": totals(db),
        "by_status": [{"code": c, "name": n, "count": k} for c, n, k in by_status(db)],
        "by_region": [r._asdict() for r in by_region(db)],
        "by_model": [{"model": f"{m} {n}", "total": t, "end_of_support_date": e} for m, n, t, e in by_model(db)],
        "vendors": [r._asdict() for r in vendors(db)],
        "repairs_by_month": [r._asdict() for r in repairs_by_month(db)],
        "end_of_support": [
            {"model": f"{m} {n}", "end_of_support_date": e, "total": t} for m, n, e, t in end_of_support(db)
        ],
    }


@dataclass(frozen=True)
class Report:
    title: str
    filename: str
    columns: list[tuple[str, int]]
    rows: Callable[[Session], list]


REPORTS: dict[str, Report] = {
    "by-region": Report(
        "Парк по регионам",
        "atms-by-region.xlsx",
        [("Регион", 30), ("В сети", 12), ("В эксплуатации", 16), ("В ремонте", 12)],
        by_region,
    ),
    "by-model": Report(
        "Парк по моделям",
        "atms-by-model.xlsx",
        [("Производитель", 20), ("Модель", 20), ("Банкоматов", 12), ("Поддержка до", 14)],
        by_model,
    ),
    "vendors": Report(
        "Ремонты и простои по исполнителям за 12 месяцев",
        "repairs-by-vendor.xlsx",
        [
            ("Исполнитель", 26),
            ("Ремонтов", 12),
            ("Средний простой, ч", 18),
            ("Простой всего, ч", 16),
            ("Открыто", 10),
            ("Влияли на сертификацию", 22),
        ],
        vendors,
    ),
    "repairs-by-month": Report(
        "Ремонты по месяцам",
        "repairs-by-month.xlsx",
        [("Месяц", 12), ("Ремонтов", 12), ("Влияли на сертификацию", 22)],
        repairs_by_month,
    ),
    "end-of-support": Report(
        "Окончание поддержки моделей в ближайшие 2 года",
        "end-of-support.xlsx",
        [("Производитель", 20), ("Модель", 20), ("Поддержка до", 14), ("Банкоматов", 12)],
        end_of_support,
    ),
    "warranty": Report(
        "Гарантия истекает в ближайшие 90 дней",
        "warranty-expiring.xlsx",
        [("Банкомат", 16), ("Производитель", 20), ("Модель", 18), ("Гарантия до", 14), ("Сервисный вендор", 22)],
        warranty_expiring,
    ),
}
