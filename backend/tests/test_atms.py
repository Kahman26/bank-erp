from sqlalchemy import select

from app.db import SessionLocal
from app.models import AuditLog, Role
from seed.generator import Generator
from seed.writer import ensure_base, id_allocator, write_db


def _seed(count: int = 40) -> None:
    with SessionLocal() as db:
        ref = ensure_base(db)
        write_db(db, Generator(ref, id_allocator(db), 11).run(count))
        db.commit()


def test_list_pagination_sort_and_search(login_as) -> None:
    _seed()
    c = login_as(Role.VIEWER)
    page = c.get("/api/v1/atms", params={"page_size": 10, "sort": "atm_code"}).json()
    assert page["total"] == 40 and len(page["items"]) == 10
    codes = [r["atm_code"] for r in page["items"]]
    assert codes == sorted(codes)

    code = page["items"][3]["atm_code"]
    found = c.get("/api/v1/atms", params={"q": code.lower()}).json()
    assert [r["atm_code"] for r in found["items"]] == [code]

    tid = next(r["terminal_id"] for r in page["items"] if r["terminal_id"])
    assert c.get("/api/v1/atms", params={"q": tid}).json()["total"] == 1


def test_filters(login_as) -> None:
    _seed()
    c = login_as(Role.VIEWER)
    ref = c.get("/api/v1/reference").json()
    in_service = next(d["id"] for d in ref["dicts"]["atm_status"] if d["code"] == "in_service")
    tashkent = next(r["id"] for r in ref["regions"] if r["code"] == "tashkent_city")

    rows = c.get("/api/v1/atms", params={"status_id": in_service, "page_size": 500}).json()["items"]
    assert rows and all(r["status_code"] == "in_service" for r in rows)

    rows = c.get("/api/v1/atms", params={"region_id": tashkent, "page_size": 500}).json()["items"]
    assert all(r["region"] == "г. Ташкент" for r in rows)

    usd = c.get("/api/v1/atms", params={"currency": "USD", "page_size": 500}).json()["items"]
    assert all("USD" in (r["currencies"] or "") for r in usd)

    both = c.get("/api/v1/atms", params=[("status_id", in_service), ("contactless", "true")]).json()["items"]
    assert all(r["contactless"] for r in both)

    for params in ({"cert_expiring_days": 90}, {"warranty_expiring_days": 365}, {"repair_over_days": 0}):
        assert c.get("/api/v1/atms", params=params).status_code == 200


def test_map_uses_same_filters(login_as) -> None:
    _seed()
    c = login_as(Role.VIEWER)
    data = c.get("/api/v1/atms/map").json()
    assert data["total"] == 40
    assert len(data["points"]) + data["without_location"] == 40
    atm_id, code, lat, lon, status = data["points"][0]
    assert 37 < lat < 46 and 55 < lon < 74 and code.startswith("ATM-")


def test_card(login_as) -> None:
    _seed()
    viewer = login_as(Role.VIEWER)
    atm_id = viewer.get("/api/v1/atms/map").json()["points"][0][0]
    card = viewer.get(f"/api/v1/atms/{atm_id}").json()
    assert card["location"] is not None
    assert card["modules"] and card["software"] and card["status_history"]
    assert {c["object"] for c in card["certificates"]} >= {"model"}
    # IP-адрес процессинга скрыт от просмотра
    assert all(p["ip_address"] is None for p in card["processings"])
    assert viewer.get("/api/v1/atms/999999").status_code == 404


def test_create_update_and_processings(login_as) -> None:
    _seed(5)
    admin = login_as(Role.ADMIN)
    ref = admin.get("/api/v1/reference").json()
    model = admin.get("/api/v1/atm-models").json()[0]
    payload = {
        "atm_code": "ATM-TAS-9001",
        "serial_number": "TEST-SN-1",
        "model_id": model["id"],
        "device_type_id": model["device_type_id"],
        "install_format_id": ref["dicts"]["install_format"][0]["id"],
        "branch_id": ref["branches"][0]["id"],
        "currencies": ["UZS", "USD"],
        "contactless": True,
    }
    r = admin.post("/api/v1/atms", json=payload)
    assert r.status_code == 201, r.text
    card = r.json()
    assert card["header"]["status_code"] == "in_stock"
    assert card["main"]["currencies"] == ["UZS", "USD"]  # порядок справочника валют

    assert admin.post("/api/v1/atms", json=payload).status_code == 409  # дубль кода

    r = admin.put(f"/api/v1/atms/{card['id']}", json={**payload, "currencies": ["UZS"], "cassette_count": 5})
    assert r.json()["config"]["cassette_count"] == 5 and r.json()["main"]["currencies"] == ["UZS"]

    own, uzcard = ref["processings"][0]["id"], ref["processings"][1]["id"]
    procs = [
        {"processing_id": own, "terminal_id": "T-1", "merchant_id": "M-1", "ip_address": "10.0.0.5"},
        {"processing_id": uzcard, "terminal_id": "T-1", "merchant_id": "M-1"},  # в другом процессинге можно
    ]
    r = admin.put(f"/api/v1/atms/{card['id']}/processings", json=procs)
    assert r.status_code == 200 and r.json()["processings"][0]["ip_address"] == "10.0.0.5"

    # тот же Terminal ID в том же процессинге у другого банкомата — конфликт
    other = admin.post("/api/v1/atms", json={**payload, "atm_code": "ATM-TAS-9002", "serial_number": "TEST-SN-2"})
    r = admin.put(f"/api/v1/atms/{other.json()['id']}/processings", json=procs[:1])
    assert r.status_code == 409

    with SessionLocal() as db:
        actions = db.scalars(select(AuditLog.action).where(AuditLog.entity == "atm")).all()
    assert actions.count("create") == 2 and "update" in actions


def test_viewer_and_operator_cannot_edit_atm(login_as) -> None:
    _seed(3)
    for role in (Role.VIEWER, Role.OPERATOR):
        c = login_as(role)
        atm_id = c.get("/api/v1/atms").json()["items"][0]["id"]
        card = c.get(f"/api/v1/atms/{atm_id}").json()
        assert c.put(f"/api/v1/atms/{atm_id}", json=card["edit"]).status_code == 403
