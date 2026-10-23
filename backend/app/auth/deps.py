from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.permissions import Perm, perms_of
from app.auth.security import token_hash
from app.config import settings
from app.db import get_db
from app.models import User, UserSession

SESSION_COOKIE = "session"


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Требуется вход")
    now = datetime.now(UTC)
    sess = db.scalar(
        select(UserSession).where(UserSession.token_hash == token_hash(token), UserSession.expires_at > now)
    )
    if sess is None or not sess.user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Сессия истекла, войдите снова")
    ttl = timedelta(hours=settings.session_ttl_hours)
    # скользящее продление: пишем в БД не чаще, чем раз в половину срока
    if sess.expires_at - now < ttl / 2:
        sess.expires_at = now + ttl
        db.commit()
    # сессия БД общая для зависимостей и обработчика запроса — журнал изменений берёт автора отсюда
    db.info["user_id"] = sess.user.id
    return sess.user


def require(perm: Perm) -> Callable[..., User]:
    def dependency(user: User = Depends(get_current_user)) -> User:
        if perm not in perms_of(user.role):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Недостаточно прав")
        return user

    return dependency
