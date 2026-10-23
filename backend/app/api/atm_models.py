from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.auth.deps import require
from app.auth.permissions import Perm
from app.db import get_db
from app.models import Atm, AtmModel, User
from app.schemas.atm_models import AtmModelIn, AtmModelOut

router = APIRouter(prefix="/atm-models", tags=["atm-models"])


def _out(m: AtmModel, atm_count: int = 0) -> AtmModelOut:
    return AtmModelOut.model_validate(
        {
            **{c.key: getattr(m, c.key) for c in AtmModel.__table__.columns},
            "manufacturer_name": m.manufacturer.name,
            "device_type_name": m.device_type.name,
            "atm_count": atm_count,
        }
    )


def _get(db: Session, model_id: int) -> AtmModel:
    m = db.get(AtmModel, model_id, options=[joinedload(AtmModel.manufacturer), joinedload(AtmModel.device_type)])
    if m is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Модель не найдена")
    return m


def _count(db: Session, model_id: int) -> int:
    return db.scalar(select(func.count(Atm.id)).where(Atm.model_id == model_id)) or 0


@router.get("", response_model=list[AtmModelOut])
def list_models(db: Session = Depends(get_db), _: User = Depends(require(Perm.VIEW))) -> list[AtmModelOut]:
    counts = dict(db.execute(select(Atm.model_id, func.count(Atm.id)).group_by(Atm.model_id)).all())
    models = db.scalars(
        select(AtmModel)
        .options(joinedload(AtmModel.manufacturer), joinedload(AtmModel.device_type))
        .order_by(AtmModel.model_name)
    ).all()
    models = sorted(models, key=lambda m: (m.manufacturer.name, m.model_name))
    return [_out(m, counts.get(m.id, 0)) for m in models]


@router.get("/{model_id}", response_model=AtmModelOut)
def get_model(model_id: int, db: Session = Depends(get_db), _: User = Depends(require(Perm.VIEW))) -> AtmModelOut:
    return _out(_get(db, model_id), _count(db, model_id))


@router.post("", response_model=AtmModelOut, status_code=201)
def create_model(
    data: AtmModelIn, db: Session = Depends(get_db), _: User = Depends(require(Perm.MANAGE_REFERENCE))
) -> AtmModelOut:
    m = AtmModel(**data.model_dump())
    db.add(m)
    db.commit()
    return _out(_get(db, m.id))


@router.put("/{model_id}", response_model=AtmModelOut)
def update_model(
    model_id: int,
    data: AtmModelIn,
    db: Session = Depends(get_db),
    _: User = Depends(require(Perm.MANAGE_REFERENCE)),
) -> AtmModelOut:
    m = _get(db, model_id)
    for field, value in data.model_dump().items():
        setattr(m, field, value)
    db.commit()
    db.expire(m)
    return _out(_get(db, model_id), _count(db, model_id))


@router.delete("/{model_id}", status_code=204)
def delete_model(
    model_id: int, db: Session = Depends(get_db), _: User = Depends(require(Perm.MANAGE_REFERENCE))
) -> None:
    m = _get(db, model_id)
    if _count(db, model_id):
        raise HTTPException(status.HTTP_409_CONFLICT, "Есть банкоматы этой модели — удалить нельзя")
    db.delete(m)
    db.commit()
