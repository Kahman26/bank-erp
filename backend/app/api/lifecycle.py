"""Операции с банкоматом. Доступны операционному блоку и выше; каждая возвращает обновлённую карточку."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.deps import require
from app.auth.permissions import Perm, perms_of
from app.db import get_db
from app.models import Atm, ServiceEvent, User
from app.schemas.atms import AtmCard
from app.services.atm_card import build_card, load_atm
from app.services.lifecycle import (
    CloseEventIn,
    ModuleIn,
    MoveIn,
    ServiceEventIn,
    SoftwareIn,
    StatusChange,
    add_module,
    add_software,
    change_status,
    close_event,
    move,
    register_event,
)

router = APIRouter(prefix="/atms/{atm_id}", tags=["lifecycle"])
operator = require(Perm.OPERATE)


def _atm(db: Session, atm_id: int) -> Atm:
    atm = load_atm(db, atm_id)
    if atm is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Банкомат не найден")
    return atm


def _done(db: Session, atm_id: int, user: User) -> AtmCard:
    db.commit()
    db.expire_all()
    return build_card(db, load_atm(db, atm_id), show_ip=Perm.EDIT in perms_of(user.role))


@router.post("/status", response_model=AtmCard)
def set_status(
    atm_id: int, data: StatusChange, db: Session = Depends(get_db), user: User = Depends(operator)
) -> AtmCard:
    change_status(db, _atm(db, atm_id), data, user.id)
    return _done(db, atm_id, user)


@router.post("/move", response_model=AtmCard)
def move_atm(atm_id: int, data: MoveIn, db: Session = Depends(get_db), user: User = Depends(operator)) -> AtmCard:
    move(db, _atm(db, atm_id), data, user.id)
    return _done(db, atm_id, user)


@router.post("/service-events", response_model=AtmCard, status_code=201)
def create_event(
    atm_id: int, data: ServiceEventIn, db: Session = Depends(get_db), user: User = Depends(operator)
) -> AtmCard:
    register_event(db, _atm(db, atm_id), data, user.id)
    return _done(db, atm_id, user)


@router.post("/service-events/{event_id}/close", response_model=AtmCard)
def finish_event(
    atm_id: int,
    event_id: int,
    data: CloseEventIn,
    db: Session = Depends(get_db),
    user: User = Depends(operator),
) -> AtmCard:
    atm = _atm(db, atm_id)
    event = db.get(ServiceEvent, event_id)
    if event is None or event.atm_id != atm_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ремонт не найден")
    close_event(db, atm, event, data, user.id)
    return _done(db, atm_id, user)


@router.post("/modules", response_model=AtmCard, status_code=201)
def create_module(
    atm_id: int, data: ModuleIn, db: Session = Depends(get_db), user: User = Depends(operator)
) -> AtmCard:
    add_module(db, _atm(db, atm_id), data)
    return _done(db, atm_id, user)


@router.post("/software", response_model=AtmCard, status_code=201)
def create_software(
    atm_id: int, data: SoftwareIn, db: Session = Depends(get_db), user: User = Depends(operator)
) -> AtmCard:
    add_software(db, _atm(db, atm_id), data)
    return _done(db, atm_id, user)
