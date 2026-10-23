"""Генератор вымышленной, но правдоподобной сети банкоматов.

Строит строки для всех таблиц сразу (с заранее выданными id) — так 2 000 банкоматов
вставляются пакетно за секунды. Один и тот же --seed даёт один и тот же набор данных
(относительно даты запуска).
"""

import random
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from seed import catalog as C


@dataclass
class Ref:
    """id справочников из БД."""

    dicts: dict[tuple[str, str], int]
    regions: dict[str, int]
    region_names: dict[str, str]
    schemes: dict[str, int]
    processings: dict[str, int]
    manufacturers: dict[str, int]
    models: dict[str, int]  # "производитель|модель" → id
    branches: dict[str, list[tuple[int, str]]]  # region code → [(id, name)]
    vendors: dict[str, int]
    dict_names: dict[int, str]
    scheme_names: dict[int, str]

    def d(self, kind: str, code: str) -> int:
        return self.dicts[(kind, code)]


@dataclass
class Ids:
    """Выдаёт id, продолжая уже существующие в таблицах."""

    next: dict[str, int]

    def __call__(self, table: str) -> int:
        self.next[table] += 1
        return self.next[table]


@dataclass
class Dataset:
    rows: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    csv: list[dict[str, str]] = field(default_factory=list)

    def add(self, table: str, row: dict[str, Any]) -> dict[str, Any]:
        self.rows.setdefault(table, []).append(row)
        return row


def _weighted(rng: random.Random, weights: dict[str, float]) -> str:
    return rng.choices(list(weights), weights=list(weights.values()))[0]


def _rand_date(rng: random.Random, start: date, end: date) -> date:
    if end <= start:
        return start
    return start + timedelta(days=rng.randrange((end - start).days + 1))


def _dt(d: date, rng: random.Random) -> datetime:
    return datetime.combine(d, time(rng.randrange(8, 20), rng.randrange(60)), tzinfo=UTC)


PLACED = {"in_service", "repair", "vendor_repair", "installing"}
REMOVED = {"on_farm", "to_writeoff", "written_off"}
NOT_YET = {"in_stock", "in_delivery"}
STATUS_ORDER_BEFORE = ["in_stock", "in_delivery", "installing", "in_service"]


