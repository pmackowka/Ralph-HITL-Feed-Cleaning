import pytest

from feed_cleaner.models import Reason, Status
from feed_cleaner.parsing import parse_name, parse_price, parse_quantity, parse_sku


class TestParsePrice:
    def test_bare_positive_number_is_clean(self) -> None:
        outcome = parse_price("29.99")
        assert outcome.status is Status.OK
        assert outcome.reasons == []
        assert outcome.value is not None
        assert outcome.value.price == pytest.approx(29.99)
        assert outcome.value.currency is None

    def test_comma_decimal_and_pln_suffix_is_repaired(self) -> None:
        outcome = parse_price("29,99 zł")
        assert outcome.status is Status.REPAIRED
        assert outcome.reasons == [Reason.PRICE_FORMAT]
        assert outcome.value is not None
        assert outcome.value.price == pytest.approx(29.99)
        assert outcome.value.currency == "PLN"

    def test_dot_decimal_with_currency_suffix_is_still_repaired(self) -> None:
        outcome = parse_price("29.99 zł")
        assert outcome.status is Status.REPAIRED
        assert outcome.reasons == [Reason.PRICE_FORMAT]
        assert outcome.value is not None
        assert outcome.value.price == pytest.approx(29.99)
        assert outcome.value.currency == "PLN"

    @pytest.mark.parametrize("raw", ["", None])
    def test_empty_or_none_is_rejected_missing_price(self, raw: str | None) -> None:
        outcome = parse_price(raw)
        assert outcome.status is Status.REJECTED
        assert outcome.reasons == [Reason.MISSING_PRICE]
        assert outcome.value is None

    def test_non_numeric_is_rejected_invalid_price(self) -> None:
        outcome = parse_price("abc")
        assert outcome.status is Status.REJECTED
        assert outcome.reasons == [Reason.INVALID_PRICE]
        assert outcome.value is None

    @pytest.mark.parametrize("raw", ["0", "-5"])
    def test_non_positive_after_parsing_is_rejected_invalid_price(self, raw: str) -> None:
        outcome = parse_price(raw)
        assert outcome.status is Status.REJECTED
        assert outcome.reasons == [Reason.INVALID_PRICE]
        assert outcome.value is None

    def test_prefix_dollar_is_recognized_as_usd(self) -> None:
        outcome = parse_price("$45.00")
        assert outcome.status is Status.REPAIRED
        assert outcome.value is not None
        assert outcome.value.currency == "USD"
        assert outcome.value.price == pytest.approx(45.00)

    def test_suffix_code_usd_is_recognized(self) -> None:
        outcome = parse_price("45.00 USD")
        assert outcome.status is Status.REPAIRED
        assert outcome.value is not None
        assert outcome.value.currency == "USD"
        assert outcome.value.price == pytest.approx(45.00)

    def test_suffix_symbol_eur_with_comma_is_recognized(self) -> None:
        outcome = parse_price("99,90 €")
        assert outcome.status is Status.REPAIRED
        assert outcome.reasons == [Reason.PRICE_FORMAT]
        assert outcome.value is not None
        assert outcome.value.currency == "EUR"
        assert outcome.value.price == pytest.approx(99.90)

    def test_surrounding_whitespace_only_is_still_clean(self) -> None:
        outcome = parse_price("  29.99  ")
        assert outcome.status is Status.OK
        assert outcome.reasons == []

    def test_currency_matching_is_case_insensitive(self) -> None:
        outcome = parse_price("45.00 Usd")
        assert outcome.status is Status.REPAIRED
        assert outcome.value is not None
        assert outcome.value.currency == "USD"


class TestParseQuantity:
    def test_bare_nonnegative_int_is_clean(self) -> None:
        outcome = parse_quantity("5")
        assert outcome.status is Status.OK
        assert outcome.value == 5
        assert outcome.reasons == []

    def test_negative_int_is_repaired_negative_quantity(self) -> None:
        outcome = parse_quantity("-5")
        assert outcome.status is Status.REPAIRED
        assert outcome.value == 5
        assert outcome.reasons == [Reason.NEGATIVE_QUANTITY]

    def test_integral_float_text_dot_is_repaired_quantity_format(self) -> None:
        outcome = parse_quantity("10.0")
        assert outcome.status is Status.REPAIRED
        assert outcome.value == 10
        assert outcome.reasons == [Reason.QUANTITY_FORMAT]

    def test_integral_float_text_comma_is_repaired_quantity_format(self) -> None:
        outcome = parse_quantity("10,0")
        assert outcome.status is Status.REPAIRED
        assert outcome.value == 10
        assert outcome.reasons == [Reason.QUANTITY_FORMAT]

    def test_negative_integral_float_has_both_reasons_in_order(self) -> None:
        outcome = parse_quantity("-10.0")
        assert outcome.status is Status.REPAIRED
        assert outcome.value == 10
        assert outcome.reasons == [Reason.NEGATIVE_QUANTITY, Reason.QUANTITY_FORMAT]

    def test_non_integral_float_is_rejected_invalid_quantity_type(self) -> None:
        outcome = parse_quantity("10.5")
        assert outcome.status is Status.REJECTED
        assert outcome.reasons == [Reason.INVALID_QUANTITY_TYPE]
        assert outcome.value is None

    def test_non_numeric_text_is_rejected_invalid_quantity_type(self) -> None:
        outcome = parse_quantity("dziesięć")
        assert outcome.status is Status.REJECTED
        assert outcome.reasons == [Reason.INVALID_QUANTITY_TYPE]
        assert outcome.value is None

    @pytest.mark.parametrize("raw", ["", None])
    def test_empty_or_none_is_rejected_missing_quantity(self, raw: str | None) -> None:
        outcome = parse_quantity(raw)
        assert outcome.status is Status.REJECTED
        assert outcome.reasons == [Reason.MISSING_QUANTITY]
        assert outcome.value is None


class TestParseSku:
    def test_non_blank_is_clean(self) -> None:
        outcome = parse_sku("A1")
        assert outcome.status is Status.OK
        assert outcome.value == "A1"
        assert outcome.reasons == []

    def test_strips_surrounding_whitespace(self) -> None:
        outcome = parse_sku("  A1  ")
        assert outcome.status is Status.OK
        assert outcome.value == "A1"

    @pytest.mark.parametrize("raw", ["", "   ", None])
    def test_blank_or_none_is_rejected_missing_sku(self, raw: str | None) -> None:
        outcome = parse_sku(raw)
        assert outcome.status is Status.REJECTED
        assert outcome.reasons == [Reason.MISSING_SKU]
        assert outcome.value is None


class TestParseName:
    def test_non_blank_is_clean(self) -> None:
        outcome = parse_name("Czajnik")
        assert outcome.status is Status.OK
        assert outcome.value == "Czajnik"
        assert outcome.reasons == []

    def test_strips_surrounding_whitespace(self) -> None:
        outcome = parse_name("  Czajnik  ")
        assert outcome.status is Status.OK
        assert outcome.value == "Czajnik"

    @pytest.mark.parametrize("raw", ["", "   ", None])
    def test_blank_or_none_is_rejected_missing_name(self, raw: str | None) -> None:
        outcome = parse_name(raw)
        assert outcome.status is Status.REJECTED
        assert outcome.reasons == [Reason.MISSING_NAME]
        assert outcome.value is None
