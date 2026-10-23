"""PDF-карточка банкомата (ReportLab). Кириллице нужен TTF-шрифт: в контейнере — DejaVu из fonts-dejavu-core."""

import io
from datetime import date, datetime
from functools import cache
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.schemas.atms import AtmCard

FONT_CANDIDATES = [
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("/Library/Fonts/Arial Unicode.ttf", "/Library/Fonts/Arial Unicode.ttf"),
]
BRAND = colors.HexColor("#1F4E79")
GRID = colors.HexColor("#BFBFBF")
BAND = colors.HexColor("#F2F2F2")


@cache
def _fonts() -> tuple[str, str]:
    for regular, bold in FONT_CANDIDATES:
        if Path(regular).is_file() and Path(bold).is_file():
            pdfmetrics.registerFont(TTFont("Body", regular))
            pdfmetrics.registerFont(TTFont("Body-Bold", bold))
            return "Body", "Body-Bold"
    raise RuntimeError("Не найден шрифт с кириллицей для PDF (нужен пакет fonts-dejavu-core)")


def _fmt(v) -> str:
    if v is None or v == "":
        return "—"
    if isinstance(v, bool):
        return "да" if v else "нет"
    if isinstance(v, datetime):
        return v.strftime("%d.%m.%Y %H:%M")
    if isinstance(v, date):
        return v.strftime("%d.%m.%Y")
    if isinstance(v, str) and len(v) == 10 and v[4] == "-" and v[7] == "-":
        return f"{v[8:]}.{v[5:7]}.{v[:4]}"
    return str(v)


