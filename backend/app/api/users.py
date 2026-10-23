from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.auth.deps import require
from app.auth.permissions import Perm, perms_of
from app.auth.security import hash_password, password_problem
from app.db import get_db
from app.models import ROLE_LABELS, Role, User, UserSession
from app.schemas.users import PasswordReset, UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


def _check_can_manage(actor: User, target_role: str) -> None:
    """Суперадмина назначает и меняет только суперадмин."""
    if target_role == Role.SUPERADMIN and Perm.SUPERADMIN not in perms_of(actor.role):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Только суперадмин управляет суперадминами")


def _get(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")
    return user


@router.get("/roles")
def roles(_: User = Depends(require(Perm.MANAGE_USERS))) -> list[dict[str, str]]:
    return [{"value": r.value, "label": ROLE_LABELS[r]} for r in Role]


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require(Perm.MANAGE_USERS))) -> list[User]:
    return list(db.scalars(select(User).order_by(User.full_name)))


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    data: UserCreate, db: Session = Depends(get_db), actor: User = Depends(require(Perm.MANAGE_USERS))
) -> User:
    _check_can_manage(actor, data.role)
    if problem := password_problem(data.password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, problem)
    if db.scalar(select(User.id).where(func.lower(User.login) == data.login.lower())):
        raise HTTPException(status.HTTP_409_CONFLICT, "Пользователь с таким логином уже есть")
    user = User(
        login=data.login,
        full_name=data.full_name,
        department=data.department,
        role=data.role,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require(Perm.MANAGE_USERS)),
) -> User:
    user = _get(db, user_id)
    _check_can_manage(actor, user.role)
    if data.role is not None:
        _check_can_manage(actor, data.role)
    if user.id == actor.id and (data.is_active is False or (data.role and data.role != actor.role)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Нельзя заблокировать себя или сменить себе роль")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    if data.is_active is False:
        db.execute(delete(UserSession).where(UserSession.user_id == user.id))
    if data.is_active:
        user.locked_until = None
        user.failed_logins = 0
    db.commit()
    return user


@router.post("/{user_id}/reset-password", status_code=204)
def reset_password(
    user_id: int,
    data: PasswordReset,
    db: Session = Depends(get_db),
    actor: User = Depends(require(Perm.MANAGE_USERS)),
) -> None:
    user = _get(db, user_id)
    _check_can_manage(actor, user.role)
    if problem := password_problem(data.password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, problem)
    user.password_hash = hash_password(data.password)
    user.locked_until = None
    user.failed_logins = 0
    db.execute(delete(UserSession).where(UserSession.user_id == user.id))
    db.commit()
