from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.deps import require
from app.auth.permissions import Perm
from app.db import get_db
from app.models import User
from app.services.importer import Importer, ImportFileError, read_table, template_xlsx

router = APIRouter(prefix="/import", tags=["import"])
manager = require(Perm.MANAGE_REFERENCE)


class RowOut(BaseModel):
    line: int
    atm_code: str
    action: str
    errors: list[str]
    warnings: list[str]


class PreviewOut(BaseModel):
    total: int
    create: int
    update: int
    errors: int
    warnings: int
    rows: list[RowOut]


class CommitOut(BaseModel):
    created: int
    updated: int
    unchanged: int
    skipped: int
    moved: int


async def _read(file: UploadFile) -> list[dict[str, str]]:
    try:
        return read_table(file.filename or "", await file.read())
    except ImportFileError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e


@router.get("/atms/template")
def template(db: Session = Depends(get_db), _: User = Depends(manager)) -> Response:
    return Response(
        template_xlsx(db),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="atm-import-template.xlsx"'},
    )


@router.post("/atms/preview", response_model=PreviewOut)
async def preview(file: UploadFile, db: Session = Depends(get_db), _: User = Depends(manager)) -> PreviewOut:
    results = Importer(db).validate(await _read(file))
    db.rollback()
    return PreviewOut(
        total=len(results),
        create=sum(r.action == "create" for r in results),
        update=sum(r.action == "update" for r in results),
        errors=sum(r.action == "error" for r in results),
        warnings=sum(bool(r.warnings) for r in results),
        # строки без замечаний не нужны интерфейсу — только счётчики
        rows=[RowOut(**r.__dict__) for r in results if r.errors or r.warnings],
    )


@router.post("/atms/commit", response_model=CommitOut)
async def commit(
    file: UploadFile,
    skip_errors: bool = Form(False),
    db: Session = Depends(get_db),
    user: User = Depends(manager),
) -> CommitOut:
    importer = Importer(db)
    results = importer.validate(await _read(file))
    bad = sum(r.action == "error" for r in results)
    if bad and not skip_errors:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"В файле {bad} строк с ошибками — исправьте или пропустите их"
        )
    stats = importer.apply(results, user.id)
    db.commit()
    return CommitOut(**stats)