def atm_pdf(card: AtmCard, author: str) -> bytes:
    body, bold = _fonts()
    text = ParagraphStyle("t", fontName=body, fontSize=8.5, leading=11)
    head = ParagraphStyle("h", fontName=bold, fontSize=11, leading=14, textColor=BRAND, spaceBefore=8, spaceAfter=4)
    title = ParagraphStyle("title", fontName=bold, fontSize=17, leading=21, textColor=BRAND)
    muted = ParagraphStyle("m", parent=text, textColor=colors.HexColor("#595959"))

    def p(v) -> Paragraph:
        return Paragraph(_fmt(v).replace("&", "&amp;").replace("<", "&lt;"), text)

    def pairs(items: list[tuple[str, object]]) -> Table:
        rows = [[Paragraph(f"<font name='{bold}'>{k}</font>", text), p(v)] for k, v in items]
        t = Table(rows, colWidths=[45 * mm, 135 * mm])
        t.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        return t

    def grid(header: list[str], rows: list[list[object]], widths: list[float]) -> Table:
        data = [[Paragraph(f"<font color='white' name='{bold}'>{h}</font>", text) for h in header]]
        data += [[p(c) for c in r] for r in rows]
        t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1)
        style = [
            ("BACKGROUND", (0, 0), (-1, 0), BRAND),
            ("GRID", (0, 0), (-1, -1), 0.4, GRID),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
        style += [("BACKGROUND", (0, i), (-1, i), BAND) for i in range(2, len(data), 2)]
        t.setStyle(TableStyle(style))
        return t

    h, m, c = card.header, card.main, card.config
    story = [
        Paragraph(f"{card.atm_code} · {h['status']}", title),
        Paragraph(f"{h['model']} · {h['device_type']}" + (f" · {h['address']}" if h.get("address") else ""), muted),
        Spacer(1, 6),
        Paragraph("Банкомат", head),
        pairs(
            [
                ("Серийный номер", m["serial_number"]),
                ("Инвентарный номер", m["inventory_number"]),
                ("Формат установки", m["install_format"]),
                ("Филиал", m["branch"]),
                ("Покупка", m["purchase_date"]),
                ("Ввод в эксплуатацию", m["commissioning_date"]),
                ("Валюты", ", ".join(m["currencies"])),
                ("Принимаемые карты", ", ".join(m["schemes"])),
                ("Функции", ", ".join(m["services"])),
                ("Поддержка модели до", m["end_of_support_date"]),
            ]
        ),
        Paragraph("Комплектация", head),
        pairs(
            [
                ("Экран", f"{_fmt(c['screen_size_in'])}\" {c['screen_resolution'] or ''}".strip()),
                ("Способ ввода", c["input_method"]),
                ("Кассет", c["cassette_count"]),
                ("Сейф", " · ".join(x for x in (c["safe_class"], c["safe_lock"]) if x) or None),
                ("NFC", c["contactless"]),
                ("ИБП", c["ups"]),
            ]
        ),
    ]
    if card.location:
        loc = card.location
        story += [
            Paragraph("Место установки", head),
            pairs(
                [
                    ("Точка", loc["name"]),
                    ("Адрес", f"{loc['region']}, {loc['city_district']}, {loc['address']}"),
                    ("Ориентир", loc["landmark"]),
                    ("Тип места", loc["place_type"]),
                    ("Режим работы", loc["working_hours"]),
                    ("Координаты", f"{loc['latitude']:.6f}, {loc['longitude']:.6f}"),
                ]
            ),
        ]
    if card.processings:
        story += [
            Paragraph("Процессинги", head),
            grid(
                ["Процессинг", "Terminal ID", "Merchant ID", "Канал"],
                [[x["processing"], x["terminal_id"], x["merchant_id"], x["connection_type"]] for x in card.processings],
                [55, 40, 40, 45],
            ),
        ]
    installed = [x for x in card.modules if not x["removed_at"]]
    if installed:
        story += [
            Paragraph("Установленные узлы", head),
            grid(
                ["Узел", "Модель", "Серийный №", "Установлен"],
                [
                    [
                        x["type"],
                        " ".join(filter(None, (x["vendor"], x["model"]))),
                        x["serial_number"],
                        x["installed_at"],
                    ]
                    for x in installed
                ],
                [55, 55, 40, 30],
            ),
        ]
    certs = [x for x in card.certificates if x["status"] != "valid" or x["needs_review"]]
    if certs:
        story += [
            Paragraph("Сертификаты, требующие внимания", head),
            grid(
                ["Объект", "Вид", "ПС", "Действует до", "Статус"],
                [
                    [
                        x["object_label"],
                        x["cert_type"],
                        x["payment_scheme"],
                        x["valid_until"],
                        x["status_label"] + (" · проверить" if x["needs_review"] else ""),
                    ]
                    for x in certs
                ],
                [50, 45, 22, 25, 38],
            ),
        ]
    if card.service_events:
        story += [
            Paragraph("Последние ремонты", head),
            grid(
                ["Начало", "Тип", "Неисправность", "Исполнитель", "Простой, ч"],
                [
                    [
                        x["started_at"],
                        x["type"],
                        x["problem"],
                        x["performer"],
                        x["downtime_hours"] if x["downtime_hours"] is not None else "открыт",
                    ]
                    for x in card.service_events[:10]
                ],
                [28, 30, 62, 35, 25],
            ),
        ]
    if card.contract:
        k = card.contract
        story += [
            Paragraph("Гарантия и договор", head),
            pairs(
                [
                    ("Окончание гарантии", k["warranty_until"]),
                    ("Сервисный вендор", k["service_vendor"]),
                    ("SLA, ч", k["service_sla_hours"]),
                    ("Поставщик", k["supplier"]),
                    ("Договор поставки", k["purchase_contract"]),
                ]
            ),
        ]

    buf = io.BytesIO()

    def footer(canvas, doc) -> None:
        canvas.setFont(body, 7)
        canvas.setFillColor(colors.HexColor("#7F7F7F"))
        canvas.drawString(15 * mm, 10 * mm, f"Справочник банкоматов · сформировано {date.today():%d.%m.%Y}, {author}")
        canvas.drawRightString(195 * mm, 10 * mm, f"стр. {doc.page}")

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=18 * mm,
        title=f"Банкомат {card.atm_code}",
        author=author,
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()
