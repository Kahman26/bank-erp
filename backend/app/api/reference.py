from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import require
from app.auth.permissions import Perm
from app.db import Base, get_db
from app.models import (
    Branch,
    Currency,
    DictItem,
    DictKind,
    Manufacturer,
    PaymentScheme,
    Processing,
    Region,
    User,
    Vendor,
)
from app.reference_data import DICT_KIND_LABELS
from app.schemas.reference import (
    BranchIn,
    BranchOut,
    CodeNameIn,
    CodeNameOut,
    DictItemIn,
    DictItemOut,
    DictItemPatch,
    ManufacturerIn,
    ManufacturerOut,
    ReferenceBundle,
    RegionIn,
    RegionOut,
    VendorIn,
    VendorOut,
)

router = APIRouter(prefix="/reference", tags=["reference"])
viewer = require(Perm.VIEW)
manager = require(Perm.MANAGE_REFERENCE)


@router.get("", response_model=ReferenceBundle)
def bundle(db: Session = Depends(get_db), _: User = Depends(viewer)) -> dict[str, Any]:
    dicts: dict[str, list[DictItem]] = {k.value: [] for k in DictKind}
    for item in db.scalars(select(DictItem).order_by(DictItem.kind, DictItem.sort, DictItem.name)):
        dicts.setdefault(item.kind, []).append(item)
    return {
        "dicts": dicts,
        "regions": db.scalars(select(Region).order_by(Region.sort)).all(),
        "branches": db.scalars(select(Branch).order_by(Branch.name)).all(),
        "manufacturers": db.scalars(select(Manufacturer).order_by(Manufacturer.name)).all(),
        "vendors": db.scalars(select(Vendor).order_by(Vendor.name)).all(),
        "processings": db.scalars(select(Processing).order_by(Processing.sort)).all(),
        "payment_schemes": db.scalars(select(PaymentScheme).order_by(PaymentScheme.sort)).all(),
        "currencies": db.scalars(select(Currency).order_by(Currency.sort)).all(),
        "dict_kinds": {k.value: DICT_KIND_LABELS[k] for k in DictKind},
    }


# --- простые списки ------------------------------------------------------------------------------------


@router.post("/dicts/{kind}", response_model=DictItemOut, status_code=201)
def create_dict_item(
    kind: DictKind, data: DictItemIn, db: Session = Depends(get_db), _: User = Depends(manager)
) -> DictItem:
    item = DictItem(kind=kind.value, **data.model_dump())
    db.add(item)
    db.commit()
    return item


@router.patch("/dicts/items/{item_id}", response_model=DictItemOut)
def update_dict_item(
    item_id: int, data: DictItemPatch, db: Session = Depends(get_db), _: User = Depends(manager)
) -> DictItem:
    item = db.get(DictItem, item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Значение не найдено")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    return item


# --- таблицы-справочники с атрибутами: одинаковый CRUD ------------------------------------------------


def _crud(path: str, model: type[Base], schema_in: type[BaseModel], schema_out: type[BaseModel]) -> None:
    def create(data: schema_in, db: Session = Depends(get_db), _: User = Depends(manager)):  # type: ignore[valid-type]
        obj = model(**data.model_dump())  # type: ignore[attr-defined]
        db.add(obj)
        db.commit()
        return obj

    def update(obj_id: int, data: schema_in, db: Session = Depends(get_db), _: User = Depends(manager)):  # type: ignore[valid-type]
        obj = db.get(model, obj_id)
        if obj is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Запись не найдена")
        for field, value in data.model_dump().items():  # type: ignore[attr-defined]
            setattr(obj, field, value)
        db.commit()
        return obj

    def remove(obj_id: int, db: Session = Depends(get_db), _: User = Depends(manager)) -> None:
        obj = db.get(model, obj_id)
        if obj is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Запись не найдена")
        db.delete(obj)
        db.commit()  # используемую запись не даст удалить внешний ключ → 409 (см. main.py)

    router.add_api_route(f"/{path}", create, methods=["POST"], response_model=schema_out, status_code=201)
    router.add_api_route(f"/{path}/{{obj_id}}", update, methods=["PUT"], response_model=schema_out)
    router.add_api_route(f"/{path}/{{obj_id}}", remove, methods=["DELETE"], status_code=204)


_crud("regions", Region, RegionIn, RegionOut)
_crud("branches", Branch, BranchIn, BranchOut)
_crud("manufacturers", Manufacturer, ManufacturerIn, ManufacturerOut)
_crud("vendors", Vendor, VendorIn, VendorOut)
_crud("processings", Processing, CodeNameIn, CodeNameOut)
_crud("payment-schemes", PaymentScheme, CodeNameIn, CodeNameOut)
