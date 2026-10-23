"""Справочные данные генератора. Модели и регионы реальные, всё остальное вымышленное.

Паспортные значения моделей взяты из открытых спецификаций (раздел «Источники» набора полей);
где данных нет — поле пустое. Даты окончания поддержки условные.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModelSpec:
    manufacturer: str
    name: str
    series: str
    device_type: str  # код dict_item device_type
    formats: tuple[str, ...]
    weight: float  # доля в парке
    years: tuple[int, int]  # годы закупок
    screens: tuple[float, ...]
    max_cassettes: int
    cash_in: bool = False
    recycling: bool = False
    dims: tuple[int, int, int] | None = None
    weight_kg: int | None = None
    cassette_capacity: int | None = None
    max_notes: int | None = 40
    max_denominations: int | None = None
    end_of_support: str = "2030-12-31"
    warranty_months: int = 24
    price_usd: tuple[int, int] = (18_000, 26_000)
    repairs_per_year: float = 0.8
    xfs: str = ""
    spec_url: str | None = None
    extra: dict = field(default_factory=dict)


MANUFACTURERS = {
    "NCR Atleos": ("США", "https://www.ncratleos.com"),
    "Hyosung TNS": ("Южная Корея", "https://www.hyosungtns.com"),
    "Diebold Nixdorf": ("США", "https://www.dieboldnixdorf.com"),
    "GRG Banking": ("Китай", "https://www.grgbanking.com"),
}

MODELS = [
    ModelSpec(
        "NCR Atleos",
        "SelfServ 22e",
        "SelfServ",
        "dispenser",
        ("lobby",),
        0.10,
        (2017, 2020),
        (15,),
        4,
        weight_kg=540,
        end_of_support="2027-12-31",
        price_usd=(14_000, 18_000),
        repairs_per_year=1.3,
        xfs="NCR APTRA XFS",
        spec_url="https://tranact.com/pdf/SS-22.pdf",
    ),
    ModelSpec(
        "NCR Atleos",
        "SelfServ 25",
        "SelfServ",
        "dispenser",
        ("lobby", "ttw"),
        0.08,
        (2018, 2022),
        (15,),
        4,
        end_of_support="2028-06-30",
        price_usd=(16_000, 21_000),
        repairs_per_year=1.1,
        xfs="NCR APTRA XFS",
    ),
    ModelSpec(
        "NCR Atleos",
        "SelfServ 84",
        "SelfServ",
        "dispenser",
        ("ttw", "kiosk"),
        0.10,
        (2019, 2024),
        (15, 19),
        4,
        dims=(1513, 770, 1248),
        weight_kg=905,
        end_of_support="2029-12-31",
        price_usd=(22_000, 28_000),
        repairs_per_year=0.9,
        xfs="NCR APTRA XFS",
    ),
    ModelSpec(
        "Hyosung TNS",
        "MX8300D",
        "MoniMax",
        "recycler",
        ("lobby", "ttw"),
        0.18,
        (2020, 2025),
        (15, 19),
        5,
        cash_in=True,
        recycling=True,
        cassette_capacity=2950,
        max_denominations=4,
        end_of_support="2031-12-31",
        price_usd=(28_000, 36_000),
        repairs_per_year=0.7,
        xfs="Hyosung Nextware",
    ),
    ModelSpec(
        "Hyosung TNS",
        "MX8600",
        "MoniMax",
        "cash_in",
        ("ttw", "kiosk"),
        0.12,
        (2019, 2023),
        (15, 19),
        4,
        cash_in=True,
        end_of_support="2030-06-30",
        price_usd=(24_000, 30_000),
        repairs_per_year=0.8,
        xfs="Hyosung Nextware",
    ),
    ModelSpec(
        "Hyosung TNS",
        "9E",
        "Halo",
        "recycler",
        ("lobby", "ttw"),
        0.08,
        (2023, 2026),
        (19,),
        6,
        cash_in=True,
        recycling=True,
        max_denominations=6,
        end_of_support="2034-12-31",
        warranty_months=36,
        price_usd=(34_000, 42_000),
        repairs_per_year=0.5,
        xfs="Hyosung Nextware",
    ),
    ModelSpec(
        "Diebold Nixdorf",
        "DN Series 200",
        "DN Series",
        "recycler",
        ("ttw",),
        0.10,
        (2021, 2025),
        (15, 19),
        4,
        cash_in=True,
        recycling=True,
        end_of_support="2032-12-31",
        price_usd=(30_000, 38_000),
        repairs_per_year=0.6,
        xfs="DN ProBase",
    ),
    ModelSpec(
        "Diebold Nixdorf",
        "DN Series 100D",
        "DN Series",
        "dispenser",
        ("lobby",),
        0.08,
        (2021, 2025),
        (15,),
        4,
        end_of_support="2032-12-31",
        price_usd=(18_000, 23_000),
        repairs_per_year=0.6,
        xfs="DN ProBase",
    ),
    ModelSpec(
        "GRG Banking",
        "H68N",
        "H68N",
        "recycler",
        ("lobby", "ttw"),
        0.16,
        (2020, 2025),
        (15, 19),
        4,
        cash_in=True,
        recycling=True,
        max_denominations=6,
        end_of_support="2033-12-31",
        price_usd=(25_000, 31_000),
        repairs_per_year=0.7,
        xfs="GRG XFS",
        spec_url="https://www.informaticsint.com/what-we-do/infrastructure-solutions/banking/atms-recyclers/atms/versatile-cash-recycler/",
    ),
]

SCREEN_RESOLUTION = {12.1: "800x600", 15: "1024x768", 19: "1280x1024"}

# Код региона (region.code) → (код для atm_code, вес в сети, [(город/район, широта, долгота, разброс)])
GEOGRAPHY: dict[str, tuple[str, float, list[tuple[str, float, float, float]]]] = {
    "tashkent_city": (
        "TAS",
        30.0,
        [
            ("Юнусабадский район", 41.3650, 69.2850, 0.012),
            ("Мирзо-Улугбекский район", 41.3300, 69.3350, 0.012),
            ("Чиланзарский район", 41.2850, 69.2050, 0.012),
            ("Яккасарайский район", 41.2900, 69.2600, 0.008),
            ("Шайхантахурский район", 41.3250, 69.2300, 0.010),
            ("Алмазарский район", 41.3450, 69.2050, 0.010),
            ("Мирабадский район", 41.2950, 69.2800, 0.008),
            ("Сергелийский район", 41.2250, 69.2200, 0.012),
            ("Учтепинский район", 41.2950, 69.1650, 0.010),
            ("Яшнабадский район", 41.3000, 69.3300, 0.012),
            ("Бектемирский район", 41.2100, 69.3350, 0.008),
            ("Янгихаётский район", 41.2100, 69.2450, 0.010),
        ],
    ),
    "tashkent": (
        "TOB",
        7.0,
        [
            ("г. Нурафшон", 41.0400, 69.3600, 0.012),
            ("г. Чирчик", 41.4690, 69.5820, 0.015),
            ("г. Алмалык", 40.8440, 69.5980, 0.015),
            ("г. Ангрен", 41.0170, 70.1440, 0.015),
            ("г. Янгиюль", 41.1120, 69.0470, 0.012),
        ],
    ),
    "samarkand": (
        "SAM",
        9.0,
        [
            ("г. Самарканд", 39.6542, 66.9597, 0.025),
            ("г. Каттакурган", 39.8990, 66.2560, 0.012),
            ("г. Ургут", 39.4020, 67.2430, 0.010),
        ],
    ),
    "fergana": (
        "FER",
        8.0,
        [
            ("г. Фергана", 40.3864, 71.7864, 0.020),
            ("г. Коканд", 40.5280, 70.9430, 0.018),
            ("г. Маргилан", 40.4710, 71.7250, 0.012),
            ("г. Кувасай", 40.3000, 71.9800, 0.010),
        ],
    ),
    "andijan": (
        "AND",
        7.0,
        [
            ("г. Андижан", 40.7821, 72.3442, 0.020),
            ("г. Асака", 40.6410, 72.2390, 0.010),
            ("г. Ханабад", 40.8000, 73.0000, 0.008),
        ],
    ),
    "namangan": (
        "NAM",
        6.5,
        [
            ("г. Наманган", 40.9983, 71.6726, 0.020),
            ("г. Чуст", 41.0030, 71.2370, 0.010),
            ("г. Касансай", 41.2430, 71.5480, 0.008),
        ],
    ),
    "kashkadarya": (
        "QAS",
        7.0,
        [
            ("г. Карши", 38.8606, 65.7891, 0.020),
            ("г. Шахрисабз", 39.0580, 66.8340, 0.012),
            ("г. Китаб", 39.1220, 66.8820, 0.008),
        ],
    ),
    "surkhandarya": (
        "SUR",
        5.0,
        [
            ("г. Термез", 37.2242, 67.2783, 0.018),
            ("г. Денау", 38.2670, 67.8990, 0.010),
            ("г. Шерабад", 37.6680, 67.0030, 0.008),
        ],
    ),
    "bukhara": (
        "BUX",
        5.0,
        [
            ("г. Бухара", 39.7681, 64.4556, 0.020),
            ("г. Каган", 39.7220, 64.5520, 0.010),
            ("г. Гиждуван", 40.1040, 64.6830, 0.008),
        ],
    ),
    "khorezm": (
        "XOR",
        4.0,
        [
            ("г. Ургенч", 41.5500, 60.6333, 0.018),
            ("г. Хива", 41.3780, 60.3640, 0.010),
            ("г. Ханка", 41.4700, 60.7900, 0.008),
        ],
    ),
    "karakalpakstan": (
        "QQR",
        4.0,
        [
            ("г. Нукус", 42.4600, 59.6100, 0.020),
            ("г. Ходжейли", 42.4040, 59.4520, 0.010),
            ("г. Турткуль", 41.5500, 61.0000, 0.010),
            ("г. Беруни", 41.6910, 60.7520, 0.008),
        ],
    ),
    "jizzakh": (
        "JIZ",
        3.0,
        [
            ("г. Джизак", 40.1158, 67.8422, 0.015),
            ("г. Галляарал", 40.0230, 67.5940, 0.008),
        ],
    ),
    "navoi": (
        "NAV",
        2.5,
        [
            ("г. Навои", 40.1039, 65.3688, 0.015),
            ("г. Зарафшан", 41.5740, 64.2000, 0.010),
            ("г. Учкудук", 42.1560, 63.5560, 0.008),
        ],
    ),
    "syrdarya": (
        "SIR",
        2.0,
        [
            ("г. Гулистан", 40.4897, 68.7842, 0.012),
            ("г. Янгиер", 40.2750, 68.8230, 0.008),
            ("г. Ширин", 40.2200, 69.1200, 0.006),
        ],
    ),
}

STREETS = [
    "ул. Амира Темура",
    "ул. Алишера Навои",
    "ул. Мустакиллик",
    "ул. Бобура",
    "ул. Шота Руставели",
    "ул. Мукими",
    "ул. Буюк Ипак Йули",
    "ул. Афросиаб",
    "ул. Бунёдкор",
    "ул. Фараби",
    "ул. Беруни",
    "ул. Мирзо Улугбека",
    "ул. Катартал",
    "ул. Ахунбабаева",
    "ул. Гагарина",
    "ул. Тараккиёт",
    "ул. Янги Хаёт",
    "ул. Истиклол",
    "ул. Навруз",
    "ул. Дустлик",
    "ул. Маърифат",
    "ул. Ипак йули",
    "ул. Матбуотчилар",
]

LANDMARKS = [
    "напротив станции метро",
    "рядом с хокимиятом",
    "у главного входа",
    "возле рынка",
    "рядом с почтой",
    "напротив школы №{n}",
    "у остановки",
    "рядом с аптекой",
    "во дворе бизнес-центра",
    "у входа в отделение банка",
    "рядом с вокзалом",
    "напротив махалли",
    "возле парка",
    "рядом с поликлиникой №{n}",
    "у супермаркета",
]

# код типа места → (вес, шаблоны названий)
PLACE_TYPES: dict[str, tuple[float, list[str]]] = {
    "branch": (0.30, ["Отделение «{city}-{n}»", "Центр банковских услуг №{n}", "Мини-банк №{n}"]),
    "mall": (0.20, ["ТЦ «{mall}», 1 этаж", "ТЦ «{mall}», у главного входа", "ТРЦ «{mall}», фудкорт"]),
    "shop": (0.15, ["Супермаркет «{shop}»", "Гипермаркет «{shop}»", "Магазин «{shop}»"]),
    "transport": (0.05, ["Железнодорожный вокзал", "Аэропорт, зона прилёта", "Автовокзал"]),
    "enterprise": (0.10, ["Предприятие «{company}», проходная", "Завод «{company}»", "Офисный центр «{company}»"]),
    "government": (0.10, ["Центр государственных услуг", "Хокимият района", "Налоговая инспекция"]),
    "street": (0.10, ["Отдельностоящий киоск", "Банкомат на фасаде здания", "Павильон у остановки"]),
}
MALLS = ["Бахор", "Олтин", "Ипак", "Зарафшан", "Навруз", "Шахристан", "Самаркандский", "Фаровон", "Гулзор", "Юлдуз"]
SHOPS = ["Мева", "Бозор-маркет", "Ташаббус", "Оила", "Хамкор", "Барака", "Сифат", "Доимий"]
COMPANIES = ["Узтекстиль", "Электроаппарат", "Агромаш", "Кимё-Сервис", "Пахта-Тола", "Курилиш-Инвест", "Энерго-Плюс"]

WORKING_HOURS = {
    "branch": "Пн–Пт 09:00–18:00",
    "mall": "Ежедневно 10:00–22:00",
    "shop": "Ежедневно 08:00–23:00",
    "transport": "Круглосуточно",
    "enterprise": "Пн–Сб 08:00–20:00",
    "government": "Пн–Пт 09:00–18:00",
    "street": "Круглосуточно",
}

SERVICE_VENDORS = [
    ("Сервис-вендор 1", "Jira Service Management", "NCR Atleos"),
    ("Сервис-вендор 2", "собственный портал заявок", "Hyosung TNS"),
    ("Сервис-вендор 3", "заявки по электронной почте", "Diebold Nixdorf"),
]
# GRG обслуживает второй вендор
VENDOR_FOR_MANUFACTURER = {"NCR Atleos": 0, "Hyosung TNS": 1, "Diebold Nixdorf": 2, "GRG Banking": 1}
SUPPLIERS = ["Поставщик А", "Поставщик Б"]

STATUS_WEIGHTS = {
    "in_service": 0.85,
    "repair": 0.03,
    "vendor_repair": 0.02,
    "on_farm": 0.01,
    "in_stock": 0.03,
    "in_delivery": 0.01,
    "installing": 0.02,
    "to_writeoff": 0.015,
    "written_off": 0.015,
}

EVENT_TYPES = {
    "breakdown": 0.55,
    "maintenance": 0.25,
    "module_replacement": 0.12,
    "software_update": 0.05,
    "vandalism": 0.02,
    "skimmer": 0.01,
}

PROBLEMS = {
    "breakdown": [
        "Картридер не возвращает карту",
        "Диспенсер не выдаёт купюры",
        "Замятие купюр в презентере",
        "Не печатает чек",
        "Нет связи с процессингом",
        "Зависание клиентского приложения",
        "Ошибка модуля приёма",
        "Не открывается шторка картридера",
        "Сенсорный экран не реагирует на нажатия",
    ],
    "maintenance": ["Плановое техническое обслуживание", "Чистка картридера и презентера", "Профилактика узлов"],
    "module_replacement": ["Износ узла", "Отказ узла после диагностики", "Повреждение узла"],
    "software_update": ["Обновление клиентского приложения", "Обновление EMV-ядра", "Обновление агента мониторинга"],
    "vandalism": ["Разбит экран", "Повреждена клавиатура", "Следы вскрытия корпуса"],
    "skimmer": ["Обнаружена накладка на картридер", "Обнаружена скрытая камера над клавиатурой"],
}

WORK_DONE = {
    "breakdown": ["Узел отрегулирован, проведено тестирование", "Перезагрузка и настройка ПО", "Устранено замятие"],
    "maintenance": ["Выполнено ТО по регламенту", "Проведена чистка и проверка узлов"],
    "module_replacement": ["Узел заменён, проведено тестирование"],
    "software_update": ["ПО обновлено, проверены транзакции"],
    "vandalism": ["Повреждённые элементы заменены"],
    "skimmer": ["Устройство изъято, картридер проверен, передано в службу безопасности"],
}

# тип узла → (вероятность замены при ремонте с заменой, производитель → модель узла)
REPLACEABLE = {
    "card_reader": 0.35,
    "dispenser": 0.20,
    "receipt_printer": 0.20,
    "epp": 0.10,
    "pc": 0.10,
    "nfc_reader": 0.05,
}

MODULE_MODELS = {
    "card_reader": {
        "NCR Atleos": "IMCRW",
        "Hyosung TNS": "MCU-3000",
        "Diebold Nixdorf": "CRDM-V2",
        "GRG Banking": "CRT-591",
    },
    "nfc_reader": {
        "NCR Atleos": "CLR-NFC",
        "Hyosung TNS": "CLR-200",
        "Diebold Nixdorf": "DN CL Reader",
        "GRG Banking": "GRG-CL",
    },
    "epp": {"NCR Atleos": "EPP 6.0", "Hyosung TNS": "EPP-8000R", "Diebold Nixdorf": "EPP V7", "GRG Banking": "ZT598"},
    "dispenser": {
        "NCR Atleos": "S2 Dispenser",
        "Hyosung TNS": "CDU-8000",
        "Diebold Nixdorf": "CMD-V6",
        "GRG Banking": "CDM8240N",
    },
    "cash_in": {"NCR Atleos": "SCPM", "Hyosung TNS": "BRM-20", "Diebold Nixdorf": "RM4", "GRG Banking": "CRM9250N"},
    "receipt_printer": {"*": "TP-80 термопринтер"},
    "camera": {"*": "IP-камера 2 Мп"},
    "sensors": {"*": "SIU-панель"},
    "pc": {"*": "ПК Intel Core i5"},
    "monitor": {"*": "LCD-монитор"},
    "antiskimming": {"*": "Активная антискимминговая защита"},
    "ups": {"*": "ИБП 1 кВА"},
}

CLIENT_APPS = [("KAL Kalignite", ["4.3", "4.4", "4.5"])]
EMV_KERNELS = [("EMV-ядро банка", ["2.1", "2.2", "3.0"])]
MONITORING = [("Агент мониторинга", ["1.8", "2.0", "2.1"])]
SECURITY = [("Защита и контроль целостности", ["5.2", "5.4", "6.0"])]
XFS_VERSIONS = ["3.30", "3.40", "3.50"]
