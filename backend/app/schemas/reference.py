from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DictItemOut(ORM):
    id: int
    kind: str
    code: str
    name: str
    sort: int
    is_active: bool
    extra: dict


class DictItemIn(BaseModel):
    code: str = Field(min_length=1, max_length=40, pattern=r"^[a-z0-9_]+$")
    name: str = Field(min_length=1, max_length=200)
    sort: int = 0
    is_active: bool = True
    extra: dict = Field(default_factory=dict)


class DictItemPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    sort: int | None = None
    is_active: bool | None = None
    extra: dict | None = None


class RegionOut(ORM):
    id: int
    code: str
    name: str
    sort: int
    center_lat: Decimal | None
    center_lon: Decimal | None


class RegionIn(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=100)
    sort: int = 0
    center_lat: Decimal | None = None
    center_lon: Decimal | None = None


class BranchOut(ORM):
    id: int
    name: str
    region_id: int
    address: str | None
    is_active: bool


class BranchIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    region_id: int
    address: str | None = Field(default=None, max_length=300)
    is_active: bool = True


class ManufacturerOut(ORM):
    id: int
    name: str
    country: str | None
    website: str | None


class ManufacturerIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    website: str | None = Field(default=None, max_length=300)


class VendorOut(ORM):
    id: int
    name: str
    is_service: bool
    is_supplier: bool
    contact: str | None
    ticket_system: str | None
    is_active: bool


class VendorIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    is_service: bool = True
    is_supplier: bool = False
    contact: str | None = Field(default=None, max_length=300)
    ticket_system: str | None = Field(default=None, max_length=200)
    is_active: bool = True


class CodeNameOut(ORM):
    id: int
    code: str
    name: str
    sort: int


class CodeNameIn(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=100)
    sort: int = 0


class CurrencyOut(ORM):
    code: str
    name: str
    sort: int


class ReferenceBundle(BaseModel):
    """Всё, что нужно интерфейсу для выпадающих списков, одним запросом."""

    dicts: dict[str, list[DictItemOut]]
    regions: list[RegionOut]
    branches: list[BranchOut]
    manufacturers: list[ManufacturerOut]
    vendors: list[VendorOut]
    processings: list[CodeNameOut]
    payment_schemes: list[CodeNameOut]
    currencies: list[CurrencyOut]
    dict_kinds: dict[str, str]
