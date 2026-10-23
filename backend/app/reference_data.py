"""Базовые значения справочников (раздел 4 набора полей v0.2). Загружаются командой bootstrap."""

from app.models.reference import DictKind

DICT_KIND_LABELS: dict[DictKind, str] = {
    DictKind.ATM_STATUS: "Статусы банкомата",
    DictKind.DEVICE_TYPE: "Типы устройств",
    DictKind.INSTALL_FORMAT: "Форматы установки",
    DictKind.ATM_SERVICE: "Функции банкомата",
    DictKind.SCREEN_ORIENTATION: "Ориентация экрана",
    DictKind.INPUT_METHOD: "Способы ввода",
    DictKind.SAFE_CLASS: "Классы сейфа",
    DictKind.SAFE_LOCK: "Типы замка сейфа",
    DictKind.SERVICE_ACCESS: "Доступ для обслуживания",
    DictKind.MODULE_TYPE: "Типы узлов",
    DictKind.SOFTWARE_TYPE: "Типы ПО",
    DictKind.HOST_PROTOCOL: "Протоколы хоста",
    DictKind.CONNECTION_TYPE: "Каналы связи",
    DictKind.PLACE_TYPE: "Типы мест",
    DictKind.ACCESS_TYPE: "Доступ к месту",
    DictKind.MOVE_REASON: "Причины перемещения",
    DictKind.SERVICE_EVENT_TYPE: "Типы событий обслуживания",
    DictKind.CERT_TYPE: "Виды сертификатов",
    DictKind.CERT_SOURCE: "Кем предоставлен сертификат",
}

# (code, name) или (code, name, extra)
DICTS: dict[DictKind, list[tuple]] = {
    DictKind.ATM_STATUS: [
        ("in_stock", "На складе банка"),
        ("in_delivery", "В доставке"),
        ("installing", "В установке"),
        ("in_service", "В эксплуатации"),
        ("on_farm", "На ферме"),
        ("repair", "На ремонте"),
        ("vendor_repair", "На ремонте у вендора"),
        ("to_writeoff", "К списанию"),
        ("written_off", "Списан"),
    ],
    DictKind.DEVICE_TYPE: [
        ("dispenser", "Выдача наличных"),
        ("cash_in", "С приёмом наличных"),
        ("recycler", "Ресайклер"),
    ],
    DictKind.INSTALL_FORMAT: [
        ("lobby", "В помещении (lobby)"),
        ("ttw", "Сквозь стену"),
        ("drive_up", "Драйв-ап"),
        ("kiosk", "Отдельностоящий киоск"),
    ],
    DictKind.ATM_SERVICE: [
        ("withdrawal", "Выдача наличных"),
        ("deposit", "Приём наличных"),
        ("payments", "Платежи"),
        ("transfers", "Переводы"),
        ("contactless", "Бесконтактное обслуживание"),
        ("qr", "Снятие по QR"),
    ],
    DictKind.SCREEN_ORIENTATION: [("landscape", "Альбомная"), ("portrait", "Книжная")],
    DictKind.INPUT_METHOD: [("touch", "Сенсорный экран"), ("fdk", "Боковые кнопки (FDK)"), ("both", "Оба")],
    DictKind.SAFE_CLASS: [
        ("ul291_bh", "UL 291 Business Hours"),
        ("ul291_l1", "UL 291 Level 1"),
        ("cen_l", "CEN L"),
        ("cen_1", "CEN I"),
        ("cen_3", "CEN III"),
        ("cen_4", "CEN IV"),
    ],
    DictKind.SAFE_LOCK: [("mechanical", "Механический кодовый"), ("electronic", "Электронный")],
    DictKind.SERVICE_ACCESS: [("front", "Фронтальный"), ("rear", "Тыльный")],
    DictKind.MODULE_TYPE: [
        ("card_reader", "Картридер (контактный)", {"xfs": "IDC", "affects_certification": True}),
        ("nfc_reader", "Бесконтактный ридер (NFC)", {"xfs": "IDC", "affects_certification": True}),
        ("epp", "PIN-клавиатура (EPP)", {"xfs": "PIN", "affects_certification": True}),
        ("dispenser", "Диспенсер", {"xfs": "CDM"}),
        ("cash_in", "Модуль приёма / рециркуляции", {"xfs": "CIM"}),
        ("receipt_printer", "Чековый принтер", {"xfs": "PTR"}),
        ("journal_printer", "Журнальный принтер", {"xfs": "PTR"}),
        ("camera", "Камера", {"xfs": "CAM"}),
        ("sensors", "Датчики и индикаторы", {"xfs": "SIU"}),
        ("barcode", "Сканер штрих- и QR-кодов", {"xfs": "BCR"}),
        ("pc", "Системный блок (ПК)"),
        ("monitor", "Монитор"),
        ("antiskimming", "Антискимминговое устройство"),
        ("ups", "ИБП"),
    ],
    DictKind.SOFTWARE_TYPE: [
        ("xfs", "XFS-платформа"),
        ("client", "Клиентское приложение"),
        ("emv", "EMV-ядро"),
        ("security", "Защита и контроль целостности"),
        ("monitoring", "Агент мониторинга"),
    ],
    DictKind.HOST_PROTOCOL: [("ndc", "NDC"), ("ddc", "DDC")],
    DictKind.CONNECTION_TYPE: [("ethernet", "Проводной (Ethernet)"), ("lte", "4G"), ("vsat", "Спутник (VSAT)")],
    DictKind.PLACE_TYPE: [
        ("branch", "Отделение банка"),
        ("mall", "ТЦ"),
        ("shop", "Магазин"),
        ("transport", "Вокзал, аэропорт"),
        ("enterprise", "Предприятие"),
        ("government", "Госучреждение"),
        ("street", "Улица"),
    ],
    DictKind.ACCESS_TYPE: [("public", "Публичный"), ("restricted", "Ограниченный")],
    DictKind.MOVE_REASON: [
        ("low_load", "Низкая загрузка"),
        ("point_closed", "Закрытие точки"),
        ("lease_end", "Окончание аренды"),
        ("renovation", "Ремонт помещения"),
        ("partner_request", "Запрос партнёра"),
        ("new_point", "Новая точка"),
    ],
    DictKind.SERVICE_EVENT_TYPE: [
        ("breakdown", "Поломка"),
        ("maintenance", "Плановое ТО"),
        ("module_replacement", "Замена узла"),
        ("software_update", "Обновление ПО"),
        ("vandalism", "Вандализм"),
        ("skimmer", "Обнаружен скиммер"),
    ],
    DictKind.CERT_TYPE: [
        ("scheme", "Сертификация терминала в ПС"),
        ("emv_l1_contact", "EMV L1 контактный"),
        ("emv_l1_contactless", "EMV L1 бесконтактный"),
        ("emv_l2", "EMV L2 (ядро)"),
        ("pci_pts", "PCI PTS (EPP)"),
    ],
    DictKind.CERT_SOURCE: [
        ("supplier", "Поставщик оборудования"),
        ("vendor", "Сервисный вендор"),
        ("scheme", "Платёжная система"),
    ],
}

