from feed_cleaner.classify import RawRow, classify_row, deduplicate_by_sku
from feed_cleaner.models import Reason, Status


def _row(
    sku: str | None = "A1",
    name: str | None = "Czajnik",
    price: str | None = "29.99",
    quantity: str | None = "5",
    category: str | None = "AGD",
) -> RawRow:
    return {"sku": sku, "name": name, "price": price, "quantity": quantity, "category": category}


class TestClassifyRow:
    def test_row_with_no_problems_is_ok(self) -> None:
        result = classify_row(_row())
        assert result.status is Status.OK
        assert result.reasons == []

    def test_row_with_repairs_in_multiple_fields_is_repaired_with_all_reasons(self) -> None:
        result = classify_row(_row(price="29,99 zł", quantity="-5"))
        assert result.status is Status.REPAIRED
        assert result.reasons == [Reason.PRICE_FORMAT, Reason.NEGATIVE_QUANTITY]

    def test_one_rejected_field_and_one_repaired_field_is_rejected_with_both_reasons(self) -> None:
        result = classify_row(_row(name="", quantity="-5"))
        assert result.status is Status.REJECTED
        assert result.reasons == [Reason.MISSING_NAME, Reason.NEGATIVE_QUANTITY]

    def test_blank_sku_and_broken_price_together_are_rejected_with_both_reasons(self) -> None:
        result = classify_row(_row(sku="", price="abc"))
        assert result.status is Status.REJECTED
        assert result.reasons == [Reason.MISSING_SKU, Reason.INVALID_PRICE]

    def test_category_missing_is_clean_and_does_not_affect_row_status(self) -> None:
        result = classify_row(_row(category=None))
        assert result.status is Status.OK
        assert result.category.status is Status.OK
        assert result.category.value is None


class TestDeduplicateBySku:
    def test_two_rows_same_sku_both_otherwise_ok(self) -> None:
        rows = [classify_row(_row()), classify_row(_row())]
        result = deduplicate_by_sku(rows)
        assert result[0].status is Status.OK
        assert result[0].reasons == []
        assert result[1].status is Status.REJECTED
        assert result[1].reasons == [Reason.DUPLICATE_SKU]

    def test_three_or_more_rows_same_sku_only_first_kept(self) -> None:
        rows = [classify_row(_row()), classify_row(_row()), classify_row(_row())]
        result = deduplicate_by_sku(rows)
        assert result[0].status is Status.OK
        assert result[1].status is Status.REJECTED
        assert result[1].reasons == [Reason.DUPLICATE_SKU]
        assert result[2].status is Status.REJECTED
        assert result[2].reasons == [Reason.DUPLICATE_SKU]

    def test_first_occurrence_rejected_on_its_own_keeps_original_reason_not_duplicate(self) -> None:
        rows = [classify_row(_row(price="abc")), classify_row(_row())]
        result = deduplicate_by_sku(rows)
        assert result[0].status is Status.REJECTED
        assert result[0].reasons == [Reason.INVALID_PRICE]
        assert result[1].status is Status.REJECTED
        assert result[1].reasons == [Reason.DUPLICATE_SKU]

    def test_duplicate_sku_is_appended_to_existing_reasons_not_replacing_them(self) -> None:
        rows = [classify_row(_row()), classify_row(_row(quantity="-5"))]
        result = deduplicate_by_sku(rows)
        assert result[1].status is Status.REJECTED
        assert result[1].reasons == [Reason.NEGATIVE_QUANTITY, Reason.DUPLICATE_SKU]

    def test_two_rows_with_blank_sku_are_independent_and_not_flagged_as_duplicate(self) -> None:
        rows = [classify_row(_row(sku="")), classify_row(_row(sku=""))]
        result = deduplicate_by_sku(rows)
        assert result[0].status is Status.REJECTED
        assert result[0].reasons == [Reason.MISSING_SKU]
        assert result[1].status is Status.REJECTED
        assert result[1].reasons == [Reason.MISSING_SKU]

    def test_input_order_is_preserved_in_output(self) -> None:
        rows = [
            classify_row(_row(sku="A1")),
            classify_row(_row(sku="B2")),
            classify_row(_row(sku="C3")),
        ]
        result = deduplicate_by_sku(rows)
        assert [row.sku.value for row in result] == ["A1", "B2", "C3"]
