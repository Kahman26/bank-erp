from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Certificate, PaymentScheme, Role
from seed.writer import ensure_base

TODAY = date.today()


def _ids(client) -> dict:
    ref = client.get("/api/v1/reference").json()
    ids = {f"{kind}:{d['code']}": d["id"] for kind, items in ref["dicts"].items() for d in items}
    ids["region"] = ref["regions"][0]["id"]
    ids["branch"] = ref["branches"][0]["id"]
    ids["vendor"] = next(v["id"] for v in ref["vendors"] if v["is_service"])
    return ids


def _location(ids: dict, lat: float = 41.31, address: str = "ул. Амира Темура, 1") -> dict:
    return {
        "name": "ТЦ «Бахор»",
        "region_id": ids["region"],
        "city_district": "Юнусабадский район",
        "address": address,
        "latitude": lat,
        "longitude": 69.24,
        "place_type_id": ids["place_type:mall"],
        "working_hours": "Ежедневно 10:00–22:00",
    }


def _new_atm(admin, ids: dict) -> dict:
    model = admin.get("/api/v1/atm-models").json()[0]
    r = admin.post(
        "/api/v1/atms",
        json={
            "atm_code": "ATM-TAS-7001",
            "serial_number": "LC-1",
            "model_id": model["id"],
            "device_type_id": model["device_type_id"],
            "install_format_id": ids["install_format:lobby"],
            "branch_id": ids["branch"],
            "purchase_date": str(TODAY - timedelta(days=400)),
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _setup(login_as):
    with SessionLocal() as db:
        ensure_base(db)  # модели, филиалы, вендоры
        db.commit()
    admin = login_as(Role.ADMIN)
    ids = _ids(admin)
    card = _new_atm(admin, ids)
    return admin, login_as(Role.OPERATOR), ids, card["id"]


def test_full_lifecycle(login_as) -> None:
    _, op, ids, atm = _setup(login_as)
    url = f"/api/v1/atms/{atm}"

    # со склада сразу в эксплуатацию нельзя; в установку — только с местом
    r = op.post(f"{url}/status", json={"status_id": ids["atm_status:in_service"]})
    assert r.status_code == 400 and "нельзя перейти" in r.json()["detail"]
    r = op.post(f"{url}/status", json={"status_id": ids["atm_status:installing"]})
    assert r.status_code == 400 and "место установки" in r.json()["detail"]

    # установка на место сразу со статусом «В установке»
    start = TODAY - timedelta(days=300)
    r = op.post(
        f"{url}/move",
        json={"location": _location(ids), "placed_from": str(start), "set_status_id": ids["atm_status:installing"]},
    )
    assert r.status_code == 200, r.text
    card = r.json()
    assert card["header"]["status_code"] == "installing" and card["location"]["address"] == "ул. Амира Темура, 1"

    r = op.post(f"{url}/status", json={"status_id": ids["atm_status:in_service"], "effective_date": str(start)})
    assert r.json()["main"]["commissioning_date"] == str(start)

    # перемещение: дата не раньше начала текущего размещения
    r = op.post(f"{url}/move", json={"location": _location(ids, 41.35), "placed_from": str(start)})
    assert r.status_code == 400
    moved_on = TODAY - timedelta(days=100)
    r = op.post(
        f"{url}/move",
        json={
            "location": _location(ids, 41.35, "ул. Навои, 5"),
            "placed_from": str(moved_on),
            "move_reason_id": ids["move_reason:low_load"],
        },
    )
    card = r.json()
    assert len(card["placements"]) == 2 and card["location"]["address"] == "ул. Навои, 5"
    assert card["placements"][1]["placed_to"] == str(moved_on)

    # списание закрывает размещение
    op.post(f"{url}/status", json={"status_id": ids["atm_status:to_writeoff"]})
    card = op.post(f"{url}/status", json={"status_id": ids["atm_status:written_off"]}).json()
    assert card["location"] is None and card["main"]["decommission_date"] == str(TODAY)
    assert card["header"]["allowed_status_ids"] == []
    assert op.post(f"{url}/move", json={"location": _location(ids), "placed_from": str(TODAY)}).status_code == 400


def test_repair_with_card_reader_replacement(login_as) -> None:
    _, op, ids, atm = _setup(login_as)
    url = f"/api/v1/atms/{atm}"
    start = TODAY - timedelta(days=200)
    op.post(
        f"{url}/move",
        json={"location": _location(ids), "placed_from": str(start), "set_status_id": ids["atm_status:installing"]},
    )
    op.post(f"{url}/status", json={"status_id": ids["atm_status:in_service"]})
    card = op.post(
        f"{url}/modules",
        json={"module_type_id": ids["module_type:card_reader"], "serial_number": "CR-OLD", "installed_at": str(start)},
    ).json()
    reader = next(m for m in card["modules"] if m["serial_number"] == "CR-OLD")
    with SessionLocal() as db:  # сертификат EMV L1 на старый картридер
        db.add(
            Certificate(
                module_id=reader["id"],
                cert_type_id=ids["cert_type:emv_l1_contact"],
                payment_scheme_id=db.scalar(select(PaymentScheme.id).limit(1)),
                cert_number="LOA-1",
                issued_at=start,
                valid_until=start + timedelta(days=1000),
            )
        )
        db.commit()

    started = datetime.now(UTC) - timedelta(hours=5)
    r = op.post(
        f"{url}/service-events",
        json={
            "event_type_id": ids["service_event_type:module_replacement"],
            "started_at": started.isoformat(),
            "problem": "Картридер не возвращает карту",
            "vendor_id": ids["vendor"],
            "ticket_number": "SV-1",
            "replacements": [{"removed_module_id": reader["id"], "serial_number": "CR-NEW"}],
            "set_repair_status": True,
        },
    )
    assert r.status_code == 201, r.text
    card = r.json()
    assert card["header"]["status_code"] == "vendor_repair"
    event = card["service_events"][0]
    assert event["affects_certification"] and event["finished_at"] is None
    assert event["replacements"][0]["installed"].endswith("CR-NEW")
    serials = {m["serial_number"]: m for m in card["modules"]}
    assert serials["CR-OLD"]["removed_at"] == str(started.date()) and serials["CR-NEW"]["removed_at"] is None
    assert any(c["needs_review"] for c in card["certificates"])

    # повторно снять уже снятый узел нельзя
    r = op.post(
        f"{url}/service-events",
        json={
            "event_type_id": ids["service_event_type:module_replacement"],
            "started_at": started.isoformat(),
            "problem": "x",
            "by_bank_engineer": True,
            "replacements": [{"removed_module_id": reader["id"], "serial_number": "CR-3"}],
        },
    )
    assert r.status_code == 400

    # закрытие ремонта с возвратом в эксплуатацию
    r = op.post(
        f"{url}/service-events/{event['id']}/close",
        json={
            "finished_at": datetime.now(UTC).isoformat(),
            "work_done": "Картридер заменён",
            "return_to_service": True,
        },
    )
    card = r.json()
    assert card["header"]["status_code"] == "in_service"
    assert card["service_events"][0]["downtime_hours"] >= 4.9
    assert (
        op.post(
            f"{url}/service-events/{event['id']}/close", json={"finished_at": datetime.now(UTC).isoformat()}
        ).status_code
        == 400
    )


def test_event_requires_performer_and_software_history(login_as) -> None:
    _, op, ids, atm = _setup(login_as)
    url = f"/api/v1/atms/{atm}"
    r = op.post(
        f"{url}/service-events",
        json={
            "event_type_id": ids["service_event_type:breakdown"],
            "started_at": datetime.now(UTC).isoformat(),
            "problem": "x",
        },
    )
    assert r.status_code == 422
    for version in ("4.4", "4.5"):
        card = op.post(
            f"{url}/software",
            json={"software_type_id": ids["software_type:client"], "name": "KAL Kalignite", "version": version},
        ).json()
    assert [s["version"] for s in card["software"]] == ["4.4", "4.5"]


def test_viewer_cannot_run_operations(login_as) -> None:
    _, _, ids, atm = _setup(login_as)
    viewer = login_as(Role.VIEWER)
    r = viewer.post(f"/api/v1/atms/{atm}/status", json={"status_id": ids["atm_status:in_delivery"]})
    assert r.status_code == 403
