"""Eksport zaakceptowanych (OK/REPAIRED) rekordów do Parquet; REJECTED pomijane."""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from feed_cleaner.classify import ClassifiedRow
from feed_cleaner.models import Status

SCHEMA = pa.schema(
    [
        pa.field("sku", pa.string(), nullable=False),
        pa.field("name", pa.string(), nullable=False),
        pa.field("price", pa.float64(), nullable=False),
        pa.field("quantity", pa.int64(), nullable=False),
        pa.field("category", pa.string(), nullable=True),
        pa.field("currency", pa.string(), nullable=True),
    ]
)


def export_to_parquet(rows: list[ClassifiedRow], output_path: Path) -> None:
    """Zapisuje wartości PO naprawie dla wierszy OK/REPAIRED. Zawsze tworzy plik
    z pełnym schematem SCHEMA, nawet gdy 0 wierszy zostało zaakceptowanych.
    """
    accepted = [row for row in rows if row.status is not Status.REJECTED]

    sku: list[str] = []
    name: list[str] = []
    price: list[float] = []
    quantity: list[int] = []
    category: list[str | None] = []
    currency: list[str | None] = []

    for row in accepted:
        assert row.sku.value is not None
        assert row.name.value is not None
        assert row.price.value is not None
        assert row.quantity.value is not None
        sku.append(row.sku.value)
        name.append(row.name.value)
        price.append(row.price.value.price)
        quantity.append(row.quantity.value)
        category.append(row.category.value)
        currency.append(row.price.value.currency)

    table = pa.table(
        {
            "sku": pa.array(sku, type=pa.string()),
            "name": pa.array(name, type=pa.string()),
            "price": pa.array(price, type=pa.float64()),
            "quantity": pa.array(quantity, type=pa.int64()),
            "category": pa.array(category, type=pa.string()),
            "currency": pa.array(currency, type=pa.string()),
        },
        schema=SCHEMA,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, output_path)
