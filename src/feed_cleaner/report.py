"""Agregacja liczników jakości danych z listy ClassifiedRow do JSON + skrótu tekstowego."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from feed_cleaner.classify import ClassifiedRow
from feed_cleaner.models import FieldOutcome, Reason, Status

_FIELD_REASON_COUNTED_STATUSES = (Status.REPAIRED, Status.REJECTED)


@dataclass(frozen=True)
class QualityReport:
    row_counts: dict[str, int]
    repaired_reasons: dict[str, int]
    rejected_reasons: dict[str, int]

    def to_dict(self) -> dict[str, dict[str, int]]:
        return {
            "row_counts": self.row_counts,
            "repaired_reasons": self.repaired_reasons,
            "rejected_reasons": self.rejected_reasons,
        }


def _field_outcomes(row: ClassifiedRow) -> tuple[FieldOutcome[Any], ...]:
    return (row.sku, row.name, row.price, row.quantity, row.category)


def build_report(rows: list[ClassifiedRow]) -> QualityReport:
    """Liczniki reasons budowane z PIĘCIU pól ClassifiedRow (nie z płaskiej
    row.reasons), wyłącznie dla pola o statusie zgodnym ze statusem CAŁEGO wiersza —
    reason z pola REPAIRED na wierszu ostatecznie REJECTED (z powodu innego pola)
    nie zadecydował o losie wiersza, więc nie jest liczony nigdzie.

    Wyjątki, które NIE należą do żadnego z pięciu pól, tylko są dopisywane na
    poziomie wiersza (row.reasons) przez późniejsze etapy pipeline'u: DUPLICATE_SKU
    (deduplicate_by_sku) i MALFORMED_ROW (loader, wiersz z pominiętym pipeline'em
    pól). Oba liczone wprost do rejected_reasons, gdy obecne w row.reasons wiersza
    REJECTED — bez tego nigdy nie pojawiłyby się w żadnym liczniku, mimo że realnie
    zdecydowały o odrzuceniu wiersza.
    """
    row_counts = {"total": 0, "ok": 0, "repaired": 0, "rejected": 0}
    repaired_reasons: dict[str, int] = {reason.value: 0 for reason in Reason}
    rejected_reasons: dict[str, int] = {reason.value: 0 for reason in Reason}

    for row in rows:
        row_counts["total"] += 1
        if row.status is Status.CLEAN:
            row_counts["ok"] += 1
            continue

        target = repaired_reasons if row.status is Status.REPAIRED else rejected_reasons
        row_counts["repaired" if row.status is Status.REPAIRED else "rejected"] += 1

        for outcome in _field_outcomes(row):
            if outcome.status is row.status and outcome.status in _FIELD_REASON_COUNTED_STATUSES:
                for reason in outcome.reasons:
                    target[reason.value] += 1

        if row.status is Status.REJECTED:
            for row_level_reason in (Reason.DUPLICATE_SKU, Reason.MALFORMED_ROW):
                if row_level_reason in row.reasons:
                    rejected_reasons[row_level_reason.value] += 1

    return QualityReport(
        row_counts=row_counts,
        repaired_reasons=repaired_reasons,
        rejected_reasons=rejected_reasons,
    )


def write_report(report: QualityReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")


def format_summary(report: QualityReport) -> str:
    counts = report.row_counts
    return (
        f"Total: {counts['total']} | OK: {counts['ok']} | "
        f"Repaired: {counts['repaired']} | Rejected: {counts['rejected']}"
    )
