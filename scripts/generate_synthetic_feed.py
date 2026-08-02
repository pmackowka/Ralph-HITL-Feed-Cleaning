"""Deterministyczny generator syntetycznego, celowo brudnego feedu produktowego.

Nie jest częścią pętli Ralpha (PRD.json) — uruchamiany raz, ręcznie, przed
startem pętli. Każdy wiersz ma z góry znaną, jawnie przypisaną klasyfikację
(ok/repaired/rejected + reasons), dzięki czemu manifest.json jest twardym
punktem odniesienia do ręcznej weryfikacji report.json wygenerowanego przez CLI.

Plik wyjściowy jest zapisywany z BOM (utf-8-sig) celowo — to częsty artefakt
eksportów z Excela, więc od razu testuje obsługę BOM w loaderze.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

OUTPUT_CSV = Path(__file__).resolve().parent.parent / "data" / "raw" / "feed.csv"
MANIFEST_JSON = Path(__file__).resolve().parent.parent / "data" / "raw" / "feed_manifest.json"

FIELDNAMES = ["sku", "name", "price", "quantity", "category"]

# Musi być zgodne z listą reason w PRD.json (zadanie 6), włącznie z tymi,
# które ten generator celowo NIE wstrzykuje (malformed_row) — raport ma je
# pokazywać z count=0, nie pomijać.
ALL_REASONS = [
    "price_format",
    "negative_quantity",
    "quantity_format",
    "missing_sku",
    "missing_name",
    "missing_price",
    "missing_quantity",
    "invalid_price",
    "invalid_quantity_type",
    "duplicate_sku",
    "malformed_row",
]


@dataclass
class Row:
    fields: dict[str, str]
    status: str
    reasons: list[str] = field(default_factory=list)


def clean(sku: str, name: str, price: str, quantity: str, category: str) -> Row:
    return Row({"sku": sku, "name": name, "price": price, "quantity": quantity, "category": category}, "ok")


def repaired(sku: str, name: str, price: str, quantity: str, category: str, reasons: list[str]) -> Row:
    return Row(
        {"sku": sku, "name": name, "price": price, "quantity": quantity, "category": category},
        "repaired",
        reasons,
    )


def rejected(sku: str, name: str, price: str, quantity: str, category: str, reasons: list[str]) -> Row:
    return Row(
        {"sku": sku, "name": name, "price": price, "quantity": quantity, "category": category},
        "rejected",
        reasons,
    )


def build_rows() -> list[Row]:
    rows: list[Row] = []

    # --- 10 czystych rekordów bazowych (OK) ---
    baseline = [
        ("B001", "Czajnik elektryczny 1.7L", "89.99", "12", "AGD"),
        ("B002", "Słuchawki bezprzewodowe", "199.00", "30", "Elektronika"),
        ("B003", "Poduszka dekoracyjna", "39.90", "50", "Dom"),
        ("B004", "Kubek termiczny 400ml", "24.50", "100", "Dom"),
        ("B005", "Lampka biurkowa LED", "59.99", "20", "Elektronika"),
        ("B006", "Ręcznik kąpielowy XL", "34.00", "75", "Dom"),
        ("B007", "Router WiFi AX3000", "249.99", "8", "Elektronika"),
        ("B008", "Zestaw garnków 5 elementów", "329.00", "5", "AGD"),
        ("B009", "Organizer na biurko", "19.99", "60", "Biuro"),
        ("B010", "Głośnik Bluetooth mini", "99.00", "40", "Elektronika"),
    ]
    for sku, name, price, qty, cat in baseline:
        rows.append(clean(sku, name, price, qty, cat))

    # --- 6 błędów formatu ceny (REPAIRED: price_format) ---
    price_format_cases = [
        ("P001", "Deska do krojenia", "29,99 zł", "15", "Kuchnia"),
        ("P002", "Nóż szefa kuchni", "19.99 zł", "22", "Kuchnia"),
        ("P003", "Otwieracz do konserw", "12,50", "45", "Kuchnia"),
        ("P004", "Zestaw kubków 6 szt", "$45.00", "18", "Kuchnia"),
        ("P005", "Patelnia ceramiczna 28cm", "45.00 USD", "10", "Kuchnia"),
        ("P006", "Termos stalowy 1L", "99,90 €", "16", "Kuchnia"),
    ]
    for sku, name, price, qty, cat in price_format_cases:
        rows.append(repaired(sku, name, price, qty, cat, ["price_format"]))

    # --- 3 ujemne ilości (REPAIRED: negative_quantity) ---
    negative_qty_cases = [
        ("N001", "Zeszyt A5 w kratkę", "9.99", "-5", "Biuro"),
        ("N002", "Długopis żelowy", "3.50", "-12", "Biuro"),
        ("N003", "Segregator A4", "14.90", "-1", "Biuro"),
    ]
    for sku, name, price, qty, cat in negative_qty_cases:
        rows.append(repaired(sku, name, price, qty, cat, ["negative_quantity"]))

    # --- 3 błędy formatu ilości (REPAIRED: quantity_format), jeden łączony z negative_quantity ---
    rows.append(repaired("F001", "Karteczki samoprzylepne", "4.99", "10.0", "Biuro", ["quantity_format"]))
    rows.append(repaired("F002", "Zakreślacz zestaw 4 kolory", "11.00", "10,0", "Biuro", ["quantity_format"]))
    rows.append(
        repaired("F003", "Spinacze biurowe 100 szt", "6.50", "-10.0", "Biuro", ["negative_quantity", "quantity_format"])
    )

    # --- 4 braki wymaganych pól (REJECTED) ---
    rows.append(rejected("", "Produkt bez SKU", "29.99", "10", "Dom", ["missing_sku"]))
    rows.append(rejected("M002", "", "19.99", "5", "Dom", ["missing_name"]))
    rows.append(rejected("M003", "Świecznik szklany", "", "8", "Dom", ["missing_price"]))
    rows.append(rejected("M004", "Wazon ceramiczny", "45.00", "", "Dom", ["missing_quantity"]))

    # --- 5 złych typów / nieprawidłowych wartości (REJECTED) ---
    rows.append(rejected("W001", "Miska dla psa", "15.00", "dziesięć", "Zwierzęta", ["invalid_quantity_type"]))
    rows.append(rejected("W002", "Smycz regulowana", "22.00", "10.5", "Zwierzęta", ["invalid_quantity_type"]))
    rows.append(rejected("W003", "Karma sucha 5kg", "abc", "20", "Zwierzęta", ["invalid_price"]))
    rows.append(rejected("W004", "Zabawka dla kota", "-10", "30", "Zwierzęta", ["invalid_price"]))
    rows.append(rejected("W005", "Kuweta narożna", "0", "12", "Zwierzęta", ["invalid_price"]))

    # --- 5 wierszy na duplikaty SKU (grupa 2x i grupa 3x wystąpienie) ---
    rows.append(clean("DUP001", "Plecak miejski 20L", "129.00", "14", "Bagaż"))
    rows.append(rejected("DUP001", "Plecak miejski 20L", "129.00", "14", "Bagaż", ["duplicate_sku"]))
    rows.append(clean("DUP002", "Walizka kabinowa", "349.00", "6", "Bagaż"))
    rows.append(rejected("DUP002", "Walizka kabinowa", "349.00", "6", "Bagaż", ["duplicate_sku"]))
    rows.append(rejected("DUP002", "Walizka kabinowa", "349.00", "6", "Bagaż", ["duplicate_sku"]))

    return rows


def build_manifest(rows: list[Row]) -> dict[str, object]:
    row_counts = {"total": len(rows), "ok": 0, "repaired": 0, "rejected": 0}
    repaired_reasons = {reason: 0 for reason in ALL_REASONS}
    rejected_reasons = {reason: 0 for reason in ALL_REASONS}

    for row in rows:
        row_counts[row.status] += 1
        if row.status == "repaired":
            for reason in row.reasons:
                repaired_reasons[reason] += 1
        elif row.status == "rejected":
            for reason in row.reasons:
                rejected_reasons[reason] += 1

    return {
        "row_counts": row_counts,
        "repaired_reasons": repaired_reasons,
        "rejected_reasons": rejected_reasons,
    }


def main() -> None:
    rows = build_rows()
    manifest = build_manifest(rows)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.fields)

    MANIFEST_JSON.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Zapisano {len(rows)} wierszy do {OUTPUT_CSV}")
    print(f"Manifest zapisany do {MANIFEST_JSON}:")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
