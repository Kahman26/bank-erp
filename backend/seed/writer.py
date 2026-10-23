"""Запись сгенерированных данных: в БД пакетами и в CSV-файлы для проверки импорта."""

import copy
import csv
import random
from pathlib import Path

from sqlalchemy import func, insert, select, text
from sqlalchemy.orm import Session

from app.db import Base
from app.models import (
    AtmModel,
    Branch,
    DictItem,
    Manufacturer,
    PaymentScheme,
    Processing,
    Region,
    Vendor,
)
from seed import catalog as C
from seed.generator import Dataset, Ids, Ref

# порядок вставки с учётом внешних ключей
TABLES = [
    "location",
    "atm",
    "atm_currency",
    "atm_service",
    "atm_scheme",
    "atm_processing",
    "placement",
    "module",
    "software",
    "contract",
    "service_event",
    "module_replacement",
    "certificate",
    "atm_status_history",
]
WITH_ID = [t for t in TABLES if t not in ("atm_currency", "atm_service", "atm_scheme")]


def _get_or_create(db: Session, model, where: dict, values: dict | None = None):
    obj = db.scalar(select(model).filter_by(**where))
    if obj is None:
        obj = model(**where, **(values or {}))
        db.add(obj)
        db.flush()
    return obj


def ensure_base(db: Session) -> Ref:
    """Производители, модели, филиалы и вендоры — создаёт недостающие, существующие не меняет."""
    dicts = {(d.kind, d.code): d.id for d in db.scalars(select(DictItem))}

    manufacturers = {}
    for name, (country, site) in C.MANUFACTURERS.items():
        manufacturers[name] = _get_or_create(db, Manufacturer, {"name": name}, {"country": country, "website": site}).id

    models = {}
    for m in C.MODELS:
        values = {
            "series": m.series,
            "device_type_id": dicts[("device_type", m.device_type)],
            "install_format_ids": [dicts[("install_format", f)] for f in m.formats],
            "height_mm": m.dims[0] if m.dims else None,
            "width_mm": m.dims[1] if m.dims else None,
            "depth_mm": m.dims[2] if m.dims else None,
            "weight_kg": m.weight_kg,
            "screen_options": " или ".join(f'{s:g}"' for s in m.screens),
            "max_cassettes": m.max_cassettes,
            "cassette_capacity": m.cassette_capacity,
            "max_notes_per_dispense": m.max_notes,
            "recycling": m.recycling,
            "cash_in": m.cash_in,
            "max_denominations": m.max_denominations,
            "supported_os": "Windows 10 IoT Enterprise",
            "power_supply": "AC 200–240 В",
            "operating_temp": "0…+40 °C" if "ttw" not in m.formats else "−20…+50 °C (наружный блок)",
            "humidity": "25–85 %",
            "end_of_support_date": m.end_of_support,
            "warranty_months": m.warranty_months,
            "spec_url": m.spec_url,
        }
        obj = _get_or_create(
            db, AtmModel, {"manufacturer_id": manufacturers[m.manufacturer], "model_name": m.name}, values
        )
        models[f"{m.manufacturer}|{m.name}"] = obj.id

    regions = {r.code: r for r in db.scalars(select(Region))}
    branches: dict[str, list[tuple[int, str]]] = {}
    for code, (_, _, cities) in C.GEOGRAPHY.items():
        for city, *_ in cities:
            name = f"{city.replace(' район', '')} филиал" if code == "tashkent_city" else f"Филиал «{city[3:]}»"
            b = _get_or_create(db, Branch, {"name": name}, {"region_id": regions[code].id, "address": f"{city}"})
            branches.setdefault(code, []).append((b.id, b.name))

    vendors = {}
    for name, ticket_system, _ in C.SERVICE_VENDORS:
        vendors[name] = _get_or_create(db, Vendor, {"name": name}, {"ticket_system": ticket_system}).id
    for name in C.SUPPLIERS:
        vendors[name] = _get_or_create(db, Vendor, {"name": name}, {"is_service": False, "is_supplier": True}).id

    schemes = {s.code: s for s in db.scalars(select(PaymentScheme))}
    return Ref(
        dicts=dicts,
        regions={c: r.id for c, r in regions.items()},
        region_names={c: r.name for c, r in regions.items()},
        schemes={c: s.id for c, s in schemes.items()},
        processings={p.code: p.id for p in db.scalars(select(Processing))},
        manufacturers=manufacturers,
        models=models,
        branches=branches,
        vendors=vendors,
        dict_names={d.id: d.name for d in db.scalars(select(DictItem))},
        scheme_names={s.id: s.name for s in schemes.values()},
    )


def id_allocator(db: Session) -> Ids:
    return Ids({t: db.scalar(text(f"select coalesce(max(id), 0) from {t}")) or 0 for t in WITH_ID})


def write_db(db: Session, ds: Dataset) -> dict[str, int]:
    tables = Base.metadata.tables
    counts = {}
    for name in TABLES:
        rows = ds.rows.get(name, [])
        if rows:
            # Core-вставка мимо ORM: журнал изменений не засоряется тысячами строк генератора
            db.execute(insert(tables[name]), rows)
        counts[name] = len(rows)
    for name in WITH_ID:
        db.execute(text(f"select setval(pg_get_serial_sequence('{name}', 'id'), coalesce(max(id), 1)) from {name}"))
    return counts


def atm_count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Base.metadata.tables["atm"])) or 0


# --- CSV ---------------------------------------------------------------------------------------------------


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # BOM — чтобы Excel открыл кириллицу без вопросов
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def dirty_rows(clean: list[dict[str, str]], seed: int) -> list[dict[str, str]]:
    """Типичные ошибки ручного Excel поверх корректных строк. Колонка _error — подсказка для теста."""
    rng = random.Random(seed + 1)
    base = [copy.deepcopy(r) for r in clean if r["latitude"]][:60]
    for r in base:
        r["_error"] = ""

    def spoil(index: int, field: str, value: str, note: str) -> None:
        base[index][field] = value
        base[index]["_error"] = note

    spoil(0, "atm_code", base[1]["atm_code"], "дубль кода банкомата")
    spoil(2, "model", "SelfServ 999", "неизвестная модель")
    spoil(3, "region", "Ташкент", "регион без «г.» — должен распознаться")
    spoil(4, "purchase_date", "15.03.2024", "дата в формате ДД.ММ.ГГГГ — должна распознаться")
    spoil(5, "latitude", base[5]["latitude"].replace(".", ","), "запятая в координате — должна распознаться")
    spoil(6, "serial_number", "", "пустое обязательное поле")
    spoil(7, "latitude", base[7]["longitude"], "перепутаны широта и долгота")
    spoil(8, "status", "Работает", "неизвестный статус")
    spoil(9, "terminal_id_own", base[10]["terminal_id_own"], "дубль Terminal ID в процессинге")
    spoil(11, "latitude", "сорок один", "координата не число")
    spoil(12, "commissioning_date", "2019-02-30", "несуществующая дата")
    spoil(13, "currencies", "UZS;EUR", "неизвестная валюта")
    rng.shuffle(base)
    return base
