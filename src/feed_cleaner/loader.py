"""Wczytywanie CSV do listy sklasyfikowanych rekordów, z zachowaniem kolejności pliku."""

from __future__ import annotations

import csv
from pathlib import Path

from feed_cleaner.classify import ClassifiedRow, classify_row, deduplicate_by_sku
from feed_cleaner.models import FieldOutcome, Reason, Status
from feed_cleaner.parsing import PriceValue


def _malformed_row() -> ClassifiedRow:
    """Wiersz ze złą liczbą kolumn względem nagłówka — granice pól są niewiarygodne,
    więc cały pipeline z parsing.py/classify.py jest pomijany na rzecz REJECTED wprost.
    """
    return ClassifiedRow(
        sku=FieldOutcome[str](status=Status.REJECTED, value=None),
        name=FieldOutcome[str](status=Status.REJECTED, value=None),
        price=FieldOutcome[PriceValue](status=Status.REJECTED, value=None),
        quantity=FieldOutcome[int](status=Status.REJECTED, value=None),
        category=FieldOutcome[str | None](status=Status.REJECTED, value=None),
        status=Status.REJECTED,
        reasons=[Reason.MALFORMED_ROW],
    )


def load_feed(path: Path) -> list[ClassifiedRow]:
    """Wczytuje CSV (UTF-8 z obsługą BOM) i klasyfikuje każdy wiersz, zachowując
    kolejność z pliku. Kolumny spoza {sku, name, price, quantity, category} są
    ignorowane. Wiersze ze złą liczbą kolumn nie wywalają całego runu.
    """
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration:
            return []

        column_count = len(header)
        rows: list[ClassifiedRow] = []
        for raw_row in reader:
            if len(raw_row) != column_count:
                rows.append(_malformed_row())
                continue
            record = dict(zip(header, raw_row, strict=True))
            rows.append(classify_row(record))

    return deduplicate_by_sku(rows)
