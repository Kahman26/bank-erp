import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import require
from app.auth.permissions import Perm
from app.config import settings
from app.db import get_db
from app.models import Atm, AtmModel, Certificate, DictItem, Module, User
from app.services.certificates import (
    CertQuery,
    apply_filters,
    base_select,
    list_columns,
    modules_without_cert,
    summary,
)
from app.services.exports import certificates_export
from app.services.xlsx import XLSX_MEDIA, content_disposition

router = APIRouter(prefix="/certificates", tags=["certificates"])
viewer = require(Perm.VIEW)
editor = require(Perm.EDIT)

DOC_TYPES = {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png"}
MAX_DOC_BYTES = 10 * 1024 * 1024


class CertRow(BaseModel):
    id: int
    object: str
    atm_model_id: int | None
    atm_id: int | None
    atm_code: str | None
    model: str | None
    module_id: int | None
    module_type: str | None
    module_serial: str | None
    module_removed_at: date | None
    cert_type_id: int
    cert_type: str
    payment_scheme_id: int | None
    payment_scheme: str | None
    cert_number: str
    issued_at: date
    valid_until: date
    manual_status: str | None
    status: str
    needs_review: bool
    source_id: int | None
    source: str | None
    has_document: bool
    atm_count: int


class CertPage(BaseModel):
    items: list[CertRow]
    total: int


class CertIn(BaseModel):
    atm_model_id: int | None = None
    atm_id: int | None = None
    module_id: int | None = None
    cert_type_id: int
    payment_scheme_id: int | None = None
    cert_number: str = Field(min_length=1, max_length=100)
    issued_at: date
    valid_until: date
    source_id: int | None = None

    @model_validator(mode="after")
    def _check(self) -> "CertIn":
        if sum(x is not None for x in (self.atm_model_id, self.atm_id, self.module_id)) != 1:
            raise ValueError("Сертификат выдаётся ровно на один объект: модель, банкомат или узел")
        if self.valid_until < self.issued_at:
            raise ValueError("Срок действия раньше даты выдачи")
        return self


class CertPatch(BaseModel):
    needs_review: bool | None = None
    # «На продлении» / «Отозван»; пустая строка снимает ручной статус
    manual_status: str | None = Field(default=None, pattern="^(renewal|revoked|)$")


class WithoutCertRow(BaseModel):
    id: int
    serial_number: str
    installed_at: date
    module_type: str
    atm_id: int
    atm_code: str
    model: str


@router.get("", response_model=CertPage)
def list_certificates(f: CertQuery, db: Session = Depends(get_db), _: User = Depends(viewer)) -> CertPage:
    total = db.scalar(select(func.count()).select_from(apply_filters(base_select(Certificate.id), f).subquery()))
    rows = db.execute(
        apply_filters(base_select(*list_columns()), f)
        .order_by(Certificate.needs_review.desc(), Certificate.valid_until, Certificate.id)
        .offset((f.page - 1) * f.page_size)
        .limit(f.page_size)
    )
    return CertPage(items=[CertRow.model_validate(dict(r._mapping)) for r in rows], total=total or 0)


@router.get("/export.xlsx")
def export_certificates(f: CertQuery, db: Session = Depends(get_db), user: User = Depends(viewer)) -> Response:
    return Response(
        certificates_export(db, f, user), media_type=XLSX_MEDIA, headers=content_disposition("certificates.xlsx")
    )


@router.get("/summary")
def certificates_summary(db: Session = Depends(get_db), _: User = Depends(viewer)) -> dict[str, int]:
    return summary(db)


@router.get("/modules-without", response_model=list[WithoutCertRow])
def without_certificate(db: Session = Depends(get_db), _: User = Depends(viewer)) -> list[WithoutCertRow]:
    return [WithoutCertRow.model_validate(dict(r._mapping)) for r in db.execute(modules_without_cert())]


def _validate_refs(db: Session, data: CertIn) -> None:
    ctype = db.get(DictItem, data.cert_type_id)
    if ctype is None or ctype.kind != "cert_type":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Неизвестный вид сертификата")
    if ctype.code == "scheme" and data.payment_scheme_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Для сертификации в ПС укажите платёжную систему")
    for model, value, label in (
        (AtmModel, data.atm_model_id, "Модель"),
        (Atm, data.atm_id, "Банкомат"),
        (Module, data.module_id, "Узел"),
    ):
        if value is not None and db.get(model, value) is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{label} не найден(а)")


def _get(db: Session, cert_id: int) -> Certificate:
    cert = db.get(Certificate, cert_id)
    if cert is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Сертификат не найден")
    return cert


@router.post("", status_code=201)
def create_certificate(data: CertIn, db: Session = Depends(get_db), _: User = Depends(editor)) -> dict[str, int]:
    _validate_refs(db, data)
    cert = Certificate(**data.model_dump())
    db.add(cert)
    db.commit()
    return {"id": cert.id}


@router.put("/{cert_id}")
def update_certificate(
    cert_id: int, data: CertIn, db: Session = Depends(get_db), _: User = Depends(editor)
) -> dict[str, int]:
    cert = _get(db, cert_id)
    _validate_refs(db, data)
    for field, value in data.model_dump().items():
        setattr(cert, field, value)
    db.commit()
    return {"id": cert.id}


@router.patch("/{cert_id}")
def patch_certificate(
    cert_id: int, data: CertPatch, db: Session = Depends(get_db), _: User = Depends(editor)
) -> dict[str, int]:
    cert = _get(db, cert_id)
    if data.needs_review is not None:
        cert.needs_review = data.needs_review
    if data.manual_status is not None:
        cert.manual_status = data.manual_status or None
    db.commit()
    return {"id": cert.id}


@router.delete("/{cert_id}", status_code=204)
def delete_certificate(
    cert_id: int, db: Session = Depends(get_db), _: User = Depends(require(Perm.SUPERADMIN))
) -> None:
    cert = _get(db, cert_id)
    _remove_file(cert.document_path)
    db.delete(cert)
    db.commit()


# --- скан сертификата -----------------------------------------------------------------------------------


def _doc_dir() -> Path:
    path = Path(settings.upload_dir) / "certificates"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _remove_file(name: str | None) -> None:
    if name:
        (_doc_dir() / name).unlink(missing_ok=True)


@router.post("/{cert_id}/document")
async def upload_document(
    cert_id: int, file: UploadFile, db: Session = Depends(get_db), _: User = Depends(editor)
) -> dict[str, bool]:
    cert = _get(db, cert_id)
    ext = DOC_TYPES.get(file.content_type or "")
    if ext is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Скан должен быть в формате PDF, JPG или PNG")
    content = await file.read(MAX_DOC_BYTES + 1)
    if len(content) > MAX_DOC_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Файл больше 10 МБ")
    # имя файла генерируем сами: пользовательское имя в путь не попадает
    name = f"{cert.id}-{uuid.uuid4().hex}{ext}"
    (_doc_dir() / name).write_bytes(content)
    _remove_file(cert.document_path)
    cert.document_path = name
    db.commit()
    return {"ok": True}


@router.get("/{cert_id}/document")
def download_document(cert_id: int, db: Session = Depends(get_db), _: User = Depends(viewer)) -> FileResponse:
    cert = _get(db, cert_id)
    path = _doc_dir() / cert.document_path if cert.document_path else None
    if path is None or not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Скан не загружен")
    return FileResponse(path, filename=f"certificate-{cert.cert_number}{path.suffix}")
