from conftest import PASSWORD, Client
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Role, User


def test_login_events_and_superadmin_only(login_as, make_user) -> None:
    make_user(Role.VIEWER, login="guest")
    Client().post("/api/v1/auth/login", json={"login": "guest", "password": "wrong-1"})
    Client().post("/api/v1/auth/login", json={"login": "guest", "password": PASSWORD})
    root = login_as(Role.SUPERADMIN)
    rows = root.get("/api/v1/audit", params={"entity": "auth"}).json()["items"]
    actions = [r["action"] for r in rows]
    assert "login" in actions and "login_fail" in actions
    fail = next(r for r in rows if r["action"] == "login_fail")
    assert fail["action_label"] == "Неудачный вход" and any(c["field"] == "ip" for c in fail["changes"])
    assert login_as(Role.ADMIN).get("/api/v1/audit").status_code == 403


def test_atm_history_is_linked_and_readable(login_as) -> None:
    admin = login_as(Role.ADMIN)
    ref = admin.get("/api/v1/reference").json()
    model = admin.post("/api/v1/reference/manufacturers", json={"name": "GRG Banking"}).json()
    dt = ref["dicts"]["device_type"][0]["id"]
    m = admin.post(
        "/api/v1/atm-models", json={"manufacturer_id": model["id"], "model_name": "H68N", "device_type_id": dt}
    ).json()
    region = ref["regions"][0]["id"]
    branch = admin.post("/api/v1/reference/branches", json={"name": "Тестовый филиал", "region_id": region}).json()
    atm = admin.post(
        "/api/v1/atms",
        json={
            "atm_code": "ATM-AUD-1",
            "serial_number": "AUD-1",
            "model_id": m["id"],
            "device_type_id": dt,
            "install_format_id": ref["dicts"]["install_format"][0]["id"],
            "branch_id": branch["id"],
        },
    ).json()
    admin.post(
        f"/api/v1/atms/{atm['id']}/modules",
        json={"module_type_id": ref["dicts"]["module_type"][0]["id"], "serial_number": "CR-1"},
    )
    in_delivery = next(d["id"] for d in ref["dicts"]["atm_status"] if d["code"] == "in_delivery")
    admin.post(f"/api/v1/atms/{atm['id']}/status", json={"status_id": in_delivery})

    root = login_as(Role.SUPERADMIN)
    rows = root.get("/api/v1/audit", params={"atm_id": atm["id"]}).json()["items"]
    entities = {r["entity"] for r in rows}
    assert {"atm", "module"} <= entities and all(r["atm_code"] == "ATM-AUD-1" for r in rows)
    status_change = next(r for r in rows if r["entity"] == "atm" and r["action"] == "update")
    change = next(c for c in status_change["changes"] if c["field"] == "status_id")
    assert change["label"] == "Статус" and change["old"] == "На складе банка" and change["new"] == "В доставке"
    assert status_change["user"] == "Тест admin"


def test_temporary_password_must_be_changed(login_as) -> None:
    admin = login_as(Role.ADMIN)
    admin.post(
        "/api/v1/users",
        json={"login": "newbie", "full_name": "Новый сотрудник", "role": "viewer", "password": "Temp12345"},
    )
    c = Client()
    me = c.post("/api/v1/auth/login", json={"login": "newbie", "password": "Temp12345"}).json()
    assert me["must_change_password"] is True
    r = c.get("/api/v1/atms")
    assert r.status_code == 403 and "временный пароль" in r.json()["detail"]
    same = c.post("/api/v1/auth/change-password", json={"old_password": "Temp12345", "new_password": "Temp12345"})
    assert same.status_code == 400
    assert (
        c.post(
            "/api/v1/auth/change-password", json={"old_password": "Temp12345", "new_password": "Mine12345"}
        ).status_code
        == 204
    )
    assert c.get("/api/v1/atms").status_code == 200

    # сброс пароля администратором снова требует смены
    with SessionLocal() as db:
        uid = db.scalar(select(User.id).where(User.login == "newbie"))
    admin.post(f"/api/v1/users/{uid}/reset-password", json={"password": "Reset1234"})
    me = Client().post("/api/v1/auth/login", json={"login": "newbie", "password": "Reset1234"}).json()
    assert me["must_change_password"] is True


def test_terminate_sessions(login_as, make_user) -> None:
    user = make_user(Role.VIEWER, login="phone_lost")
    a, b = Client(), Client()
    for c in (a, b):
        c.post("/api/v1/auth/login", json={"login": "phone_lost", "password": PASSWORD})
    admin = login_as(Role.ADMIN)
    row = next(u for u in admin.get("/api/v1/users").json() if u["login"] == "phone_lost")
    assert row["active_sessions"] == 2
    assert admin.post(f"/api/v1/users/{user.id}/terminate-sessions").status_code == 204
    assert a.get("/api/v1/auth/me").status_code == 401 and b.get("/api/v1/auth/me").status_code == 401
