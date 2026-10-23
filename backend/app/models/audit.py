from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_log_entity", "entity", "entity_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("app_user.id", ondelete="SET NULL"))
    entity: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[int | None]
    action: Mapped[str] = mapped_column(String(10))  # create / update / delete
    # для update — {"поле": [было, стало]}, для create/delete — снимок значений
    changes: Mapped[dict] = mapped_column(JSONB, default=dict)
