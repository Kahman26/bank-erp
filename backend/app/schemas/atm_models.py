from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class AtmModelIn(BaseModel):
    manufacturer_id: int
    model_name: str = Field(min_length=1, max_length=100)
    series: str | None = Field(default=None, max_length=100)
    device_type_id: int
    install_format_ids: list[int] = Field(default_factory=list)
    height_mm: int | None = Field(default=None, gt=0)
    width_mm: int | None = Field(default=None, gt=0)
    depth_mm: int | None = Field(default=None, gt=0)
    weight_kg: int | None = Field(default=None, gt=0)
    screen_options: str | None = Field(default=None, max_length=100)
    max_cassettes: int | None = Field(default=None, ge=0)
    cassette_capacity: int | None = Field(default=None, ge=0)
    max_notes_per_dispense: int | None = Field(default=None, ge=0)
    recycling: bool = False
    cash_in: bool = False
    max_denominations: int | None = Field(default=None, ge=0)
    supported_os: str | None = Field(default=None, max_length=200)
    power_supply: str | None = Field(default=None, max_length=100)
    operating_temp: str | None = Field(default=None, max_length=100)
    humidity: str | None = Field(default=None, max_length=100)
    end_of_support_date: date | None = None
    warranty_months: int | None = Field(default=None, ge=0, le=240)
    spec_url: str | None = Field(default=None, max_length=500)


class AtmModelOut(AtmModelIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    manufacturer_name: str
    device_type_name: str
    atm_count: int = 0
