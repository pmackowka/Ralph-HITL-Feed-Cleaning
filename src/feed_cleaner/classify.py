"""Kompozycja statusu wiersza z wyników walidacji pól + osobny przebieg dedup po SKU."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace

from feed_cleaner.models import FieldOutcome, Reason, Status
from feed_cleaner.parsing import PriceValue, parse_name, parse_price, parse_quantity, parse_sku

RawRow = Mapping[str, str | None]


@dataclass(frozen=True)
class ClassifiedRow:
    """Wynik klasyfikacji jednego wiersza feedu na bazie wyników wszystkich pól."""

    sku: FieldOutcome[str]
    name: FieldOutcome[str]
    price: FieldOutcome[PriceValue]
    quantity: FieldOutcome[int]
    category: FieldOutcome[str | None]
    status: Status
    reasons: list[Reason] = field(default_factory=list)


def _parse_category(raw: str | None) -> FieldOutcome[str | None]:
    if raw is None:
        return FieldOutcome(status=Status.CLEAN, value=None)
    stripped = raw.strip()
    return FieldOutcome(status=Status.CLEAN, value=stripped or None)


def classify_row(raw: RawRow) -> ClassifiedRow:
    """Klasyfikuje wiersz na bazie NIEZALEŻNYCH wyników wszystkich pięciu pól —
    celowo nie przez próbę konstrukcji ProductRecord, bo to nie pozwoliłoby
    ocenić np. samego sku, gdy price jest jednocześnie zepsute.
    """
    sku_outcome = parse_sku(raw.get("sku"))
    name_outcome = parse_name(raw.get("name"))
    price_outcome = parse_price(raw.get("price"))
    quantity_outcome = parse_quantity(raw.get("quantity"))
    category_outcome = _parse_category(raw.get("category"))

    statuses = [
        sku_outcome.status,
        name_outcome.status,
        price_outcome.status,
        quantity_outcome.status,
        category_outcome.status,
    ]
    reasons: list[Reason] = [
        *sku_outcome.reasons,
        *name_outcome.reasons,
        *price_outcome.reasons,
        *quantity_outcome.reasons,
        *category_outcome.reasons,
    ]

    if Status.REJECTED in statuses:
        status = Status.REJECTED
    elif Status.REPAIRED in statuses:
        status = Status.REPAIRED
    else:
        status = Status.CLEAN

    return ClassifiedRow(
        sku=sku_outcome,
        name=name_outcome,
        price=price_outcome,
        quantity=quantity_outcome,
        category=category_outcome,
        status=status,
        reasons=reasons,
    )


def deduplicate_by_sku(rows: list[ClassifiedRow]) -> list[ClassifiedRow]:
    """Keep-first dedup po SKU, w kolejności wejściowej listy `rows`.

    Wiersze z sku=None (już REJECTED missing_sku) są pomijane — nie biorą
    udziału w dedup ani między sobą, ani z innymi wierszami.
    """
    seen: set[str] = set()
    result: list[ClassifiedRow] = []
    for row in rows:
        sku_value = row.sku.value
        if sku_value is None:
            result.append(row)
            continue
        if sku_value in seen:
            result.append(
                replace(row, status=Status.REJECTED, reasons=[*row.reasons, Reason.DUPLICATE_SKU])
            )
        else:
            seen.add(sku_value)
            result.append(row)
    return result
