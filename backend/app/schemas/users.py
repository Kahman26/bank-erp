from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.users import Role


class MeOut(BaseModel):
    id: int
    login: str
    full_name: str
    department: str | None
    role: str
    role_label: str
    permissions: list[str]
    must_change_password: bool = False


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    login: str
    full_name: str
    department: str | None
    role: Role
    is_active: bool
    last_login_at: datetime | None
    locked_until: datetime | None
    created_at: datetime
    must_change_password: bool
    active_sessions: int = 0


class UserCreate(BaseModel):
    login: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    full_name: str = Field(min_length=2, max_length=200)
    department: str | None = Field(default=None, max_length=200)
    role: Role
    password: str


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    department: str | None = Field(default=None, max_length=200)
    role: Role | None = None
    is_active: bool | None = None


class PasswordReset(BaseModel):
    password: str
