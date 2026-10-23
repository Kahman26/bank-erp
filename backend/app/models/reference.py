"""Справочники (раздел 4 набора полей)."""

from enum import StrEnum

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint, false, true
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class DictKind(StrEnum):
    """Простые списки, которые администратор правит сам. Порядок — порядок в интерфейсе."""

    ATM_STATUS = "atm_status"
    DEVICE_TYPE = "device_type"
    INSTALL_FORMAT = "install_format"
    ATM_SERVICE = "atm_service"
    SCREEN_ORIENTATION = "screen_orientation"
    INPUT_METHOD = "input_method"
    SAFE_CLASS = "safe_class"
    SAFE_LOCK = "safe_lock"
    SERVICE_ACCESS = "service_access"
    MODULE_TYPE = "module_type"
    SOFTWARE_TYPE = "software_type"
    HOST_PROTOCOL = "host_protocol"
    CONNECTION_TYPE = "connection_type"
    PLACE_TYPE = "place_type"
    ACCESS_TYPE = "access_type"
    MOVE_REASON = "move_reason"
    SERVICE_EVENT_TYPE = "service_event_type"
    CERT_TYPE = "cert_type"
    CERT_SOURCE = "cert_source"


class DictItem(Base):
    __tablename__ = "dict_item"
    __table_args__ = (UniqueConstraint("kind", "code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(200))
    sort: Mapped[int] = mapped_column(default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())
    # доп. атрибуты конкретного списка, например класс XFS у типа узла
    extra: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")


class Region(Base):
    __tablename__ = "region"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    sort: Mapped[int] = mapped_column(default=0, server_default="0")
    # центр — для карты и генератора тестовых данных
    center_lat: Mapped[float | None] = mapped_column(Numeric(9, 6))
    center_lon: Mapped[float | None] = mapped_column(Numeric(9, 6))


class Branch(Base):
    __tablename__ = "branch"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("region.id"))
    address: Mapped[str | None] = mapped_column(String(300))
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())

    region: Mapped[Region] = relationship()


class Manufacturer(Base):
    __tablename__ = "manufacturer"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    country: Mapped[str | None] = mapped_column(String(100))
    website: Mapped[str | None] = mapped_column(String(300))


class Vendor(Base):
    """Сервисные компании, которые ремонтируют банкоматы, и поставщики."""

    __tablename__ = "vendor"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    is_service: Mapped[bool] = mapped_column(default=True, server_default=true())
    is_supplier: Mapped[bool] = mapped_column(default=False, server_default=false())
    contact: Mapped[str | None] = mapped_column(String(300))
    ticket_system: Mapped[str | None] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())


class Processing(Base):
    __tablename__ = "processing"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    sort: Mapped[int] = mapped_column(default=0, server_default="0")


class PaymentScheme(Base):
    __tablename__ = "payment_scheme"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    sort: Mapped[int] = mapped_column(default=0, server_default="0")


class Currency(Base):
    __tablename__ = "currency"

    code: Mapped[str] = mapped_column(String(3), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    sort: Mapped[int] = mapped_column(default=0, server_default="0")
