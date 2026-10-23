"""Банкомат и всё, что к нему относится (раздел 3 набора полей v0.2)."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
    false,
    func,
    text,
    true,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import Timestamps
from app.models.reference import (
    Branch,
    Currency,
    DictItem,
    Manufacturer,
    PaymentScheme,
    Processing,
    Region,
    Vendor,
)

# --- 3.2 Модель банкомата ---------------------------------------------------------------------------


class AtmModel(Timestamps, Base):
    __tablename__ = "atm_model"
    __table_args__ = (UniqueConstraint("manufacturer_id", "model_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    manufacturer_id: Mapped[int] = mapped_column(ForeignKey("manufacturer.id"))
    model_name: Mapped[str] = mapped_column(String(100))
    series: Mapped[str | None] = mapped_column(String(100))
    device_type_id: Mapped[int] = mapped_column(ForeignKey("dict_item.id"))
    install_format_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=list, server_default="{}")
    height_mm: Mapped[int | None]
    width_mm: Mapped[int | None]
    depth_mm: Mapped[int | None]
    weight_kg: Mapped[int | None]
    screen_options: Mapped[str | None] = mapped_column(String(100))
    max_cassettes: Mapped[int | None]
    cassette_capacity: Mapped[int | None]
    max_notes_per_dispense: Mapped[int | None]
    recycling: Mapped[bool] = mapped_column(default=False, server_default=false())
    cash_in: Mapped[bool] = mapped_column(default=False, server_default=false())
    max_denominations: Mapped[int | None]
    supported_os: Mapped[str | None] = mapped_column(String(200))
    power_supply: Mapped[str | None] = mapped_column(String(100))
    operating_temp: Mapped[str | None] = mapped_column(String(100))
    humidity: Mapped[str | None] = mapped_column(String(100))
    end_of_support_date: Mapped[date | None] = mapped_column(Date)
    warranty_months: Mapped[int | None]
    spec_url: Mapped[str | None] = mapped_column(String(500))

    manufacturer: Mapped[Manufacturer] = relationship()
    device_type: Mapped[DictItem] = relationship()


# --- 3.1 Банкомат -----------------------------------------------------------------------------------

atm_currency = Table(
    "atm_currency",
    Base.metadata,
    Column("atm_id", ForeignKey("atm.id", ondelete="CASCADE"), primary_key=True),
    Column("currency_code", ForeignKey("currency.code"), primary_key=True),
)

atm_service = Table(
    "atm_service",
    Base.metadata,
    Column("atm_id", ForeignKey("atm.id", ondelete="CASCADE"), primary_key=True),
    Column("service_id", ForeignKey("dict_item.id"), primary_key=True),
)

atm_scheme = Table(
    "atm_scheme",
    Base.metadata,
    Column("atm_id", ForeignKey("atm.id", ondelete="CASCADE"), primary_key=True),
    Column("scheme_id", ForeignKey("payment_scheme.id"), primary_key=True),
)


class Atm(Timestamps, Base):
    __tablename__ = "atm"

    id: Mapped[int] = mapped_column(primary_key=True)
    atm_code: Mapped[str] = mapped_column(String(40), unique=True)
    serial_number: Mapped[str] = mapped_column(String(80), unique=True)
    inventory_number: Mapped[str | None] = mapped_column(String(80))
    model_id: Mapped[int] = mapped_column(ForeignKey("atm_model.id"), index=True)
    device_type_id: Mapped[int] = mapped_column(ForeignKey("dict_item.id"))
    install_format_id: Mapped[int] = mapped_column(ForeignKey("dict_item.id"))
    status_id: Mapped[int] = mapped_column(ForeignKey("dict_item.id"), index=True)
    purchase_date: Mapped[date | None] = mapped_column(Date)
    commissioning_date: Mapped[date | None] = mapped_column(Date)
    decommission_date: Mapped[date | None] = mapped_column(Date)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branch.id"), index=True)
    notes: Mapped[str | None] = mapped_column(Text)

    # 3.1.1 комплектация
    screen_size_in: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    screen_resolution: Mapped[str | None] = mapped_column(String(20))
    screen_orientation_id: Mapped[int | None] = mapped_column(ForeignKey("dict_item.id"))
    input_method_id: Mapped[int | None] = mapped_column(ForeignKey("dict_item.id"))
    screen_sunlight: Mapped[bool | None]
    privacy_filter: Mapped[bool | None]
    safe_class_id: Mapped[int | None] = mapped_column(ForeignKey("dict_item.id"))
    safe_lock_id: Mapped[int | None] = mapped_column(ForeignKey("dict_item.id"))
    service_access_id: Mapped[int | None] = mapped_column(ForeignKey("dict_item.id"))
    cassette_count: Mapped[int | None]
    contactless: Mapped[bool] = mapped_column(default=False, server_default=false())
    audio_jack: Mapped[bool | None]
    ups: Mapped[bool | None]

    model: Mapped[AtmModel] = relationship()
    branch: Mapped[Branch] = relationship()
    status: Mapped[DictItem] = relationship(foreign_keys=[status_id])
    device_type: Mapped[DictItem] = relationship(foreign_keys=[device_type_id])
    install_format: Mapped[DictItem] = relationship(foreign_keys=[install_format_id])
    currencies: Mapped[list[Currency]] = relationship(secondary=atm_currency, order_by=Currency.sort)
    services: Mapped[list[DictItem]] = relationship(secondary=atm_service, order_by=DictItem.sort)
    schemes: Mapped[list[PaymentScheme]] = relationship(secondary=atm_scheme, order_by=PaymentScheme.sort)
    processings: Mapped[list["AtmProcessing"]] = relationship(
        back_populates="atm", cascade="all, delete-orphan", order_by="AtmProcessing.processing_id"
    )


class AtmStatusHistory(Base):
    __tablename__ = "atm_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    atm_id: Mapped[int] = mapped_column(ForeignKey("atm.id", ondelete="CASCADE"), index=True)
    status_id: Mapped[int] = mapped_column(ForeignKey("dict_item.id"))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    changed_by_id: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"))
    comment: Mapped[str | None] = mapped_column(Text)

    status: Mapped[DictItem] = relationship()


# --- 3.3 Узлы, 3.4 ПО ---------------------------------------------------------------------------------


class Module(Timestamps, Base):
    __tablename__ = "module"
    __table_args__ = (
        Index("ix_module_installed", "atm_id", postgresql_where=text("removed_at is null")),
        CheckConstraint("removed_at is null or removed_at >= installed_at", name="dates"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    atm_id: Mapped[int] = mapped_column(ForeignKey("atm.id", ondelete="CASCADE"), index=True)
    module_type_id: Mapped[int] = mapped_column(ForeignKey("dict_item.id"))
    vendor: Mapped[str | None] = mapped_column(String(100))
    model: Mapped[str | None] = mapped_column(String(100))
    serial_number: Mapped[str] = mapped_column(String(80))
    firmware_version: Mapped[str | None] = mapped_column(String(50))
    installed_at: Mapped[date] = mapped_column(Date)
    removed_at: Mapped[date | None] = mapped_column(Date)
    is_faulty: Mapped[bool] = mapped_column(default=False, server_default=false())
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    module_type: Mapped[DictItem] = relationship()


class Software(Base):
    __tablename__ = "software"

    id: Mapped[int] = mapped_column(primary_key=True)
    atm_id: Mapped[int] = mapped_column(ForeignKey("atm.id", ondelete="CASCADE"), index=True)
    software_type_id: Mapped[int] = mapped_column(ForeignKey("dict_item.id"))
    name: Mapped[str] = mapped_column(String(100))
    version: Mapped[str] = mapped_column(String(50))
    installed_at: Mapped[date | None] = mapped_column(Date)

    software_type: Mapped[DictItem] = relationship()


# --- 3.5 Подключение к процессингам -------------------------------------------------------------------


class AtmProcessing(Base):
    __tablename__ = "atm_processing"
    __table_args__ = (
        UniqueConstraint("atm_id", "processing_id"),
        UniqueConstraint("processing_id", "terminal_id", name="uq_atm_processing_terminal"),
        UniqueConstraint("processing_id", "merchant_id", name="uq_atm_processing_merchant"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    atm_id: Mapped[int] = mapped_column(ForeignKey("atm.id", ondelete="CASCADE"))
    processing_id: Mapped[int] = mapped_column(ForeignKey("processing.id"))
    terminal_id: Mapped[str] = mapped_column(String(40))
    merchant_id: Mapped[str] = mapped_column(String(40))
    host_protocol_id: Mapped[int | None] = mapped_column(ForeignKey("dict_item.id"))
    connection_type_id: Mapped[int | None] = mapped_column(ForeignKey("dict_item.id"))
    ip_address: Mapped[str | None] = mapped_column(String(45))

    atm: Mapped[Atm] = relationship(back_populates="processings")
    processing: Mapped[Processing] = relationship()


# --- 3.6 Локация, 3.7 Размещение ---------------------------------------------------------------------


class Location(Timestamps, Base):
    __tablename__ = "location"
    __table_args__ = (
        # примерные границы Узбекистана — ловим перепутанные широту и долготу
        CheckConstraint("latitude between 37 and 46 and longitude between 55 and 74", name="uz_bounds"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    region_id: Mapped[int] = mapped_column(ForeignKey("region.id"), index=True)
    city_district: Mapped[str] = mapped_column(String(150))
    address: Mapped[str] = mapped_column(String(300))
    landmark: Mapped[str | None] = mapped_column(String(300))
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    place_type_id: Mapped[int] = mapped_column(ForeignKey("dict_item.id"))
    indoor: Mapped[bool] = mapped_column(default=True, server_default=true())
    access_type_id: Mapped[int | None] = mapped_column(ForeignKey("dict_item.id"))
    is_24h: Mapped[bool] = mapped_column(default=False, server_default=false())
    working_hours: Mapped[str] = mapped_column(String(200))
    premises_owner: Mapped[str | None] = mapped_column(String(200))
    site_contact: Mapped[str | None] = mapped_column(String(200))

    region: Mapped[Region] = relationship()
    place_type: Mapped[DictItem] = relationship(foreign_keys=[place_type_id])


class Placement(Base):
    """История размещений. Пересечение периодов запрещено exclusion constraint (см. миграцию)."""

    __tablename__ = "placement"
    __table_args__ = (
        Index("uq_placement_current", "atm_id", unique=True, postgresql_where=text("placed_to is null")),
        CheckConstraint("placed_to is null or placed_to >= placed_from", name="dates"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    atm_id: Mapped[int] = mapped_column(ForeignKey("atm.id", ondelete="CASCADE"), index=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("location.id"), index=True)
    placed_from: Mapped[date] = mapped_column(Date)
    placed_to: Mapped[date | None] = mapped_column(Date)
    move_reason_id: Mapped[int | None] = mapped_column(ForeignKey("dict_item.id"))
    basis_document: Mapped[str | None] = mapped_column(String(200))
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    location: Mapped[Location] = relationship()
    move_reason: Mapped[DictItem | None] = relationship()


# --- 3.8 События обслуживания -----------------------------------------------------------------------


class ServiceEvent(Timestamps, Base):
    __tablename__ = "service_event"
    __table_args__ = (
        CheckConstraint("finished_at is null or finished_at >= started_at", name="dates"),
        CheckConstraint("vendor_id is not null or by_bank_engineer", name="performer"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    atm_id: Mapped[int] = mapped_column(ForeignKey("atm.id", ondelete="CASCADE"), index=True)
    event_type_id: Mapped[int] = mapped_column(ForeignKey("dict_item.id"))
    ticket_number: Mapped[str | None] = mapped_column(String(80))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    module_id: Mapped[int | None] = mapped_column(ForeignKey("module.id", ondelete="SET NULL"))
    problem: Mapped[str] = mapped_column(Text)
    work_done: Mapped[str | None] = mapped_column(Text)
    affects_certification: Mapped[bool] = mapped_column(default=False, server_default=false())
    vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendor.id"))
    by_bank_engineer: Mapped[bool] = mapped_column(default=False, server_default=false())
    cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    cost_currency: Mapped[str | None] = mapped_column(ForeignKey("currency.code"))
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"))

    event_type: Mapped[DictItem] = relationship()
    vendor: Mapped[Vendor | None] = relationship()
    replacements: Mapped[list["ModuleReplacement"]] = relationship(cascade="all, delete-orphan")


class ModuleReplacement(Base):
    __tablename__ = "module_replacement"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("service_event.id", ondelete="CASCADE"), index=True)
    removed_module_id: Mapped[int] = mapped_column(ForeignKey("module.id"))
    installed_module_id: Mapped[int] = mapped_column(ForeignKey("module.id"))


# --- 3.9 Сертификаты --------------------------------------------------------------------------------


class Certificate(Timestamps, Base):
    __tablename__ = "certificate"
    __table_args__ = (
        CheckConstraint("num_nonnulls(atm_model_id, atm_id, module_id) = 1", name="one_object"),
        CheckConstraint("manual_status in ('renewal', 'revoked')", name="manual_status"),
        CheckConstraint("valid_until >= issued_at", name="dates"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    atm_model_id: Mapped[int | None] = mapped_column(ForeignKey("atm_model.id", ondelete="CASCADE"), index=True)
    atm_id: Mapped[int | None] = mapped_column(ForeignKey("atm.id", ondelete="CASCADE"), index=True)
    module_id: Mapped[int | None] = mapped_column(ForeignKey("module.id", ondelete="CASCADE"), index=True)
    cert_type_id: Mapped[int] = mapped_column(ForeignKey("dict_item.id"))
    # EMV L1/L2 и PCI PTS выдают не платёжные системы — для них поле пустое
    payment_scheme_id: Mapped[int | None] = mapped_column(ForeignKey("payment_scheme.id"))
    cert_number: Mapped[str] = mapped_column(String(100))
    issued_at: Mapped[date] = mapped_column(Date)
    valid_until: Mapped[date] = mapped_column(Date, index=True)
    # «На продлении» / «Отозван» ставят вручную; остальные статусы считаются по датам
    manual_status: Mapped[str | None] = mapped_column(String(20))
    source_id: Mapped[int | None] = mapped_column(ForeignKey("dict_item.id"))
    document_path: Mapped[str | None] = mapped_column(String(300))
    needs_review: Mapped[bool] = mapped_column(default=False, server_default=false())

    cert_type: Mapped[DictItem] = relationship(foreign_keys=[cert_type_id])
    payment_scheme: Mapped[PaymentScheme | None] = relationship()


# --- 3.10 Договоры и гарантия ------------------------------------------------------------------------


class Contract(Timestamps, Base):
    __tablename__ = "contract"

    id: Mapped[int] = mapped_column(primary_key=True)
    atm_id: Mapped[int] = mapped_column(ForeignKey("atm.id", ondelete="CASCADE"), unique=True)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("vendor.id"))
    purchase_contract: Mapped[str | None] = mapped_column(String(200))
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    price_currency: Mapped[str | None] = mapped_column(ForeignKey("currency.code"))
    warranty_until: Mapped[date | None] = mapped_column(Date, index=True)
    service_vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendor.id"))
    service_sla_hours: Mapped[int | None]

    supplier: Mapped[Vendor | None] = relationship(foreign_keys=[supplier_id])
    service_vendor: Mapped[Vendor | None] = relationship(foreign_keys=[service_vendor_id])
