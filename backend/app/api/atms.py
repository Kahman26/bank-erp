from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.auth.deps import require
from app.auth.permissions import Perm, perms_of
from app.db import get_db
from app.models import (
    Atm,
    AtmProcessing,
    AtmStatusHistory,
    Contract,
    Currency,
    DictItem,
    Location,
    PaymentScheme,
    User,
)
from app.schemas.atms import AtmCard, AtmCreate, AtmIn, AtmPage, AtmRow, ContractIn, MapPoints, ProcessingIn
from app.services.atm_card import build_card, load_atm
from app.services.atm_pdf import atm_pdf
from app.services.atm_query import (
    SORT_COLUMNS,
    FilterQuery,
    ListQuery,
    Status,
    apply_filters,
    base_select,
    list_columns,
)
from app.services.exports import atm_export
from app.services.xlsx import XLSX_MEDIA, content_disposition

router = APIRouter(prefix="/atms", tags=["atms"])


@router.get("", response_model=AtmPage)
def list_atms(params: ListQuery, db: Session = Depends(get_db), _: User = Depends(require(Perm.VIEW))) -> AtmPage:
    filtered = apply_filters(base_select(Atm.id), params)
    total = db.scalar(select(func.count()).select_from(filtered.subquery())) or 0
    order = SORT_COLUMNS[params.sort]
    order = order.desc().nulls_last() if params.order == "desc" else order.asc().nulls_last()
    stmt = (
        apply_filters(base_select(*list_columns()), params)
        .order_by(order, Atm.atm_code)
        .offset((params.page - 1) * params.page_size)
        .limit(params.page_size)
    )
    items = [AtmRow.model_validate(dict(r._mapping)) for r in db.execute(stmt)]
    return AtmPage(items=items, total=total, page=params.page, page_size=params.page_size)


@router.get("/map", response_model=MapPoints)
def map_points(f: FilterQuery, db: Session = Depends(get_db), _: User = Depends(require(Perm.VIEW))) -> MapPoints:
    rows = db.execute(
        apply_filters(base_select(Atm.id, Atm.atm_code, Location.latitude, Location.longitude, Status.code), f)
    ).all()
    points = [(r[0], r[1], float(r[2]), float(r[3]), r[4]) for r in rows if r[2] is not None]
    return MapPoints(points=points, total=len(rows), without_location=len(rows) - len(points))


@router.get("/export.xlsx")
def export_atms(f: FilterQuery, db: Session = Depends(get_db), user: User = Depends(require(Perm.VIEW))) -> Response:
    return Response(atm_export(db, f, user), media_type=XLSX_MEDIA, headers=content_disposition("atms.xlsx"))


@router.get("/{atm_id}/card.pdf")
def card_pdf(atm_id: int, db: Session = Depends(get_db), user: User = Depends(require(Perm.VIEW))) -> Response:
    atm = load_atm(db, atm_id)
    if atm is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Банкомат не найден")
    card = build_card(db, atm, show_ip=False)
    return Response(
        atm_pdf(card, user.full_name),
        media_type="application/pdf",
        headers=content_disposition(f"{atm.atm_code}.pdf"),
    )


@router.get("/{atm_id}", response_model=AtmCard)
def get_atm(atm_id: int, db: Session = Depends(get_db), user: User = Depends(require(Perm.VIEW))) -> AtmCard:
    atm = load_atm(db, atm_id)
    if atm is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Банкомат не найден")
    return build_card(db, atm, show_ip=Perm.EDIT in perms_of(user.role))


def _apply(db: Session, atm: Atm, data: AtmIn) -> None:
    for field, value in data.model_dump(exclude={"currencies", "service_ids", "scheme_ids", "status_id"}).items():
        setattr(atm, field, value)
    atm.currencies = list(db.scalars(select(Currency).where(Currency.code.in_(data.currencies))))
    if len(atm.currencies) != len(set(data.currencies)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Неизвестная валюта")
    atm.services = list(db.scalars(select(DictItem).where(DictItem.id.in_(data.service_ids))))
    atm.schemes = list(db.scalars(select(PaymentScheme).where(PaymentScheme.id.in_(data.scheme_ids))))


@router.post("", response_model=AtmCard, status_code=201)
def create_atm(data: AtmCreate, db: Session = Depends(get_db), user: User = Depends(require(Perm.EDIT))) -> AtmCard:
    status_id = data.status_id or db.scalar(
        select(DictItem.id).where(DictItem.kind == "atm_status", DictItem.code == "in_stock")
    )
    atm = Atm(status_id=status_id)
    _apply(db, atm, data)
    db.add(atm)
    db.flush()
    db.add(AtmStatusHistory(atm_id=atm.id, status_id=status_id, changed_by_id=user.id, comment="Банкомат заведён"))
    db.commit()
    return build_card(db, load_atm(db, atm.id), show_ip=True)


@router.put("/{atm_id}", response_model=AtmCard)
def update_atm(
    atm_id: int, data: AtmIn, db: Session = Depends(get_db), _: User = Depends(require(Perm.EDIT))
) -> AtmCard:
    atm = load_atm(db, atm_id)
    if atm is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Банкомат не найден")
    _apply(db, atm, data)
    db.commit()
    db.expire_all()
    return build_card(db, load_atm(db, atm_id), show_ip=True)


@router.put("/{atm_id}/processings", response_model=AtmCard)
def set_processings(
    atm_id: int,
    data: list[ProcessingIn],
    db: Session = Depends(get_db),
    _: User = Depends(require(Perm.EDIT)),
) -> AtmCard:
    if load_atm(db, atm_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Банкомат не найден")
    if len({p.processing_id for p in data}) != len(data):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Процессинг указан дважды")
    db.execute(delete(AtmProcessing).where(AtmProcessing.atm_id == atm_id))
    db.flush()
    db.add_all(AtmProcessing(atm_id=atm_id, **p.model_dump()) for p in data)
    db.commit()  # дубль Terminal ID / Merchant ID в процессинге → 409
    db.expire_all()
    return build_card(db, load_atm(db, atm_id), show_ip=True)


def add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    year, month = d.year + y, m + 1
    days = [31, 29 if year % 4 == 0 and (year % 100 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return date(year, month, min(d.day, days[month - 1]))


@router.put("/{atm_id}/contract", response_model=AtmCard)
def set_contract(
    atm_id: int, data: ContractIn, db: Session = Depends(get_db), _: User = Depends(require(Perm.EDIT))
) -> AtmCard:
    atm = load_atm(db, atm_id)
    if atm is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Банкомат не найден")
    values = data.model_dump(exclude={"auto_warranty"})
    if data.auto_warranty:
        # окончание гарантии = дата покупки + гарантийный срок модели
        if atm.purchase_date is None or atm.model.warranty_months is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Для расчёта нужны дата покупки и гарантийный срок модели")
        values["warranty_until"] = add_months(atm.purchase_date, atm.model.warranty_months)
    contract = db.scalar(select(Contract).where(Contract.atm_id == atm_id)) or Contract(atm_id=atm_id)
    for field, value in values.items():
        setattr(contract, field, value)
    db.add(contract)
    db.commit()
    db.expire_all()
    return build_card(db, load_atm(db, atm_id), show_ip=True)
