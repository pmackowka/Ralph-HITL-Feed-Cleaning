from __future__ import annotations

import dataclasses
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from pydantic import ValidationError

from feed_cleaner.classify import classify_row
from feed_cleaner.export import SCHEMA, export_to_parquet
from feed_cleaner.models import FieldOutcome, ProductRecord, Status


def test_exports_repaired_values_not_raw_text(tmp_path: Path) -> None:
    row = classify_row({"sku": "A1", "name": "Foo", "price": "29,99 zł", "quantity": "-5"})
    output_path = tmp_path / "clean.parquet"

    export_to_parquet([row], output_path)

    table = pq.read_table(output_path)
    assert table.column("price").to_pylist() == [29.99]
    assert table.column("quantity").to_pylist() == [5]
    assert table.column("currency").to_pylist() == ["PLN"]
    assert table.column("sku").to_pylist() == ["A1"]
    assert table.column("name").to_pylist() == ["Foo"]


def test_rejected_rows_are_skipped(tmp_path: Path) -> None:
    ok_row = classify_row({"sku": "A1", "name": "Foo", "price": "10", "quantity": "1"})
    rejected_row = classify_row({"sku": "", "name": "Bar", "price": "10", "quantity": "1"})
    output_path = tmp_path / "clean.parquet"

    export_to_parquet([ok_row, rejected_row], output_path)

    table = pq.read_table(output_path)
    assert table.num_rows == 1
    assert table.column("sku").to_pylist() == ["A1"]


def test_zero_accepted_records_writes_valid_empty_parquet_with_schema(tmp_path: Path) -> None:
    rejected_row = classify_row({"sku": "", "name": "Bar", "price": "10", "quantity": "1"})
    output_path = tmp_path / "clean.parquet"

    export_to_parquet([rejected_row], output_path)

    table = pq.read_table(output_path)
    assert table.num_rows == 0
    assert table.schema.equals(SCHEMA)


def test_creates_output_directory_if_missing(tmp_path: Path) -> None:
    row = classify_row({"sku": "A1", "name": "Foo", "price": "10", "quantity": "1"})
    output_path = tmp_path / "nested" / "dir" / "clean.parquet"

    export_to_parquet([row], output_path)

    assert output_path.exists()


def test_none_category_and_currency_written_as_null_no_crash(tmp_path: Path) -> None:
    row = classify_row({"sku": "A1", "name": "Foo", "price": "10", "quantity": "1"})
    output_path = tmp_path / "clean.parquet"

    export_to_parquet([row], output_path)

    table = pq.read_table(output_path)
    assert table.column("category").to_pylist() == [None]
    assert table.column("currency").to_pylist() == [None]


def test_empty_input_list_writes_valid_empty_parquet(tmp_path: Path) -> None:
    output_path = tmp_path / "clean.parquet"

    export_to_parquet([], output_path)

    table = pq.read_table(output_path)
    assert table.num_rows == 0
    assert table.schema.equals(SCHEMA)


def test_schema_is_derived_from_product_record() -> None:
    """SCHEMA nie jest pisany ręcznie — dopisanie pola do ProductRecord ma samo
    dołożyć kolumnę, żeby kształt rekordu miał jedno źródło prawdy.
    """
    assert SCHEMA.names == list(ProductRecord.model_fields)
    assert SCHEMA.field("price").type == pa.float64()
    assert SCHEMA.field("quantity").type == pa.int64()
    assert not SCHEMA.field("sku").nullable
    assert SCHEMA.field("category").nullable


def test_accepted_row_missing_required_value_fails_loudly(tmp_path: Path) -> None:
    """Wiersz zaakceptowany, ale z pustym wymaganym polem, nie może po cichu
    trafić do Parquet — kontrakt pilnuje ProductRecord tuż przed zapisem.
    """
    row = classify_row({"sku": "A1", "name": "Foo", "price": "10", "quantity": "1"})
    broken = dataclasses.replace(row, price=FieldOutcome(status=Status.OK, value=None))

    with pytest.raises(ValidationError):
        export_to_parquet([broken], tmp_path / "clean.parquet")
