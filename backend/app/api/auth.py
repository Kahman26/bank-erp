import time
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.auth.deps import SESSION_COOKIE, get_current_user
from app.auth.permissions import perms_of
from app.auth.security import hash_password, new_session_token, password_problem, token_hash, verify_password
from app.config import settings
from app.db import get_db
from app.models import ROLE_LABELS, Role, User, UserSession
from app.schemas.users import MeOut

router = APIRouter(prefix="/auth", tags=["auth"])

BAD_CREDENTIALS = "Неверный логин или пароль"

# Перебор с одного IP по разным логинам. Один процесс uvicorn — хватает памяти процесса.
_IP_WINDOW_SEC = 15 * 60
_IP_MAX_FAILURES = 30
_ip_failures: dict[str, deque[float]] = defaultdict(deque)


def _ip_blocked(ip: str) -> bool:
    q = _ip_failures[ip]
    while q and q[0] < time.monotonic() - _IP_WINDOW_SEC:
        q.popleft()
    return len(q) >= _IP_MAX_FAILURES


class LoginIn(BaseModel):
    login: str
    password: str


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str


def me_out(user: User) -> MeOut:
    return MeOut(
        id=user.id,
        login=user.login,
        full_name=user.full_name,
        department=user.department,
        role=user.role,
        role_label=ROLE_LABELS[Role(user.role)],
        permissions=sorted(perms_of(user.role)),
    )


@router.post("/login", response_model=MeOut)
def login(data: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)) -> MeOut:
    ip = request.client.host if request.client else "unknown"
    if _ip_blocked(ip):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Слишком много попыток входа, попробуйте позже")

    now = datetime.now(UTC)
    user = db.scalar(select(User).where(func.lower(User.login) == data.login.strip().lower()))
    if user and user.locked_until and user.locked_until > now:
        minutes = int((user.locked_until - now).total_seconds() // 60) + 1
        raise HTTPException(status.HTTP_423_LOCKED, f"Вход временно заблокирован, повторите через {minutes} мин.")

    if user is None or not user.is_active or not verify_password(data.password, user.password_hash):
        _ip_failures[ip].append(time.monotonic())
        if user is not None:
            user.failed_logins += 1
            if user.failed_logins >= settings.login_max_failures:
                user.locked_until = now + timedelta(minutes=settings.login_lock_minutes)
                user.failed_logins = 0
            db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, BAD_CREDENTIALS)

    user.failed_logins = 0
    user.locked_until = None
    user.last_login_at = now
    token = new_session_token()
    ttl = timedelta(hours=settings.session_ttl_hours)
    db.add(
        UserSession(
            token_hash=token_hash(token),
            user_id=user.id,
            expires_at=now + ttl,
            ip=ip,
            user_agent=(request.headers.get("user-agent") or "")[:300],
        )
    )
    # заодно чистим протухшие сессии этого пользователя
    db.execute(delete(UserSession).where(UserSession.user_id == user.id, UserSession.expires_at < now))
    db.commit()
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(ttl.total_seconds()),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/api",
    )
    return me_out(user)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> None:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        db.execute(delete(UserSession).where(UserSession.token_hash == token_hash(token)))
        db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/api")


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(get_current_user)) -> MeOut:
    return me_out(user)


@router.post("/change-password", status_code=204)
def change_password(
    data: ChangePasswordIn,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    if not verify_password(data.old_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Текущий пароль указан неверно")
    if problem := password_problem(data.new_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, problem)
    user.password_hash = hash_password(data.new_password)
    # остальные сессии пользователя закрываем, текущую оставляем
    current = token_hash(request.cookies.get(SESSION_COOKIE, ""))
    db.execute(delete(UserSession).where(UserSession.user_id == user.id, UserSession.token_hash != current))
    db.commit()