class Generator:
    def __init__(self, ref: Ref, ids: Ids, seed: int, today: date | None = None) -> None:
        self.ref = ref
        self.ids = ids
        self.rng = random.Random(seed)
        self.today = today or date.today()
        self.ds = Dataset()
        self.seq_by_region: dict[str, int] = {}
        self.terminal_seq = {"own": 10010000, "uzcard": 50000, "humo": 7710000}
        self.merchant_seq = {"own": 900000, "uzcard": 9010000, "humo": 8810000}
        self.serial_seq = 1000000

    # --- верхний уровень ------------------------------------------------------------------------------

    def run(self, count: int) -> Dataset:
        self._model_certificates()
        region_weights = {code: g[1] for code, g in C.GEOGRAPHY.items()}
        model_weights = {f"{m.manufacturer}|{m.name}": m.weight for m in C.MODELS}
        specs = {f"{m.manufacturer}|{m.name}": m for m in C.MODELS}
        for _ in range(count):
            region = _weighted(self.rng, region_weights)
            spec = specs[_weighted(self.rng, model_weights)]
            self._atm(region, spec)
        return self.ds

    # --- банкомат ---------------------------------------------------------------------------------------

    def _atm(self, region: str, spec: C.ModelSpec) -> None:
        rng, ref, today = self.rng, self.ref, self.today
        status = _weighted(rng, C.STATUS_WEIGHTS)
        y0, y1 = spec.years
        if status in NOT_YET:
            purchase = today - timedelta(days=rng.randrange(5, 90))
        else:
            # снятые с места банкоматы должны были успеть поработать
            latest = today - timedelta(days=450 if status in REMOVED else 90)
            purchase = min(_rand_date(rng, date(y0, 1, 15), min(date(y1, 12, 1), latest)), latest)
        commissioning = None if status in NOT_YET | {"installing"} else purchase + timedelta(days=rng.randrange(15, 75))

        prefix, _, cities = C.GEOGRAPHY[region]
        self.seq_by_region[region] = self.seq_by_region.get(region, 0) + 1
        atm_id = self.ids("atm")
        city = rng.choice(cities)
        fmt = rng.choice(spec.formats)
        screen = rng.choice(spec.screens)
        contactless = rng.random() < (0.9 if y0 >= 2020 else 0.5)
        branch_id, branch_name = rng.choice(ref.branches[region])

        end_date = None  # когда банкомат сняли с места (для «на ферме», «к списанию», «списан»)
        if status in REMOVED:
            end_date = _rand_date(rng, commissioning + timedelta(days=200), today - timedelta(days=5))
        decommission = end_date if status == "written_off" else None

        atm = self.ds.add(
            "atm",
            {
                "id": atm_id,
                "atm_code": f"ATM-{prefix}-{self.seq_by_region[region]:04d}",
                "serial_number": self._serial(spec.manufacturer),
                "inventory_number": f"ОС-{rng.randrange(100000, 999999)}",
                "model_id": ref.models[f"{spec.manufacturer}|{spec.name}"],
                "device_type_id": ref.d("device_type", spec.device_type),
                "install_format_id": ref.d("install_format", fmt),
                "status_id": ref.d("atm_status", status),
                "purchase_date": purchase,
                "commissioning_date": commissioning,
                "decommission_date": decommission,
                "branch_id": branch_id,
                "notes": None,
                "screen_size_in": Decimal(str(screen)),
                "screen_resolution": C.SCREEN_RESOLUTION[screen],
                "screen_orientation_id": ref.d("screen_orientation", "landscape"),
                "input_method_id": ref.d("input_method", "touch" if y0 >= 2019 else rng.choice(["fdk", "both"])),
                "screen_sunlight": fmt in ("ttw", "kiosk"),
                "privacy_filter": rng.random() < 0.6,
                "safe_class_id": ref.d("safe_class", rng.choice(["cen_1", "cen_3", "ul291_l1"])),
                "safe_lock_id": ref.d("safe_lock", rng.choice(["electronic", "electronic", "mechanical"])),
                "service_access_id": ref.d("service_access", "rear" if fmt == "ttw" else "front"),
                "cassette_count": rng.randint(max(2, spec.max_cassettes - 1), spec.max_cassettes),
                "contactless": contactless,
                "audio_jack": rng.random() < 0.3,
                "ups": rng.random() < 0.6,
            },
        )

        currencies = ["UZS"] + (["USD"] if rng.random() < (0.45 if region == "tashkent_city" else 0.15) else [])
        for code in currencies:
            self.ds.add("atm_currency", {"atm_id": atm_id, "currency_code": code})
        services = ["withdrawal"] + (["deposit"] if spec.cash_in else [])
        services += [s for s, p in (("payments", 0.6), ("transfers", 0.4), ("qr", 0.3)) if rng.random() < p]
        if contactless:
            services.append("contactless")
        for s in services:
            self.ds.add("atm_service", {"atm_id": atm_id, "service_id": ref.d("atm_service", s)})

        start = commissioning or (today - timedelta(days=rng.randrange(3, 20)) if status == "installing" else None)
        placements = self._placements(atm_id, region, city, fmt, start, end_date, status) if start else []
        processings = self._processings(atm_id, status)
        schemes = self._schemes(atm_id, processings)
        modules = self._modules(atm_id, spec, purchase, contactless)
        self._software(atm_id, spec, purchase)
        vendor_id = self._contract(atm_id, spec, purchase)
        if commissioning:
            self._events(atm_id, spec, commissioning, end_date or today, status, vendor_id, modules)
        self._status_history(atm_id, status, purchase, commissioning, start, end_date)
        self._csv(atm, spec, region, branch_name, placements, processings, schemes, currencies, contactless)

    def _serial(self, manufacturer: str) -> str:
        self.serial_seq += self.rng.randrange(1, 40)
        prefix = {"NCR Atleos": "NC", "Hyosung TNS": "HY", "Diebold Nixdorf": "DN", "GRG Banking": "GR"}[manufacturer]
        return f"{prefix}{self.serial_seq}"

    # --- размещения -------------------------------------------------------------------------------------

    def _placements(self, atm_id, region, city, fmt, start, end_date, status) -> list[dict]:
        rng = self.rng
        n = rng.choices([1, 2, 3], weights=[0.7, 0.22, 0.08])[0]
        last = end_date or self.today
        if (last - start).days < 400:
            n = 1
        dates = sorted({_rand_date(rng, start + timedelta(days=180), last - timedelta(days=30)) for _ in range(n - 1)})
        bounds = [start, *dates]
        result = []
        for i, placed_from in enumerate(bounds):
            is_last = i == len(bounds) - 1
            placed_to = bounds[i + 1] if not is_last else (end_date if status in REMOVED else None)
            if i > 0:
                city = rng.choice(C.GEOGRAPHY[region][2])  # переезд — в пределах региона
            loc = self._location(region, city, fmt)
            row = self.ds.add(
                "placement",
                {
                    "id": self.ids("placement"),
                    "atm_id": atm_id,
                    "location_id": loc["id"],
                    "placed_from": placed_from,
                    "placed_to": placed_to,
                    "move_reason_id": self.ref.d("move_reason", rng.choice(list(_MOVE_REASONS)) if i else "new_point"),
                    "basis_document": f"Приказ №{rng.randrange(10, 999)}-П" if rng.random() < 0.6 else None,
                    "created_by_id": None,
                },
            )
            result.append((row, loc))
        return result

    def _location(self, region: str, city: tuple, fmt: str) -> dict:
        rng = self.rng
        name, lat, lon, spread = city
        place = _weighted(rng, {k: v[0] for k, v in C.PLACE_TYPES.items()})
        if fmt in ("ttw", "kiosk") and place in ("mall", "shop"):
            place = "street" if fmt == "kiosk" else "branch"
        title = rng.choice(C.PLACE_TYPES[place][1]).format(
            city=name.replace("г. ", "").split()[0],
            n=rng.randrange(1, 60),
            mall=rng.choice(C.MALLS),
            shop=rng.choice(C.SHOPS),
            company=rng.choice(C.COMPANIES),
        )
        is_24h = fmt in ("ttw", "kiosk", "drive_up") or place in ("transport", "street")
        hours = "Круглосуточно" if is_24h else C.WORKING_HOURS[place]
        return self.ds.add(
            "location",
            {
                "id": self.ids("location"),
                "name": title,
                "region_id": self.ref.regions[region],
                "city_district": name,
                "address": f"{rng.choice(C.STREETS)}, {rng.randrange(1, 180)}",
                "landmark": rng.choice(C.LANDMARKS).format(n=rng.randrange(1, 300)) if rng.random() < 0.8 else None,
                "latitude": Decimal(f"{lat + rng.uniform(-spread, spread):.6f}"),
                "longitude": Decimal(f"{lon + rng.uniform(-spread, spread) * 1.3:.6f}"),
                "place_type_id": self.ref.d("place_type", place),
                "indoor": fmt == "lobby",
                "access_type_id": self.ref.d("access_type", "restricted" if place == "enterprise" else "public"),
                "is_24h": is_24h,
                "working_hours": hours,
                "premises_owner": None if place == "branch" else f"Арендодатель: ООО «{rng.choice(C.COMPANIES)}»",
                "site_contact": f"+998 {rng.choice([71, 90, 91, 93, 94, 97, 99])} {rng.randrange(100, 999)}-"
                f"{rng.randrange(10, 99)}-{rng.randrange(10, 99)}",
            },
        )

    # --- процессинги, ПС --------------------------------------------------------------------------------

    def _processings(self, atm_id: int, status: str) -> dict[str, dict]:
        rng = self.rng
        if status in NOT_YET:
            return {}
        result = {}
        for code, p in (("own", 1.0), ("uzcard", 0.95), ("humo", 0.9)):
            if rng.random() > p:
                continue
            self.terminal_seq[code] += 1
            self.merchant_seq[code] += 1
            tid = {
                "own": f"{self.terminal_seq[code]}",
                "uzcard": f"UZ{self.terminal_seq[code]:06d}",
                "humo": f"{self.terminal_seq[code]}H",
            }[code]
            result[code] = self.ds.add(
                "atm_processing",
                {
                    "id": self.ids("atm_processing"),
                    "atm_id": atm_id,
                    "processing_id": self.ref.processings[code],
                    "terminal_id": tid,
                    "merchant_id": f"{self.merchant_seq[code]}",
                    "host_protocol_id": self.ref.d("host_protocol", "ndc"),
                    "connection_type_id": self.ref.d(
                        "connection_type", rng.choices(["ethernet", "lte", "vsat"], weights=[0.75, 0.22, 0.03])[0]
                    ),
                    "ip_address": f"10.{rng.randrange(10, 60)}.{rng.randrange(0, 255)}.{rng.randrange(2, 254)}",
                },
            )
        return result

    def _schemes(self, atm_id: int, processings: dict) -> list[str]:
        schemes = []
        if "uzcard" in processings:
            schemes.append("uzcard")
        if "humo" in processings:
            schemes.append("humo")
        if "own" in processings:
            schemes += [s for s, p in (("visa", 0.8), ("mastercard", 0.8), ("unionpay", 0.6)) if self.rng.random() < p]
        for s in schemes:
            self.ds.add("atm_scheme", {"atm_id": atm_id, "scheme_id": self.ref.schemes[s]})
        return schemes

    # --- узлы, ПО ---------------------------------------------------------------------------------------

    def _module(self, atm_id: int, mtype: str, manufacturer: str, installed: date) -> dict:
        rng = self.rng
        models = C.MODULE_MODELS[mtype]
        attrs: dict[str, Any] = {}
        if mtype == "card_reader":
            attrs = {"тип": "моторизованный", "чтение": "магнитная полоса, чип (EMV)", "антискимминг": "есть"}
        elif mtype == "epp":
            attrs = {"PCI PTS": rng.choice(["5.x", "6.x"]), "шифрование": "AES", "RKL": "да"}
        elif mtype == "pc":
            attrs = {
                "процессор": rng.choice(["Intel Core i3", "Intel Core i5"]),
                "ОЗУ, ГБ": rng.choice([4, 8, 16]),
                "накопитель": rng.choice(["SSD 256 ГБ", "SSD 512 ГБ", "HDD 500 ГБ"]),
            }
        elif mtype == "camera":
            attrs = {"количество": rng.choice([2, 3]), "тип": "IP", "зона": "лицо, руки"}
        self.serial_seq += 1
        return self.ds.add(
            "module",
            {
                "id": self.ids("module"),
                "atm_id": atm_id,
                "module_type_id": self.ref.d("module_type", mtype),
                "vendor": manufacturer
                if mtype in ("card_reader", "nfc_reader", "epp", "dispenser", "cash_in")
                else None,
                "model": models.get(manufacturer) or models["*"],
                "serial_number": f"M{self.serial_seq}",
                "firmware_version": f"{rng.randrange(1, 6)}.{rng.randrange(0, 20)}" if rng.random() < 0.7 else None,
                "installed_at": installed,
                "removed_at": None,
                "is_faulty": False,
                "attributes": attrs,
            },
        )

    def _modules(self, atm_id: int, spec: C.ModelSpec, purchase: date, contactless: bool) -> list[dict]:
        types = [
            "card_reader",
            "epp",
            "dispenser",
            "receipt_printer",
            "camera",
            "sensors",
            "pc",
            "monitor",
            "antiskimming",
        ]
        if contactless:
            types.append("nfc_reader")
        if spec.cash_in:
            types.append("cash_in")
        if self.rng.random() < 0.6:
            types.append("ups")
        modules = [self._module(atm_id, t, spec.manufacturer, purchase) for t in types]
        for m in modules:
            self._module_certificate(m, purchase)
        return modules

    def _software(self, atm_id: int, spec: C.ModelSpec, purchase: date) -> None:
        rng = self.rng
        items = [("xfs", spec.xfs, rng.choice(C.XFS_VERSIONS))]
        for stype, catalog in (
            ("client", C.CLIENT_APPS),
            ("emv", C.EMV_KERNELS),
            ("security", C.SECURITY),
            ("monitoring", C.MONITORING),
        ):
            name, versions = catalog[0]
            items.append((stype, name, rng.choice(versions)))
        for stype, name, version in items:
            installed = purchase + timedelta(days=rng.randrange(10, 40))
            if stype == "client" and rng.random() < 0.3 and installed < self.today - timedelta(days=200):
                # история версий: старая запись + обновление
                self.ds.add(
                    "software",
                    {
                        "id": self.ids("software"),
                        "atm_id": atm_id,
                        "software_type_id": self.ref.d("software_type", stype),
                        "name": name,
                        "version": "4.2",
                        "installed_at": installed,
                    },
                )
                installed = _rand_date(rng, installed + timedelta(days=120), self.today - timedelta(days=10))
            self.ds.add(
                "software",
                {
                    "id": self.ids("software"),
                    "atm_id": atm_id,
                    "software_type_id": self.ref.d("software_type", stype),
                    "name": name,
                    "version": version,
                    "installed_at": installed,
                },
            )

    # --- договор, ремонты --------------------------------------------------------------------------------

    def _contract(self, atm_id: int, spec: C.ModelSpec, purchase: date) -> int:
        rng = self.rng
        vendor_name = C.SERVICE_VENDORS[C.VENDOR_FOR_MANUFACTURER[spec.manufacturer]][0]
        months = rng.choice([spec.warranty_months, spec.warranty_months, 36])
        self.ds.add(
            "contract",
            {
                "id": self.ids("contract"),
                "atm_id": atm_id,
                "supplier_id": self.ref.vendors[rng.choice(C.SUPPLIERS)],
                "purchase_contract": f"ДП-{purchase.year}/{rng.randrange(1, 120):03d} от {purchase:%d.%m.%Y}",
                "purchase_price": Decimal(rng.randrange(*spec.price_usd, 100)),
                "price_currency": "USD",
                "warranty_until": purchase + timedelta(days=months * 30),
                "service_vendor_id": self.ref.vendors[vendor_name],
                "service_sla_hours": rng.choice([24, 48, 72]),
            },
        )
        return self.ref.vendors[vendor_name]

    def _events(self, atm_id, spec, start: date, end: date, status, vendor_id, modules) -> None:
        rng = self.rng
        day = start
        while True:
            day += timedelta(days=int(rng.expovariate(spec.repairs_per_year / 365)) + 1)
            if day >= end - timedelta(days=3):
                break
            self._event(atm_id, day, vendor_id, modules, finished=True)
        if status in ("repair", "vendor_repair"):
            self._event(
                atm_id,
                self.today - timedelta(days=rng.randrange(0, 12)),
                vendor_id,
                modules,
                finished=False,
                etype="breakdown",
                by_vendor=status == "vendor_repair",
            )

    def _event(self, atm_id, day, vendor_id, modules, finished, etype=None, by_vendor=None) -> None:
        rng = self.rng
        etype = etype or _weighted(rng, C.EVENT_TYPES)
        started = _dt(day, rng)
        hours = {"breakdown": (2, 72), "maintenance": (1, 6), "module_replacement": (4, 96)}.get(etype, (1, 24))
        by_bank = (not by_vendor) if by_vendor is not None else rng.random() < 0.15
        event_id = self.ids("service_event")
        row = self.ds.add(
            "service_event",
            {
                "id": event_id,
                "atm_id": atm_id,
                "event_type_id": self.ref.d("service_event_type", etype),
                "ticket_number": None if by_bank else f"SV{vendor_id}-{day.year}-{rng.randrange(1, 99999):05d}",
                "started_at": started,
                "finished_at": started + timedelta(hours=rng.uniform(*hours)) if finished else None,
                "module_id": None,
                "problem": rng.choice(C.PROBLEMS[etype]),
                "work_done": rng.choice(C.WORK_DONE[etype]) if finished else None,
                "affects_certification": False,
                "vendor_id": None if by_bank else vendor_id,
                "by_bank_engineer": by_bank,
                "cost": Decimal(rng.randrange(50, 1500)) if not by_bank and rng.random() < 0.3 else None,
                "cost_currency": "USD",
                "created_by_id": None,
            },
        )
        if etype != "module_replacement":
            return
        mtype = _weighted(rng, C.REPLACEABLE)
        old = next(
            (
                m
                for m in modules
                if m["module_type_id"] == self.ref.d("module_type", mtype)
                and m["removed_at"] is None
                and m["installed_at"] < day
            ),
            None,
        )
        if old is None:
            return
        old["removed_at"] = day
        old["is_faulty"] = True
        manufacturer = old["vendor"] or "*"
        new = self._module(atm_id, mtype, manufacturer if manufacturer != "*" else "*", day)
        modules.append(new)
        row["module_id"] = old["id"]
        if mtype in ("card_reader", "nfc_reader", "epp"):
            row["affects_certification"] = True
            recent = (self.today - day).days < 180
            for cert in self.ds.rows.get("certificate", []):
                if cert["module_id"] == old["id"] and recent:
                    cert["needs_review"] = True
            if rng.random() < 0.5:
                self._module_certificate(new, day)
        self.ds.add(
            "module_replacement",
            {
                "id": self.ids("module_replacement"),
                "event_id": event_id,
                "removed_module_id": old["id"],
                "installed_module_id": new["id"],
            },
        )

    # --- сертификаты -------------------------------------------------------------------------------------

    def _cert(self, years: int, **target) -> dict:
        """Действующий сертификат: срок окончания распределён так, что ~5 % истекают в ближайшие 90 дней,
        ~2 % уже истекли, остальные действуют дольше."""
        rng = self.rng
        roll = rng.random()
        if roll < 0.02:
            offset = -rng.randrange(1, 180)
        elif roll < 0.07:
            offset = rng.randrange(0, 90)
        else:
            offset = rng.randrange(90, 365 * years - 30)
        valid = self.today + timedelta(days=offset)
        issued = valid - timedelta(days=365 * years)
        # часть сертификатов «на продлении»; немного отозванных
        manual = "renewal" if valid < self.today + timedelta(days=60) and rng.random() < 0.3 else None
        if rng.random() < 0.005:
            manual = "revoked"
        return self.ds.add(
            "certificate",
            {
                "id": self.ids("certificate"),
                "atm_model_id": None,
                "atm_id": None,
                "module_id": None,
                "payment_scheme_id": None,
                "cert_number": f"LOA-{issued.year}-{rng.randrange(10000, 99999)}",
                "issued_at": issued,
                "valid_until": valid,
                "manual_status": manual,
                "source_id": self.ref.d("cert_source", rng.choices(["supplier", "vendor"], weights=[0.75, 0.25])[0]),
                "document_path": None,
                "needs_review": False,
                **target,
            },
        )

    def _model_certificates(self) -> None:
        for model_id in self.ref.models.values():
            for scheme_id in self.ref.schemes.values():
                cert = self._cert(
                    3,
                    atm_model_id=model_id,
                    payment_scheme_id=scheme_id,
                    cert_type_id=self.ref.d("cert_type", "scheme"),
                )
                cert["source_id"] = self.ref.d("cert_source", "scheme")
            self._cert(3, atm_model_id=model_id, cert_type_id=self.ref.d("cert_type", "emv_l2"))

    def _module_certificate(self, module: dict, installed: date) -> None:
        cert_type = {
            self.ref.d("module_type", "card_reader"): ("emv_l1_contact", 4),
            self.ref.d("module_type", "nfc_reader"): ("emv_l1_contactless", 4),
            self.ref.d("module_type", "epp"): ("pci_pts", 6),
        }.get(module["module_type_id"])
        if cert_type is None or self.rng.random() < 0.08:  # часть сертификатов так и не собрана
            return
        code, years = cert_type
        del installed  # срок сертификата не зависит от даты установки узла
        self._cert(years, module_id=module["id"], cert_type_id=self.ref.d("cert_type", code))

    # --- история статусов ------------------------------------------------------------------------------

    def _status_history(self, atm_id, status, purchase, commissioning, start, end_date) -> None:
        chain: list[tuple[str, date]] = [("in_stock", purchase)]
        if status != "in_stock":
            chain.append(("in_delivery", purchase + timedelta(days=3)))
        if start and status not in NOT_YET:
            chain.append(("installing", start - timedelta(days=5) if commissioning else start))
        if commissioning:
            chain.append(("in_service", commissioning))
        if status in ("repair", "vendor_repair", "on_farm", "to_writeoff"):
            chain.append((status, end_date or self.today - timedelta(days=self.rng.randrange(0, 12))))
        if status == "written_off":
            chain.append(("to_writeoff", end_date - timedelta(days=30)))
            chain.append(("written_off", end_date))
        for code, day in chain:
            self.ds.add(
                "atm_status_history",
                {
                    "id": self.ids("atm_status_history"),
                    "atm_id": atm_id,
                    "status_id": self.ref.d("atm_status", code),
                    "changed_at": _dt(day, self.rng),
                    "changed_by_id": None,
                    "comment": None,
                },
            )

    # --- строка CSV (формат раздела 5 набора полей) -------------------------------------------------------

    def _csv(self, atm, spec, region, branch_name, placements, processings, schemes, currencies, contactless) -> None:
        current = placements[-1][1] if placements and placements[-1][0]["placed_to"] is None else None
        names = self.ref.dict_names
        row = {
            "atm_code": atm["atm_code"],
            "terminal_id_own": processings.get("own", {}).get("terminal_id", ""),
            "terminal_id_uzcard": processings.get("uzcard", {}).get("terminal_id", ""),
            "terminal_id_humo": processings.get("humo", {}).get("terminal_id", ""),
            "merchant_id_own": processings.get("own", {}).get("merchant_id", ""),
            "merchant_id_uzcard": processings.get("uzcard", {}).get("merchant_id", ""),
            "merchant_id_humo": processings.get("humo", {}).get("merchant_id", ""),
            "serial_number": atm["serial_number"],
            "manufacturer": spec.manufacturer,
            "model": spec.name,
            "device_type": names[atm["device_type_id"]],
            "install_type": names[atm["install_format_id"]],
            "status": names[atm["status_id"]],
            "purchase_date": atm["purchase_date"].isoformat(),
            "commissioning_date": atm["commissioning_date"].isoformat() if atm["commissioning_date"] else "",
            "branch": branch_name,
            "region": self.ref.region_names[region],
            "city_district": current["city_district"] if current else "",
            "address": current["address"] if current else "",
            "landmark": (current["landmark"] or "") if current else "",
            "latitude": str(current["latitude"]) if current else "",
            "longitude": str(current["longitude"]) if current else "",
            "place_type": names[current["place_type_id"]] if current else "",
            "working_hours": current["working_hours"] if current else "",
            "currencies": ";".join(currencies),
            "accepted_schemes": ";".join(self.ref.scheme_names[self.ref.schemes[s]] for s in schemes),
            "screen_size_in": str(atm["screen_size_in"]),
            "screen_resolution": atm["screen_resolution"],
            "cassette_count": str(atm["cassette_count"]),
            "cash_in": "да" if spec.cash_in else "нет",
            "contactless": "да" if contactless else "нет",
        }
        self.ds.csv.append(row)


_MOVE_REASONS = ("low_load", "point_closed", "lease_end", "renovation", "partner_request")