# code, name, широта и долгота административного центра
REGIONS = [
    ("tashkent_city", "г. Ташкент", 41.311081, 69.240562),
    ("tashkent", "Ташкентская обл.", 41.040000, 69.360000),
    ("andijan", "Андижанская обл.", 40.782100, 72.344200),
    ("bukhara", "Бухарская обл.", 39.768100, 64.455600),
    ("jizzakh", "Джизакская обл.", 40.115800, 67.842200),
    ("kashkadarya", "Кашкадарьинская обл.", 38.860600, 65.789100),
    ("navoi", "Навоийская обл.", 40.103900, 65.368800),
    ("namangan", "Наманганская обл.", 40.998300, 71.672600),
    ("samarkand", "Самаркандская обл.", 39.654200, 66.959700),
    ("surkhandarya", "Сурхандарьинская обл.", 37.224200, 67.278300),
    ("syrdarya", "Сырдарьинская обл.", 40.489700, 68.784200),
    ("fergana", "Ферганская обл.", 40.386400, 71.786400),
    ("khorezm", "Хорезмская обл.", 41.550000, 60.633300),
    ("karakalpakstan", "Республика Каракалпакстан", 42.460000, 59.610000),
]

CURRENCIES = [("UZS", "Узбекский сум"), ("USD", "Доллар США")]

PAYMENT_SCHEMES = [
    ("uzcard", "Uzcard"),
    ("humo", "Humo"),
    ("visa", "Visa"),
    ("mastercard", "Mastercard"),
    ("unionpay", "UnionPay"),
]

PROCESSINGS = [("own", "Собственный процессинг банка"), ("uzcard", "Uzcard"), ("humo", "Humo")]
