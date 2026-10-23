from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth.deps import require
from app.auth.permissions import Perm
from app.db import get_db
from app.models import User
from app.services.reports import REPORTS, dashboard
from app.services.xlsx import XLSX_MEDIA, build_xlsx, content_disposition

router = APIRouter(prefix="/reports", tags=["reports"])
viewer = require(Perm.VIEW)


@router.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db), _: User = Depends(viewer)) -> dict:
    return dashboard(db)


@router.get("/{name}.xlsx")
def export_report(name: str, db: Session = Depends(get_db), user: User = Depends(viewer)) -> Response:
    report = REPORTS.get(name)
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Отчёт не найден")
    data = build_xlsx(
        report.title, report.columns, (tuple(r) for r in report.rows(db)), params=[("Выгрузил", user.full_name)]
    )
    return Response(data, media_type=XLSX_MEDIA, headers=content_disposition(report.filename))
