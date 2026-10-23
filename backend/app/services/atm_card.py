"""Сборка карточки банкомата: все разделы одним ответом, с подписями вместо id."""

from datetime import date, datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import (
    Atm,
    AtmModel,
    AtmProcessing,
    AtmStatusHistory,
    Certificate,
    Contract,
    DictItem,
    Module,
    Placement,
    ServiceEvent,
    Software,
    User,
)
from app.schemas.atms import AtmCard, AtmCreate

CERT_STATUS = {
    "revoked": "Отозван",
    "renewal": "На продлении",
    "expired": "Истёк",
    "expiring": "Истекает",
    "valid": "Действует",
}
EXPIRING_DAYS = 90


def cert_status(valid_until: date, manual: str | None, today: date | None = None) -> str:
    if manual:
        return manual
    days = (valid_until - (today or date.today())).days
    if days < 0:
        return "expired"
    return "expiring" if days <= EXPIRING_DAYS else "valid"


def _loc(loc) -> dict[str, Any]:
    return {
        "id": loc.id,
        "name": loc.name,
        "region": loc.region.name,
        "city_district": loc.city_district,
        "address": loc.address,
        "landmark": loc.landmark,
        "latitude": float(loc.latitude),
        "longitude": float(loc.longitude),
        "place_type": loc.place_type.name,
        "indoor": loc.indoor,
        "is_24h": loc.is_24h,
        "working_hours": loc.working_hours,
        "premises_owner": loc.premises_owner,
        "site_contact": loc.site_contact,
    }


