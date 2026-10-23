"""Генератор тестовых данных.

python -m seed --count 1000 --db                 # наполнить БД
python -m seed --count 1000 --db --if-empty      # только если банкоматов ещё нет (для старта контейнера)
python -m seed --count 1000 --csv seed/out       # CSV для проверки импорта: atms.csv и atms_dirty.csv
"""

import argparse
import sys
import time
from pathlib import Path

from app.db import SessionLocal
from seed.generator import Generator
from seed.writer import atm_count, dirty_rows, ensure_base, id_allocator, write_csv, write_db


def main() -> None:
    p = argparse.ArgumentParser(prog="python -m seed", description="Вымышленные данные сети банкоматов")
    p.add_argument("--count", type=int, default=1000, help="сколько банкоматов (по умолчанию 1000)")
    p.add_argument("--seed", type=int, default=42, help="зерно генератора (по умолчанию 42)")
    p.add_argument("--db", action="store_true", help="записать в БД")
    p.add_argument("--if-empty", action="store_true", help="ничего не делать, если в БД уже есть банкоматы")
    p.add_argument("--csv", type=Path, help="каталог для atms.csv и atms_dirty.csv")
    args = p.parse_args()
    if not args.db and not args.csv:
        p.error("укажите --db и/или --csv")

    started = time.monotonic()
    with SessionLocal() as db:
        if args.if_empty and atm_count(db):
            print("seed: банкоматы уже есть — пропускаю")
            return
        ref = ensure_base(db)
        ds = Generator(ref, id_allocator(db), args.seed).run(args.count)
        if args.db:
            counts = write_db(db, ds)
            db.commit()
            print("seed: " + ", ".join(f"{k}={v}" for k, v in counts.items() if v))
        else:
            db.rollback()
    if args.csv:
        write_csv(args.csv / "atms.csv", ds.csv)
        write_csv(args.csv / "atms_dirty.csv", dirty_rows(ds.csv, args.seed))
        print(f"seed: CSV в {args.csv}")
    print(f"seed: готово за {time.monotonic() - started:.1f} с")


if __name__ == "__main__":
    sys.exit(main())
