import hashlib
import secrets

from pwdlib import PasswordHash

_hasher = PasswordHash.recommended()  # argon2id

MIN_PASSWORD_LENGTH = 8


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _hasher.verify(password, password_hash)


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    """В БД храним только хэш токена: утечка таблицы сессий не даёт войти."""
    return hashlib.sha256(token.encode()).hexdigest()


def password_problem(password: str) -> str | None:
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Пароль должен быть не короче {MIN_PASSWORD_LENGTH} символов"
    if password.isdigit() or password.isalpha():
        return "Пароль должен содержать и буквы, и цифры"
    return None
