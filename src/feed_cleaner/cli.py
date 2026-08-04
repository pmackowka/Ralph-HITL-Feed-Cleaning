"""Argparse entry point: spina loader -> classify -> export -> report."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from feed_cleaner.export import export_to_parquet
from feed_cleaner.loader import load_feed
from feed_cleaner.report import build_report, format_summary, write_report

EXIT_OK = 0
EXIT_USAGE_ERROR = 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="feed-cleaner")
    parser.add_argument("--input", required=True, type=Path, help="Ścieżka do pliku CSV")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Katalog wyjściowy (domyślnie 'output/')",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    input_path: Path = args.input
    output_dir: Path = args.output_dir

    if not input_path.is_file():
        print(f"Błąd: plik wejściowy nie istnieje: {input_path}", file=sys.stderr)
        return EXIT_USAGE_ERROR

    try:
        rows = load_feed(input_path)
    except UnicodeDecodeError:
        print(
            f"Błąd: plik wejściowy nie jest w kodowaniu UTF-8: {input_path}",
            file=sys.stderr,
        )
        return EXIT_USAGE_ERROR

    export_to_parquet(rows, output_dir / "clean.parquet")
    report = build_report(rows)
    write_report(report, output_dir / "report.json")

    print(format_summary(report))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
