from conftest import PASSWORD, Client

from app.models import Role

NEW_USER = {"login": "kassir1", "full_name": "Каримов Азиз", "department": "Опер. блок", "role": "operator"}


def test_admin_manages_users(login_as) -> None:
    admin = login_as(Role.ADMIN)
    r = admin.post("/api/v1/users", json={**NEW_USER, "password": "Start1234"})
    assert r.status_code == 201, r.text
    uid = r.json()["id"]

    assert admin.post("/api/v1/users", json={**NEW_USER, "password": "Start1234"}).status_code == 409

    worker = Client()
    assert worker.post("/api/v1/auth/login", json={"login": "kassir1", "password": "Start1234"}).status_code == 200

    # блокировка сразу закрывает сессии
    assert admin.patch(f"/api/v1/users/{uid}", json={"is_active": False}).status_code == 200
    assert worker.get("/api/v1/auth/me").status_code == 401
    assert worker.post("/api/v1/auth/login", json={"login": "kassir1", "password": "Start1234"}).status_code == 401


def test_admin_cannot_create_superadmin(login_as) -> None:
    admin = login_as(Role.ADMIN)
    r = admin.post("/api/v1/users", json={**NEW_USER, "role": "superadmin", "password": "Start1234"})
    assert r.status_code == 403


def test_superadmin_can_create_superadmin(login_as) -> None:
    root = login_as(Role.SUPERADMIN)
    r = root.post("/api/v1/users", json={**NEW_USER, "role": "superadmin", "password": "Start1234"})
    assert r.status_code == 201


def test_weak_password_rejected(login_as) -> None:
    admin = login_as(Role.ADMIN)
    assert admin.post("/api/v1/users", json={**NEW_USER, "password": "12345678"}).status_code == 400


def test_viewer_and_operator_cannot_manage_users(login_as) -> None:
    for role in (Role.VIEWER, Role.OPERATOR):
        c = login_as(role)
        assert c.get("/api/v1/users").status_code == 403


def test_reset_password(login_as, make_user) -> None:
    admin = login_as(Role.ADMIN)
    target = make_user(Role.VIEWER, login="forgot")
    assert admin.post(f"/api/v1/users/{target.id}/reset-password", json={"password": "Fresh1234"}).status_code == 204
    c = Client()
    assert c.post("/api/v1/auth/login", json={"login": "forgot", "password": PASSWORD}).status_code == 401
    assert c.post("/api/v1/auth/login", json={"login": "forgot", "password": "Fresh1234"}).status_code == 200


def test_cannot_block_self(login_as) -> None:
    admin = login_as(Role.ADMIN)
    me = admin.get("/api/v1/auth/me").json()
    assert admin.patch(f"/api/v1/users/{me['id']}", json={"is_active": False}).status_code == 400
