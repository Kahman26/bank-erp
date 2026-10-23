from datetime import date

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.db import SessionLocal
from app.models import AuditLog, Role


def test_bundle_contains_base_reference(login_as) -> None:
    data = login_as(Role.VIEWER).get("/api/v1/reference").json()
    statuses = [i["name"] for i in data["dicts"]["atm_status"]]
    assert statuses[0] == "На складе банка" and "На ремонте у вендора" in statuses
    assert [s["name"] for s in data["payment_schemes"]] == ["Uzcard", "Humo", "Visa", "Mastercard", "UnionPay"]
    assert len(data["regions"]) == 14
    assert [p["code"] for p in data["processings"]] == ["own", "uzcard", "humo"]


def test_viewer_cannot_edit_reference(login_as) -> None:
    r = login_as(Role.VIEWER).post("/api/v1/reference/manufacturers", json={"name": "NCR Atleos"})
    assert r.status_code == 403


def test_admin_edits_reference_and_it_is_audited(login_as) -> None:
    admin = login_as(Role.ADMIN)
    region_id = admin.get("/api/v1/reference").json()["regions"][0]["id"]
    r = admin.post("/api/v1/reference/branches", json={"name": "Юнусабадский филиал", "region_id": region_id})
    assert r.status_code == 201
    bid = r.json()["id"]
    r = admin.put(f"/api/v1/reference/branches/{bid}", json={"name": "Юнусабадский филиал №2", "region_id": region_id})
    assert r.json()["name"] == "Юнусабадский филиал №2"

    with SessionLocal() as db:
        log = db.scalars(select(AuditLog).where(AuditLog.entity == "branch").order_by(AuditLog.id)).all()
    assert [entry.action for entry in log] == ["create", "update"]
    assert log[1].changes["name"] == ["Юнусабадский филиал", "Юнусабадский филиал №2"]
    assert log[1].user_id is not None

    # регион используется филиалом — удалить нельзя
    assert admin.delete(f"/api/v1/reference/regions/{region_id}").status_code == 409


def test_dict_item_create_and_deactivate(login_as) -> None:
    admin = login_as(Role.ADMIN)
    r = admin.post("/api/v1/reference/dicts/place_type", json={"code": "hotel", "name": "Гостиница", "sort": 99})
    assert r.status_code == 201
    r = admin.patch(f"/api/v1/reference/dicts/items/{r.json()['id']}", json={"is_active": False})
    assert r.json()["is_active"] is False


def _model_payload(admin) -> dict:
    ref = admin.get("/api/v1/reference").json()
    manufacturer = admin.post("/api/v1/reference/manufacturers", json={"name": "Hyosung TNS"}).json()
    recycler = next(d for d in ref["dicts"]["device_type"] if d["code"] == "recycler")
    return {
        "manufacturer_id": manufacturer["id"],
        "model_name": "MX8300D",
        "device_type_id": recycler["id"],
        "recycling": True,
        "cash_in": True,
        "max_cassettes": 5,
        "warranty_months": 24,
        "end_of_support_date": "2031-12-31",
    }


def test_atm_model_crud(login_as) -> None:
    admin = login_as(Role.ADMIN)
    payload = _model_payload(admin)
    r = admin.post("/api/v1/atm-models", json=payload)
    assert r.status_code == 201, r.text
    model = r.json()
    assert model["manufacturer_name"] == "Hyosung TNS" and model["device_type_name"] == "Ресайклер"

    assert admin.post("/api/v1/atm-models", json=payload).status_code == 409  # та же модель того же производителя

    r = admin.put(f"/api/v1/atm-models/{model['id']}", json={**payload, "warranty_months": 36})
    assert r.json()["warranty_months"] == 36
    assert len(login_as(Role.VIEWER).get("/api/v1/atm-models").json()) == 1
    assert admin.delete(f"/api/v1/atm-models/{model['id']}").status_code == 204


# --- ограничения целостности на уровне БД ------------------------------------------------------------


def _atm_and_location(db) -> tuple[int, int]:
    """Минимальный банкомат и локация прямым SQL — API банкоматов появится на этапе 3."""
    ids = dict(db.execute(text("select kind || ':' || code, id from dict_item")).all())
    region = db.execute(text("select id from region limit 1")).scalar()
    db.execute(text("insert into manufacturer (name) values ('NCR Atleos')"))
    db.execute(
        text(
            "insert into atm_model (manufacturer_id, model_name, device_type_id, recycling, cash_in) "
            "values ((select id from manufacturer), 'SelfServ 84', :dt, false, false)"
        ),
        {"dt": ids["device_type:dispenser"]},
    )
    db.execute(text("insert into branch (name, region_id) values ('Филиал', :r)"), {"r": region})
    atm_id = db.execute(
        text(
            "insert into atm (atm_code, serial_number, model_id, device_type_id, install_format_id, status_id, "
            "branch_id, contactless) values ('ATM-1', 'SN-1', (select id from atm_model), :dt, :inst, :st, "
            "(select id from branch), false) returning id"
        ),
        {"dt": ids["device_type:dispenser"], "inst": ids["install_format:lobby"], "st": ids["atm_status:in_service"]},
    ).scalar()
    loc_id = db.execute(
        text(
            "insert into location (name, region_id, city_district, address, latitude, longitude, place_type_id, "
            "indoor, is_24h, working_hours) values ('ТЦ', :r, 'Юнусабадский район', 'ул. 1', 41.31, 69.24, :pt, "
            "true, true, '24/7') returning id"
        ),
        {"r": region, "pt": ids["place_type:mall"]},
    ).scalar()
    return atm_id, loc_id


def test_placements_cannot_overlap() -> None:
    with SessionLocal() as db:
        atm_id, loc_id = _atm_and_location(db)
        insert = text("insert into placement (atm_id, location_id, placed_from, placed_to) values (:a, :l, :f, :t)")
        db.execute(insert, {"a": atm_id, "l": loc_id, "f": date(2024, 1, 1), "t": date(2024, 6, 1)})
        db.execute(insert, {"a": atm_id, "l": loc_id, "f": date(2024, 6, 1), "t": None})  # стык допустим
        db.commit()
        with pytest.raises(IntegrityError):
            db.execute(insert, {"a": atm_id, "l": loc_id, "f": date(2024, 3, 1), "t": date(2024, 4, 1)})
        db.rollback()


def test_location_must_be_in_uzbekistan() -> None:
    with SessionLocal() as db:
        _atm_and_location(db)
        db.commit()
        with pytest.raises(IntegrityError):
            # перепутаны широта и долгота
            db.execute(
                text(
                    "insert into location (name, region_id, city_district, address, latitude, longitude, "
                    "place_type_id, indoor, is_24h, working_hours) select name, region_id, city_district, address, "
                    "69.24, 41.31, place_type_id, indoor, is_24h, working_hours from location limit 1"
                )
            )
        db.rollback()


def test_certificate_has_exactly_one_object() -> None:
    with SessionLocal() as db:
        atm_id, _ = _atm_and_location(db)
        db.commit()
        with pytest.raises(IntegrityError):
            db.execute(
                text(
                    "insert into certificate (atm_model_id, atm_id, cert_type_id, payment_scheme_id, cert_number, "
                    "issued_at, valid_until) values ((select id from atm_model), :a, "
                    "(select id from dict_item where kind='cert_type' limit 1), (select id from payment_scheme "
                    "limit 1), 'LOA-1', '2025-01-01', '2027-01-01')"
                ),
                {"a": atm_id},
            )
        db.rollback()
