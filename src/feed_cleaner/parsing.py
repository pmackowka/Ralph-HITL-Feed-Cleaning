"""Czyste funkcje parsujące pojedyncze surowe pola feedu (price, quantity)."""

from __future__ import annotations

from typing import NamedTuple

from feed_cleaner.models import FieldOutcome, Reason, Status

_CURRENCY_TOKENS: list[tuple[str, str]] = [
    ("zł", "PLN"),
    ("pln", "PLN"),
    ("$", "USD"),
    ("usd", "USD"),
    ("€", "EUR"),
    ("eur", "EUR"),
]


class PriceValue(NamedTuple):
    price: float
    currency: str | None


def _extract_currency(text: str) -> tuple[str, str | None]:
    """Zdejmuje rozpoznany prefiks/sufiks waluty (case-insensitive) z tekstu."""
    lower = text.lower()
    for token, code in _CURRENCY_TOKENS:
        token_len = len(token)
        if lower.startswith(token):
            return text[token_len:].strip(), code
        if lower.endswith(token):
            return text[: len(text) - token_len].strip(), code
    return text, None


def parse_price(raw: str | None) -> FieldOutcome[PriceValue]:
    if raw is None:
        return FieldOutcome(status=Status.REJECTED, value=None, reasons=[Reason.MISSING_PRICE])

    text = raw.strip()
    if not text:
        return FieldOutcome(status=Status.REJECTED, value=None, reasons=[Reason.MISSING_PRICE])

    rest, currency = _extract_currency(text)
    comma_used = "," in rest
    numeric_text = rest.replace(",", ".") if comma_used else rest

    try:
        parsed = float(numeric_text)
    except ValueError:
        return FieldOutcome(status=Status.REJECTED, value=None, reasons=[Reason.INVALID_PRICE])

    if parsed <= 0:
        return FieldOutcome(status=Status.REJECTED, value=None, reasons=[Reason.INVALID_PRICE])

    if currency is not None or comma_used:
        return FieldOutcome(
            status=Status.REPAIRED,
            value=PriceValue(price=parsed, currency=currency),
            reasons=[Reason.PRICE_FORMAT],
        )

    return FieldOutcome(status=Status.CLEAN, value=PriceValue(price=parsed, currency=None))


def parse_quantity(raw: str | None) -> FieldOutcome[int]:
    if raw is None:
        return FieldOutcome(status=Status.REJECTED, value=None, reasons=[Reason.MISSING_QUANTITY])

    text = raw.strip()
    if not text:
        return FieldOutcome(status=Status.REJECTED, value=None, reasons=[Reason.MISSING_QUANTITY])

    try:
        int_value = int(text)
    except ValueError:
        pass
    else:
        if int_value < 0:
            return FieldOutcome(
                status=Status.REPAIRED, value=abs(int_value), reasons=[Reason.NEGATIVE_QUANTITY]
            )
        return FieldOutcome(status=Status.CLEAN, value=int_value)

    comma_used = "," in text
    numeric_text = text.replace(",", ".") if comma_used else text

    invalid_type = FieldOutcome[int](
        status=Status.REJECTED, value=None, reasons=[Reason.INVALID_QUANTITY_TYPE]
    )

    try:
        parsed = float(numeric_text)
    except ValueError:
        return invalid_type

    if not parsed.is_integer():
        return invalid_type

    int_from_float = int(parsed)
    reasons: list[Reason] = []
    if int_from_float < 0:
        reasons.append(Reason.NEGATIVE_QUANTITY)
    reasons.append(Reason.QUANTITY_FORMAT)

    return FieldOutcome(status=Status.REPAIRED, value=abs(int_from_float), reasons=reasons)