def build_card(db: Session, atm: Atm, show_ip: bool) -> AtmCard:
    names = {d.id: d.name for d in db.scalars(select(DictItem))}
    extra = {d.id: d.extra for d in db.scalars(select(DictItem).where(DictItem.kind == "module_type"))}
    n = names.get
    model: AtmModel = atm.model

    placements = db.scalars(
        select(Placement)
        .where(Placement.atm_id == atm.id)
        .options(joinedload(Placement.location), joinedload(Placement.move_reason))
        .order_by(Placement.placed_from.desc())
    ).all()
    current = next((p for p in placements if p.placed_to is None), None)

    modules = db.scalars(
        select(Module).where(Module.atm_id == atm.id).order_by(Module.removed_at.is_not(None), Module.module_type_id)
    ).all()
    module_ids = [m.id for m in modules]

    certs = db.scalars(
        select(Certificate)
        .where(
            or_(
                Certificate.atm_id == atm.id,
                Certificate.atm_model_id == atm.model_id,
                Certificate.module_id.in_(module_ids) if module_ids else False,
            )
        )
        .options(joinedload(Certificate.payment_scheme))
        .order_by(Certificate.valid_until)
    ).all()
    module_by_id = {m.id: m for m in modules}

    events = db.scalars(
        select(ServiceEvent)
        .where(ServiceEvent.atm_id == atm.id)
        .options(joinedload(ServiceEvent.vendor), selectinload(ServiceEvent.replacements))
        .order_by(ServiceEvent.started_at.desc())
    ).all()
    users = {u.id: u.full_name for u in db.scalars(select(User))}

    def module_label(m: Module) -> str:
        return f"{n(m.module_type_id)} · {m.serial_number}"

    contract = db.scalar(
        select(Contract)
        .where(Contract.atm_id == atm.id)
        .options(joinedload(Contract.supplier), joinedload(Contract.service_vendor))
    )
    history = db.scalars(
        select(AtmStatusHistory).where(AtmStatusHistory.atm_id == atm.id).order_by(AtmStatusHistory.changed_at.desc())
    ).all()
    processings = db.scalars(
        select(AtmProcessing)
        .where(AtmProcessing.atm_id == atm.id)
        .options(joinedload(AtmProcessing.processing))
        .order_by(AtmProcessing.processing_id)
    ).all()
    software = db.scalars(
        select(Software).where(Software.atm_id == atm.id).order_by(Software.software_type_id, Software.installed_at)
    ).all()

    def hours(start: datetime, end: datetime | None) -> float | None:
        return round((end - start).total_seconds() / 3600, 1) if end else None

    edit = AtmCreate(
        **{f: getattr(atm, f) for f in AtmCreate.model_fields if hasattr(Atm, f) and f not in ("currencies",)},
        currencies=[c.code for c in atm.currencies],
        service_ids=[s.id for s in atm.services],
        scheme_ids=[s.id for s in atm.schemes],
    )

    return AtmCard(
        id=atm.id,
        atm_code=atm.atm_code,
        edit=edit,
        updated_at=atm.updated_at,
        header={
            "status_code": atm.status.code,
            "status": atm.status.name,
            "model": f"{model.manufacturer.name} {model.model_name}",
            "model_id": model.id,
            "device_type": atm.device_type.name,
            "address": f"{current.location.city_district}, {current.location.address}" if current else None,
        },
        main={
            "serial_number": atm.serial_number,
            "inventory_number": atm.inventory_number,
            "install_format": atm.install_format.name,
            "branch": atm.branch.name,
            "purchase_date": atm.purchase_date,
            "commissioning_date": atm.commissioning_date,
            "decommission_date": atm.decommission_date,
            "currencies": [c.code for c in atm.currencies],
            "services": [s.name for s in atm.services],
            "schemes": [s.name for s in atm.schemes],
            "notes": atm.notes,
            "model_cash_in": model.cash_in,
            "model_recycling": model.recycling,
            "end_of_support_date": model.end_of_support_date,
        },
        config={
            "screen_size_in": atm.screen_size_in,
            "screen_resolution": atm.screen_resolution,
            "screen_orientation": n(atm.screen_orientation_id),
            "input_method": n(atm.input_method_id),
            "screen_sunlight": atm.screen_sunlight,
            "privacy_filter": atm.privacy_filter,
            "safe_class": n(atm.safe_class_id),
            "safe_lock": n(atm.safe_lock_id),
            "service_access": n(atm.service_access_id),
            "cassette_count": atm.cassette_count,
            "contactless": atm.contactless,
            "audio_jack": atm.audio_jack,
            "ups": atm.ups,
        },
        location=_loc(current.location) if current else None,
        placements=[
            {
                "id": p.id,
                "placed_from": p.placed_from,
                "placed_to": p.placed_to,
                "move_reason": p.move_reason.name if p.move_reason else None,
                "basis_document": p.basis_document,
                "location": _loc(p.location),
            }
            for p in placements
        ],
        processings=[
            {
                "id": p.id,
                "processing_id": p.processing_id,
                "processing": p.processing.name,
                "terminal_id": p.terminal_id,
                "merchant_id": p.merchant_id,
                "host_protocol_id": p.host_protocol_id,
                "host_protocol": n(p.host_protocol_id),
                "connection_type_id": p.connection_type_id,
                "connection_type": n(p.connection_type_id),
                # IP-адрес видят только администраторы (набор полей v0.2, раздел 3.5)
                "ip_address": p.ip_address if show_ip else None,
            }
            for p in processings
        ],
        modules=[
            {
                "id": m.id,
                "type": n(m.module_type_id),
                "xfs": extra.get(m.module_type_id, {}).get("xfs"),
                "vendor": m.vendor,
                "model": m.model,
                "serial_number": m.serial_number,
                "firmware_version": m.firmware_version,
                "installed_at": m.installed_at,
                "removed_at": m.removed_at,
                "is_faulty": m.is_faulty,
                "attributes": m.attributes,
            }
            for m in modules
        ],
        software=[
            {
                "id": s.id,
                "type": n(s.software_type_id),
                "name": s.name,
                "version": s.version,
                "installed_at": s.installed_at,
            }
            for s in software
        ],
        service_events=[
            {
                "id": e.id,
                "type": n(e.event_type_id),
                "ticket_number": e.ticket_number,
                "started_at": e.started_at,
                "finished_at": e.finished_at,
                "downtime_hours": hours(e.started_at, e.finished_at),
                "problem": e.problem,
                "work_done": e.work_done,
                "affects_certification": e.affects_certification,
                "performer": e.vendor.name if e.vendor else "Инженер банка",
                "cost": e.cost,
                "cost_currency": e.cost_currency,
                "replacements": [
                    {
                        "removed": module_label(module_by_id[r.removed_module_id]),
                        "installed": module_label(module_by_id[r.installed_module_id]),
                    }
                    for r in e.replacements
                    if r.removed_module_id in module_by_id and r.installed_module_id in module_by_id
                ],
            }
            for e in events
        ],
        certificates=[
            {
                "id": c.id,
                "object": "model" if c.atm_model_id else "atm" if c.atm_id else "module",
                "object_label": (
                    f"Модель {model.model_name}"
                    if c.atm_model_id
                    else "Банкомат"
                    if c.atm_id
                    else module_label(module_by_id[c.module_id])
                    + (" (снят)" if module_by_id[c.module_id].removed_at else "")
                ),
                "cert_type": n(c.cert_type_id),
                "payment_scheme": c.payment_scheme.name if c.payment_scheme else None,
                "cert_number": c.cert_number,
                "issued_at": c.issued_at,
                "valid_until": c.valid_until,
                "status": (st := cert_status(c.valid_until, c.manual_status)),
                "status_label": CERT_STATUS[st],
                "needs_review": c.needs_review,
                "source": n(c.source_id),
            }
            for c in certs
        ],
        status_history=[
            {
                "status": n(h.status_id),
                "changed_at": h.changed_at,
                "changed_by": users.get(h.changed_by_id) if h.changed_by_id else None,
                "comment": h.comment,
            }
            for h in history
        ],
        contract=(
            {
                "supplier": contract.supplier.name if contract.supplier else None,
                "purchase_contract": contract.purchase_contract,
                "purchase_price": contract.purchase_price,
                "price_currency": contract.price_currency,
                "warranty_until": contract.warranty_until,
                "service_vendor": contract.service_vendor.name if contract.service_vendor else None,
                "service_sla_hours": contract.service_sla_hours,
            }
            if contract
            else None
        ),
    )


def load_atm(db: Session, atm_id: int) -> Atm | None:
    return db.scalar(
        select(Atm)
        .where(Atm.id == atm_id)
        .options(
            joinedload(Atm.model).joinedload(AtmModel.manufacturer),
            joinedload(Atm.status),
            joinedload(Atm.device_type),
            joinedload(Atm.install_format),
            joinedload(Atm.branch),
            selectinload(Atm.currencies),
            selectinload(Atm.services),
            selectinload(Atm.schemes),
        )
    )
