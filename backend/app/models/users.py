from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, false, func, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import Timestamps


class Role(StrEnum):
    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


ROLE_LABELS = {
    Role.VIEWER: "Просмотр",
    Role.OPERATOR: "Операционный блок",
    Role.ADMIN: "Администратор",
    Role.SUPERADMIN: "Суперадмин",
}


class User(Timestamps, Base):
    __tablename__ = "app_user"
    __table_args__ = (CheckConstraint(f"role in ({', '.join(repr(r.value) for r in Role)})", name="role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(64))
    full_name: Mapped[str] = mapped_column(String(200))
    department: Mapped[str | None] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_logins: Mapped[int] = mapped_column(default=0, server_default="0")
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # пароль задал администратор — при входе сотрудник обязан сменить его на свой
    must_change_password: Mapped[bool] = mapped_column(default=False, server_default=false())

    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")


# логин уникален без учёта регистра
Index("uq_app_user_login_lower", func.lower(User.login), unique=True)


class UserSession(Base):
    __tablename__ = "user_session"

    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(300))

    user: Mapped[User] = relationship(back_populates="sessions")
