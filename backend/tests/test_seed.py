import csv
from pathlib import Path

from sqlalchemy import func, select, text

from app.db import SessionLocal
from app.models import Atm, Certificate, Placement
from seed.generator import Generator
from seed.writer import dirty_rows, ensure_base, id_allocator, write_csv, write_db


def _generate(count: int, seed: int = 7):
    with SessionLocal() as db:
        ref = ensure_base(db)
        ds = Generator(ref, id_allocator(db), seed).run(count)
        write_db(db, ds)
        db.commit()
    return ds


def test_generated_data_passes_db_constraints() -> None:
    ds = _generate(60)
    with SessionLocal() as db:
        assert db.scalar(select(func.count(Atm.id))) == 60
        # у каждого размещённого банкомата ровно одно текущее место
        current = db.scalar(select(func.count(Placement.id)).where(Placement.placed_to.is_(None)))
        placed = sum(1 for r in ds.csv if r["latitude"])
        assert current == placed
        assert db.scalar(select(func.count(Certificate.id))) > 60
        # последовательности продолжены — следующая вставка не упрётся в занятый id
        next_id = db.execute(text("select nextval(pg_get_serial_sequence('atm', 'id'))")).scalar()
        assert next_id == 61


def test_same_seed_same_data() -> None:
    with SessionLocal() as db:
        ref = ensure_base(db)
        a = Generator(ref, id_allocator(db), 3).run(20).csv
        b = Generator(ref, id_allocator(db), 3).run(20).csv
        db.rollback()
    assert a == b


def test_csv_outputs(tmp_path: Path) -> None:
    ds = _generate(40)
    write_csv(tmp_path / "atms.csv", ds.csv)
    write_csv(tmp_path / "atms_dirty.csv", dirty_rows(ds.csv, 7))
    with (tmp_path / "atms.csv").open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 40
    assert rows[0]["atm_code"].startswith("ATM-")
    with (tmp_path / "atms_dirty.csv").open(encoding="utf-8-sig") as f:
        dirty = list(csv.DictReader(f))
    assert sum(1 for r in dirty if r["_error"]) == 12
