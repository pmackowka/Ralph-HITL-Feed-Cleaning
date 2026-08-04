"""Eksport zaakceptowanych (OK/REPAIRED) rekordów do Parquet; REJECTED pomijane."""

from __future__ import annotations

from pathlib import Path
from typing import get_args

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic.fields import FieldInfo

from feed_cleaner.classify import ClassifiedRow
from feed_cleaner.models import ProductRecord, Status

_ARROW_TYPES: dict[object, pa.DataType] = {
    str: pa.string(),
    float: pa.float64(),
    int: pa.int64(),
}


def _arrow_field(name: str, info: FieldInfo) -> pa.Field:
    """Mapuje pole ProductRecord na kolumnę Parquet. Pole opcjonalne w schemacie
    (`str | None` z domyślnym None) → kolumna nullable.
    """
    non_none = [arg for arg in get_args(info.annotation) if arg is not type(None)]
    base_type = non_none[0] if non_none else info.annotation
    if base_type not in _ARROW_TYPES:
        raise TypeError(f"Brak mapowania Parquet dla pola '{name}': {base_type!r}")
    return pa.field(name, _ARROW_TYPES[base_type], nullable=not info.is_required())


SCHEMA = pa.schema(
    [_arrow_field(name, info) for name, info in ProductRecord.model_fields.items()]
)


def _to_record(row: ClassifiedRow) -> ProductRecord:
    """Składa wiersz w ProductRecord tuż przed zapisem. To jedyna walidacja kontraktu
    na wyjściu — pipeline celowo nie konstruuje ProductRecord wcześniej (patrz docstring
    `classify_row`), więc bez tego kroku nic nie pilnowałoby, czy zaakceptowany wiersz
    faktycznie wypełnia schemat. Brak wymaganego pola → ValidationError, nie cichy zapis.
    """
    price = row.price.value
    return ProductRecord.model_validate(
        {
            "sku": row.sku.value,
            "name": row.name.value,
            "price": price.price if price is not None else None,
            "quantity": row.quantity.value,
            "category": row.category.value,
            "currency": price.currency if price is not None else None,
        }
    )


def export_to_parquet(rows: list[ClassifiedRow], output_path: Path) -> None:
    """Zapisuje wartości PO naprawie dla wierszy OK/REPAIRED. Zawsze tworzy plik
    z pełnym schematem SCHEMA, nawet gdy 0 wierszy zostało zaakceptowanych.
    """
    records = [_to_record(row) for row in rows if row.status is not Status.REJECTED]

    table = pa.table(
        {
            name: pa.array(
                [getattr(record, name) for record in records],
                type=SCHEMA.field(name).type,
            )
            for name in ProductRecord.model_fields
        },
        schema=SCHEMA,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, output_path)
