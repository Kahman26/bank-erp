import os

# База для тестов задаётся до импорта приложения: движок создаётся при импорте app.db
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or os.environ["DATABASE_URL"]
assert "test" in os.environ["DATABASE_URL"].rsplit("/", 1)[-1], "тесты очищают БД — нужна отдельная тестовая база"

from collections.abc import Callable, Iterator  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.auth.security import hash_password  # noqa: E402
from app.cli import load_reference  # noqa: E402
from app.db import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Role, User  # noqa: E402

PASSWORD = "Secret123"
# таблицы, которые наполняют тесты; справочники из bootstrap не трогаем
MUTABLE = (
    "audit_log, user_session, app_user, certificate, contract, module_replacement, service_event, "
    "placement, location, software, module, atm_processing, atm_status_history, atm_currency, atm_service, "
    "atm_scheme, atm, atm_model, manufacturer, branch, vendor"
)


@pytest.fixture(scope="session", autouse=True)
def database() -> None:
    with engine.begin() as conn:
        conn.execute(text("drop schema public cascade; create schema public"))
    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "alembic"))
    command.upgrade(cfg, "head")
    with SessionLocal() as db:
        load_reference(db)
        db.commit()


@pytest.fixture(autouse=True)
def clean() -> Iterator[None]:
    yield
    with engine.begin() as conn:
        conn.execute(text(f"truncate {MUTABLE} restart identity cascade"))


class Client(TestClient):
    """Клиент как фронтенд: с заголовком X-Requested-With."""

    def __init__(self) -> None:
        super().__init__(app, headers={"X-Requested-With": "fetch"})


@pytest.fixture
def make_user() -> Callable[..., User]:
    def factory(role: Role = Role.VIEWER, login: str | None = None) -> User:
        with SessionLocal() as db:
            user = User(
                login=login or f"{role.value}_user",
                full_name=f"Тест {role.value}",
                role=role,
                password_hash=hash_password(PASSWORD),
            )
            db.add(user)
            db.commit()
            return user

    return factory


@pytest.fixture
def login_as(make_user: Callable[..., User]) -> Callable[[Role], Client]:
    def factory(role: Role) -> Client:
        user = make_user(role)
        client = Client()
        r = client.post("/api/v1/auth/login", json={"login": user.login, "password": PASSWORD})
        assert r.status_code == 200, r.text
        return client

    return factory
