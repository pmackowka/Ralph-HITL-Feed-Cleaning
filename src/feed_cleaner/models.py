"""Współdzielone typy: status/powód walidacji pola oraz docelowy schemat rekordu."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import BaseModel, field_validator

T = TypeVar("T")


class Status(StrEnum):
    CLEAN = "CLEAN"
    REPAIRED = "REPAIRED"
    REJECTED = "REJECTED"


class Reason(StrEnum):
    PRICE_FORMAT = "price_format"
    NEGATIVE_QUANTITY = "negative_quantity"
    QUANTITY_FORMAT = "quantity_format"
    MISSING_SKU = "missing_sku"
    MISSING_NAME = "missing_name"
    MISSING_PRICE = "missing_price"
    INVALID_PRICE = "invalid_price"
    MISSING_QUANTITY = "missing_quantity"
    INVALID_QUANTITY_TYPE = "invalid_quantity_type"
    DUPLICATE_SKU = "duplicate_sku"
    MALFORMED_ROW = "malformed_row"


@dataclass(frozen=True)
class FieldOutcome(Generic[T]):
    """Wynik walidacji/naprawy pojedynczego pola. `reasons` puste dla CLEAN."""

    status: Status
    value: T | None
    reasons: list[Reason] = field(default_factory=list)


class ProductRecord(BaseModel):
    """Docelowy, już wyczyszczony rekord produktu (schemat eksportu)."""

    sku: str
    name: str
    price: float
    quantity: int
    category: str | None = None
    currency: str | None = None

    @field_validator("sku")
    @classmethod
    def _reject_blank_sku(cls, value: str) -> str:
        if not value.strip():
            raise ValueError(Reason.MISSING_SKU.value)
        return value

    @field_validator("name")
    @classmethod
    def _reject_blank_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError(Reason.MISSING_NAME.value)
        return value

    @field_validator("category")
    @classmethod
    def _blank_category_to_none(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            return None
        return value
