from datetime import date, timedelta

from sqlalchemy import select

from app.db import SessionLocal
from app.models import AtmModel, Certificate, Role
from seed.generator import Generator
from seed.writer import ensure_base, id_allocator, write_db

TODAY = date.today()


def _seed(count: int = 25) -> None:
    with SessionLocal() as db:
        ref = ensure_base(db)
        write_db(db, Generator(ref, id_allocator(db), 21).run(count))
        db.commit()


def _ids(client) -> dict:
    ref = client.get("/api/v1/reference").json()
    ids = {f"{kind}:{d['code']}": d["id"] for kind, items in ref["dicts"].items() for d in items}
    ids.update({f"scheme:{s['code']}": s["id"] for s in ref["payment_schemes"]})
    return ids


def test_registry_statuses_and_summary(login_as) -> None:
    _seed()
    c = login_as(Role.VIEWER)
    summary = c.get("/api/v1/certificates/summary").json()
    page = c.get("/api/v1/certificates", params={"page_size": 500}).json()
    assert page["total"] == sum(summary[s] for s in ("valid", "expiring", "expired", "renewal", "revoked"))

    for status in ("valid", "expiring", "expired"):
        rows = c.get("/api/v1/certificates", params={"status": status, "page_size": 500}).json()["items"]
        assert all(r["status"] == status for r in rows)
        for r in rows:
            left = (date.fromisoformat(r["valid_until"]) - TODAY).days
            assert (status == "expired") == (left < 0) or r["manual_status"]

    models = c.get("/api/v1/certificates", params={"object": "model", "page_size": 500}).json()["items"]
    assert models and all(r["object"] == "model" and r["atm_count"] >= 0 for r in models)

    # сертификаты конкретного банкомата: его собственные, его узлов и его модели
    atm_id = c.get("/api/v1/atms", params={"page_size": 1}).json()["items"][0]["id"]
    rows = c.get("/api/v1/certificates", params={"atm_id": atm_id, "page_size": 500}).json()["items"]
    assert {r["object"] for r in rows} >= {"model"}


def test_crud_review_and_manual_status(login_as) -> None:
    _seed(3)
    admin = login_as(Role.ADMIN)
    ids = _ids(admin)
    with SessionLocal() as db:
        model_id = db.scalar(select(AtmModel.id).limit(1))

    base = {
        "atm_model_id": model_id,
        "cert_type_id": ids["cert_type:scheme"],
        "cert_number": "LOA-TEST",
        "issued_at": str(TODAY - timedelta(days=30)),
        "valid_until": str(TODAY + timedelta(days=20)),
    }
    assert admin.post("/api/v1/certificates", json=base).status_code == 400  # нет платёжной системы
    two_objects = {**base, "atm_id": 1, "payment_scheme_id": ids["scheme:visa"]}
    assert admin.post("/api/v1/certificates", json=two_objects).status_code == 422

    r = admin.post("/api/v1/certificates", json={**base, "payment_scheme_id": ids["scheme:visa"]})
    assert r.status_code == 201
    cid = r.json()["id"]
    row = next(x for x in admin.get("/api/v1/certificates", params={"q": "LOA-TEST"}).json()["items"])
    assert row["status"] == "expiring" and row["payment_scheme"] == "Visa"

    admin.patch(f"/api/v1/certificates/{cid}", json={"manual_status": "renewal", "needs_review": True})
    row = admin.get("/api/v1/certificates", params={"q": "LOA-TEST"}).json()["items"][0]
    assert row["status"] == "renewal" and row["needs_review"]
    admin.patch(f"/api/v1/certificates/{cid}", json={"manual_status": "", "needs_review": False})
    row = admin.get("/api/v1/certificates", params={"q": "LOA-TEST"}).json()["items"][0]
    assert row["status"] == "expiring" and not row["needs_review"]

    # удалять может только суперадмин
    assert admin.delete(f"/api/v1/certificates/{cid}").status_code == 403
    assert login_as(Role.SUPERADMIN).delete(f"/api/v1/certificates/{cid}").status_code == 204


def test_document_upload(login_as, tmp_path, monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    _seed(3)
    admin = login_as(Role.ADMIN)
    cid = admin.get("/api/v1/certificates").json()["items"][0]["id"]
    pdf = b"%PDF-1.4 test"
    r = admin.post(f"/api/v1/certificates/{cid}/document", files={"file": ("../../evil.pdf", pdf, "application/pdf")})
    assert r.status_code == 200
    saved = list((tmp_path / "certificates").iterdir())
    assert len(saved) == 1 and saved[0].name.startswith(f"{cid}-")  # имя от пользователя в путь не попало
    viewer = login_as(Role.VIEWER)
    assert viewer.get(f"/api/v1/certificates/{cid}/document").content == pdf
    bad = admin.post(
        f"/api/v1/certificates/{cid}/document", files={"file": ("x.exe", b"MZ", "application/x-msdownload")}
    )
    assert bad.status_code == 400
    assert (
        viewer.post(
            f"/api/v1/certificates/{cid}/document", files={"file": ("a.pdf", pdf, "application/pdf")}
        ).status_code
        == 403
    )


def test_modules_without_certificate(login_as) -> None:
    _seed(20)
    c = login_as(Role.VIEWER)
    rows = c.get("/api/v1/certificates/modules-without").json()
    with SessionLocal() as db:
        for r in rows:
            certs = db.scalars(select(Certificate).where(Certificate.module_id == r["id"])).all()
            assert all(x.valid_until < TODAY or x.manual_status == "revoked" for x in certs)
    assert c.get("/api/v1/certificates/summary").json()["modules_without"] == len(rows)


def test_contract_and_auto_warranty(login_as) -> None:
    _seed(2)
    admin = login_as(Role.ADMIN)
    atm = admin.get("/api/v1/atms").json()["items"][0]
    card = admin.get(f"/api/v1/atms/{atm['id']}").json()
    vendor = next(v["id"] for v in admin.get("/api/v1/reference").json()["vendors"] if v["is_service"])
    r = admin.put(
        f"/api/v1/atms/{atm['id']}/contract",
        json={
            "service_vendor_id": vendor,
            "service_sla_hours": 24,
            "purchase_price": 25000,
            "price_currency": "USD",
            "auto_warranty": True,
        },
    )
    assert r.status_code == 200, r.text
    contract = r.json()["contract"]
    purchase = date.fromisoformat(card["main"]["purchase_date"])
    assert date.fromisoformat(contract["warranty_until"]) > purchase
    assert contract["service_sla_hours"] == 24
    op = login_as(Role.OPERATOR)
    assert op.put(f"/api/v1/atms/{atm['id']}/contract", json={}).status_code == 403
