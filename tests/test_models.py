import pytest
from pydantic import ValidationError

from feed_cleaner.models import FieldOutcome, ProductRecord, Reason, Status


def test_field_outcome_clean_defaults_to_no_reasons() -> None:
    outcome: FieldOutcome[int] = FieldOutcome(status=Status.CLEAN, value=5)
    assert outcome.status is Status.CLEAN
    assert outcome.value == 5
    assert outcome.reasons == []


def test_field_outcome_rejected_carries_reason() -> None:
    outcome: FieldOutcome[int] = FieldOutcome(
        status=Status.REJECTED, value=None, reasons=[Reason.MISSING_QUANTITY]
    )
    assert outcome.value is None
    assert outcome.reasons == [Reason.MISSING_QUANTITY]


def test_product_record_happy_path() -> None:
    record = ProductRecord(
        sku="A1", name="Czajnik", price=29.99, quantity=5, category="AGD", currency="PLN"
    )
    assert record.sku == "A1"
    assert record.price == 29.99
    assert record.quantity == 5
    assert record.category == "AGD"
    assert record.currency == "PLN"


@pytest.mark.parametrize("sku", ["", "   "])
def test_product_record_rejects_blank_sku(sku: str) -> None:
    with pytest.raises(ValidationError) as exc_info:
        ProductRecord(sku=sku, name="Czajnik", price=29.99, quantity=5)
    assert Reason.MISSING_SKU.value in str(exc_info.value)


def test_product_record_rejects_blank_name() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ProductRecord(sku="A1", name="", price=29.99, quantity=5)
    assert Reason.MISSING_NAME.value in str(exc_info.value)


def test_product_record_blank_category_becomes_none() -> None:
    record = ProductRecord(sku="A1", name="Czajnik", price=29.99, quantity=5, category="")
    assert record.category is None


def test_product_record_missing_category_and_currency_default_to_none() -> None:
    record = ProductRecord(sku="A1", name="Czajnik", price=29.99, quantity=5)
    assert record.category is None
    assert record.currency is None
