from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class AtmRow(BaseModel):
    id: int
    atm_code: str
    status_code: str
    status: str
    manufacturer: str
    model: str
    device_type: str
    branch: str
    region: str
    city_district: str | None
    address: str | None
    place_type: str | None
    latitude: Decimal | None
    longitude: Decimal | None
    is_24h: bool | None
    contactless: bool
    commissioning_date: date | None
    warranty_until: date | None
    terminal_id: str | None
    currencies: str | None


class AtmPage(BaseModel):
    items: list[AtmRow]
    total: int
    page: int
    page_size: int


class MapPoints(BaseModel):
    """Компактный формат для карты: [id, код, широта, долгота, код статуса]."""

    points: list[tuple[int, str, float, float, str]]
    total: int
    without_location: int


class AtmIn(BaseModel):
    atm_code: str = Field(min_length=1, max_length=40)
    serial_number: str = Field(min_length=1, max_length=80)
    inventory_number: str | None = Field(default=None, max_length=80)
    model_id: int
    device_type_id: int
    install_format_id: int
    branch_id: int
    purchase_date: date | None = None
    commissioning_date: date | None = None
    notes: str | None = None
    screen_size_in: Decimal | None = Field(default=None, gt=0, lt=100)
    screen_resolution: str | None = Field(default=None, max_length=20)
    screen_orientation_id: int | None = None
    input_method_id: int | None = None
    screen_sunlight: bool | None = None
    privacy_filter: bool | None = None
    safe_class_id: int | None = None
    safe_lock_id: int | None = None
    service_access_id: int | None = None
    cassette_count: int | None = Field(default=None, ge=0, le=20)
    contactless: bool = False
    audio_jack: bool | None = None
    ups: bool | None = None
    currencies: list[str] = Field(default_factory=lambda: ["UZS"])
    service_ids: list[int] = Field(default_factory=list)
    scheme_ids: list[int] = Field(default_factory=list)


class AtmCreate(AtmIn):
    status_id: int | None = None  # по умолчанию «На складе банка»


class ProcessingIn(BaseModel):
    processing_id: int
    terminal_id: str = Field(min_length=1, max_length=40)
    merchant_id: str = Field(min_length=1, max_length=40)
    host_protocol_id: int | None = None
    connection_type_id: int | None = None
    ip_address: str | None = Field(default=None, max_length=45)


class ContractIn(BaseModel):
    supplier_id: int | None = None
    purchase_contract: str | None = Field(default=None, max_length=200)
    purchase_price: Decimal | None = Field(default=None, ge=0)
    price_currency: str | None = None
    warranty_until: date | None = None
    auto_warranty: bool = False  # посчитать от даты покупки и гарантийного срока модели
    service_vendor_id: int | None = None
    service_sla_hours: int | None = Field(default=None, ge=0, le=10000)


class AtmCard(BaseModel):
    """Карточка банкомата целиком. Вложенные разделы — словари: их структура описана в коде сборки."""

    id: int
    atm_code: str
    edit: AtmCreate
    header: dict[str, Any]
    main: dict[str, Any]
    config: dict[str, Any]
    location: dict[str, Any] | None
    placements: list[dict[str, Any]]
    processings: list[dict[str, Any]]
    modules: list[dict[str, Any]]
    software: list[dict[str, Any]]
    service_events: list[dict[str, Any]]
    certificates: list[dict[str, Any]]
    status_history: list[dict[str, Any]]
    contract: dict[str, Any] | None
    updated_at: datetime
