from __future__ import annotations

import json
from pathlib import Path

from feed_cleaner.classify import ClassifiedRow, classify_row, deduplicate_by_sku
from feed_cleaner.models import FieldOutcome, Reason, Status
from feed_cleaner.parsing import PriceValue
from feed_cleaner.report import build_report, format_summary, write_report

_ALL_REASON_VALUES = {reason.value for reason in Reason}


def _malformed_row() -> ClassifiedRow:
    return ClassifiedRow(
        sku=FieldOutcome[str](status=Status.REJECTED, value=None),
        name=FieldOutcome[str](status=Status.REJECTED, value=None),
        price=FieldOutcome[PriceValue](status=Status.REJECTED, value=None),
        quantity=FieldOutcome[int](status=Status.REJECTED, value=None),
        category=FieldOutcome[str | None](status=Status.REJECTED, value=None),
        status=Status.REJECTED,
        reasons=[Reason.MALFORMED_ROW],
    )


def test_zero_rows_all_counters_zero_no_crash() -> None:
    report = build_report([])

    assert report.row_counts == {"total": 0, "ok": 0, "repaired": 0, "rejected": 0}
    assert set(report.repaired_reasons) == _ALL_REASON_VALUES
    assert all(count == 0 for count in report.repaired_reasons.values())
    assert set(report.rejected_reasons) == _ALL_REASON_VALUES
    assert all(count == 0 for count in report.rejected_reasons.values())


def test_reason_not_encountered_still_present_with_zero_count() -> None:
    row = classify_row({"sku": "A1", "name": "Foo", "price": "10", "quantity": "1"})

    report = build_report([row])

    assert report.repaired_reasons[Reason.PRICE_FORMAT.value] == 0
    assert report.rejected_reasons[Reason.MISSING_SKU.value] == 0


def test_repaired_row_with_two_reasons_counted_separately_row_counts_once() -> None:
    row = classify_row({"sku": "A1", "name": "Foo", "price": "10", "quantity": "-10.0"})
    assert row.status is Status.REPAIRED

    report = build_report([row])

    assert report.row_counts["repaired"] == 1
    assert report.repaired_reasons[Reason.NEGATIVE_QUANTITY.value] == 1
    assert report.repaired_reasons[Reason.QUANTITY_FORMAT.value] == 1


def test_row_with_rejected_field_and_repaired_field_counts_only_rejected() -> None:
    row = classify_row({"sku": "", "name": "Foo", "price": "29,99 zł", "quantity": "1"})
    assert row.status is Status.REJECTED
    assert row.price.status is Status.REPAIRED

    report = build_report([row])

    assert report.row_counts["rejected"] == 1
    assert report.row_counts["repaired"] == 0
    assert report.rejected_reasons[Reason.MISSING_SKU.value] == 1
    assert report.repaired_reasons[Reason.PRICE_FORMAT.value] == 0
    assert report.rejected_reasons[Reason.PRICE_FORMAT.value] == 0


def test_duplicate_sku_counted_once_per_rejected_duplicate() -> None:
    rows = [
        classify_row({"sku": "A1", "name": "Foo", "price": "10", "quantity": "1"}),
        classify_row({"sku": "A1", "name": "Bar", "price": "20", "quantity": "2"}),
        classify_row({"sku": "A1", "name": "Baz", "price": "30", "quantity": "3"}),
    ]
    deduped = deduplicate_by_sku(rows)

    report = build_report(deduped)

    assert report.row_counts["ok"] == 1
    assert report.row_counts["rejected"] == 2
    assert report.rejected_reasons[Reason.DUPLICATE_SKU.value] == 2


def test_malformed_row_counted_in_rejected_reasons() -> None:
    report = build_report([_malformed_row()])

    assert report.row_counts["rejected"] == 1
    assert report.rejected_reasons[Reason.MALFORMED_ROW.value] == 1


def test_row_counts_always_sum_to_total() -> None:
    rows = [
        classify_row({"sku": "A1", "name": "Foo", "price": "10", "quantity": "1"}),
        classify_row({"sku": "A2", "name": "Bar", "price": "29,99 zł", "quantity": "1"}),
        classify_row({"sku": "", "name": "Baz", "price": "10", "quantity": "1"}),
        _malformed_row(),
    ]

    report = build_report(rows)

    counts = report.row_counts
    assert counts["ok"] + counts["repaired"] + counts["rejected"] == counts["total"]
    assert counts["total"] == 4


def test_write_report_creates_output_directory_and_valid_json(tmp_path: Path) -> None:
    row = classify_row({"sku": "A1", "name": "Foo", "price": "10", "quantity": "1"})
    report = build_report([row])
    output_path = tmp_path / "nested" / "dir" / "report.json"

    write_report(report, output_path)

    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["row_counts"]["total"] == 1
    assert data["row_counts"]["ok"] == 1


def test_format_summary_contains_row_counts() -> None:
    row = classify_row({"sku": "A1", "name": "Foo", "price": "10", "quantity": "1"})
    report = build_report([row])

    summary = format_summary(report)

    assert "Total: 1" in summary
    assert "OK: 1" in summary
