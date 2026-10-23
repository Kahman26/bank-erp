"""Выгрузки списка банкоматов и реестра сертификатов в Excel — с теми же фильтрами, что на экране.

Первые колонки выгрузки банкоматов совпадают с форматом загрузки (по русским названиям),
поэтому выгруженный файл можно поправить и загрузить обратно.
"""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.models import (
    Atm,
    AtmModel,
    AtmProcessing,
    Branch,
    Contract,
    DictItem,
    Location,
    Manufacturer,
    PaymentScheme,
    Processing,
    Region,
    ServiceEvent,
    User,
    Vendor,
    atm_currency,
    atm_scheme,
)
from app.services import atm_query, certificates
from app.services.atm_query import AtmFilter, DeviceType, PlaceType, Status
from app.services.importer import COLUMNS
from app.services.xlsx import build_xlsx

InstallFormat = aliased(DictItem, name="install_format")
ServiceVendor = aliased(Vendor, name="service_vendor")


def _proc(code: str, field):
    return (
        select(field)
        .join(Processing, Processing.id == AtmProcessing.processing_id)
        .where(AtmProcessing.atm_id == Atm.id, Processing.code == code)
        .scalar_subquery()
    )


def atm_export(db: Session, f: AtmFilter, user: User) -> bytes:
    currencies = (
        select(func.string_agg(atm_currency.c.currency_code, ";"))
        .where(atm_currency.c.atm_id == Atm.id)
        .scalar_subquery()
    )
    schemes = (
        select(func.string_agg(PaymentScheme.name, ";"))
        .select_from(atm_scheme.join(PaymentScheme, PaymentScheme.id == atm_scheme.c.scheme_id))
        .where(atm_scheme.c.atm_id == Atm.id)
        .scalar_subquery()
    )
    open_repair = (
        select(func.min(ServiceEvent.started_at))
        .where(ServiceEvent.atm_id == Atm.id, ServiceEvent.finished_at.is_(None))
        .scalar_subquery()
    )
    import_cols = [
        Atm.atm_code,
        _proc("own", AtmProcessing.terminal_id),
        _proc("uzcard", AtmProcessing.terminal_id),
        _proc("humo", AtmProcessing.terminal_id),
        _proc("own", AtmProcessing.merchant_id),
        _proc("uzcard", AtmProcessing.merchant_id),
        _proc("humo", AtmProcessing.merchant_id),
        Atm.serial_number,
        Manufacturer.name,
        AtmModel.model_name,
        DeviceType.name,
        InstallFormat.name,
        Status.name,
        Atm.purchase_date,
        Atm.commissioning_date,
        Branch.name,
        Region.name,
        Location.city_district,
        Location.address,
        Location.landmark,
        Location.latitude,
        Location.longitude,
        PlaceType.name,
        Location.working_hours,
        currencies,
        schemes,
        Atm.screen_size_in,
        Atm.screen_resolution,
        Atm.cassette_count,
        AtmModel.cash_in,
        Atm.contactless,
    ]
    extra = [
        ("Инвентарный номер", 16, Atm.inventory_number),
        ("Название точки", 28, Location.name),
        ("Круглосуточно", 12, Location.is_24h),
        ("Окончание гарантии", 14, Contract.warranty_until),
        ("Сервисный вендор", 20, ServiceVendor.name),
        ("Ремонт открыт с", 16, open_repair),
        ("Дата вывода", 12, Atm.decommission_date),
    ]
    stmt = (
        atm_query.apply_filters(atm_query.base_select(*import_cols, *(e[2] for e in extra)), f)
        .join(InstallFormat, InstallFormat.id == Atm.install_format_id)
        .outerjoin(ServiceVendor, ServiceVendor.id == Contract.service_vendor_id)
        .order_by(Atm.atm_code)
    )
    widths = {"atm_code": 16, "address": 30, "branch": 24, "model": 16, "status": 18, "region": 22}
    columns = [(label, widths.get(col, 14)) for col, (label, _) in COLUMNS.items()]
    columns += [(label, width) for label, width, _ in extra]
    return build_xlsx(
        "Банкоматы",
        columns,
        (tuple(r) for r in db.execute(stmt)),
        params=_params(f.model_dump(exclude_defaults=True), user),
    )


def certificates_export(db: Session, f: certificates.CertFilter, user: User) -> bytes:
    rows = db.execute(
        certificates.apply_filters(certificates.base_select(*certificates.list_columns()), f).order_by(
            certificates.Certificate.valid_until
        )
    )
    labels = {
        "valid": "Действует",
        "expiring": "Истекает",
        "expired": "Истёк",
        "renewal": "На продлении",
        "revoked": "Отозван",
    }
    objects = {"model": "Модель", "atm": "Банкомат", "module": "Узел"}
    data = (
        (
            objects[r.object],
            r.atm_code or "",
            r.model or "",
            f"{r.module_type} {r.module_serial}" if r.module_type else "",
            r.cert_type,
            r.payment_scheme or "",
            r.cert_number,
            r.issued_at,
            r.valid_until,
            labels[r.status],
            "да" if r.needs_review else "",
            r.source or "",
            r.atm_count,
        )
        for r in rows
    )
    columns = [
        ("Объект", 12),
        ("Банкомат", 16),
        ("Модель", 24),
        ("Узел", 32),
        ("Вид", 28),
        ("Платёжная система", 16),
        ("Номер", 20),
        ("Дата выдачи", 12),
        ("Действует до", 12),
        ("Статус", 14),
        ("Требует проверки", 14),
        ("Кем предоставлен", 22),
        ("Банкоматов", 12),
    ]
    filters = f.model_dump(exclude_defaults=True, exclude={"page", "page_size"})
    return build_xlsx("Сертификаты", columns, data, params=_params(filters, user))


def _params(filters: dict, user: User) -> list[tuple[str, str]]:
    shown = "; ".join(f"{k} = {v}" for k, v in filters.items()) or "без фильтров"
    return [("Дата выгрузки", f"{date.today():%d.%m.%Y}"), ("Выгрузил", user.full_name), ("Фильтры", shown)]
