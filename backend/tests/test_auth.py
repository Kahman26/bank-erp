from conftest import PASSWORD, Client

from app.models import Role


def test_login_me_logout(make_user) -> None:
    make_user(Role.OPERATOR, login="Ivanov")
    c = Client()
    r = c.post("/api/v1/auth/login", json={"login": "ivanov", "password": PASSWORD})  # без учёта регистра
    assert r.status_code == 200
    assert r.json()["role_label"] == "Операционный блок"
    assert "operate" in r.json()["permissions"]
    assert c.get("/api/v1/auth/me").json()["login"] == "Ivanov"

    assert c.post("/api/v1/auth/logout").status_code == 204
    assert c.get("/api/v1/auth/me").status_code == 401


def test_data_requires_login() -> None:
    assert Client().get("/api/v1/reference").status_code == 401


def test_wrong_password_and_lockout(make_user) -> None:
    make_user(Role.VIEWER, login="petrov")
    c = Client()
    for _ in range(5):
        r = c.post("/api/v1/auth/login", json={"login": "petrov", "password": "wrong-pass1"})
        assert r.status_code == 401
        assert r.json()["detail"] == "Неверный логин или пароль"
    # после 5 ошибок блокируется даже правильный пароль
    r = c.post("/api/v1/auth/login", json={"login": "petrov", "password": PASSWORD})
    assert r.status_code == 423


def test_unknown_user_gets_same_message() -> None:
    r = Client().post("/api/v1/auth/login", json={"login": "nobody", "password": "x"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Неверный логин или пароль"


def test_mutation_without_fetch_header_rejected(make_user) -> None:
    make_user(Role.VIEWER, login="sidorov")
    r = TestClientNoHeader().post("/api/v1/auth/login", json={"login": "sidorov", "password": PASSWORD})
    assert r.status_code == 403


def test_change_password(login_as) -> None:
    c = login_as(Role.VIEWER)
    r = c.post("/api/v1/auth/change-password", json={"old_password": "bad", "new_password": "NewPass123"})
    assert r.status_code == 400
    r = c.post("/api/v1/auth/change-password", json={"old_password": PASSWORD, "new_password": "short"})
    assert r.status_code == 400
    r = c.post("/api/v1/auth/change-password", json={"old_password": PASSWORD, "new_password": "NewPass123"})
    assert r.status_code == 204
    assert c.get("/api/v1/auth/me").status_code == 200  # текущая сессия жива
    r = Client().post("/api/v1/auth/login", json={"login": "viewer_user", "password": "NewPass123"})
    assert r.status_code == 200


class TestClientNoHeader(Client):
    def __init__(self) -> None:
        super().__init__()
        del self.headers["X-Requested-With"]
