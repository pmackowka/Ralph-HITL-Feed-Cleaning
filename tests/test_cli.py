from __future__ import annotations

import json
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from feed_cleaner.cli import main


def _write_csv(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "feed.csv"
    path.write_text(content, encoding="utf-8")
    return path


class TestCli:
    def test_nonexistent_input_prints_readable_error_and_nonzero_exit(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        missing = tmp_path / "missing.csv"
        output_dir = tmp_path / "out"

        exit_code = main(["--input", str(missing), "--output-dir", str(output_dir)])

        assert exit_code != 0
        captured = capsys.readouterr()
        assert "Traceback" not in captured.err
        assert str(missing) in captured.err

    def test_non_utf8_input_prints_readable_error_and_nonzero_exit(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        input_path = tmp_path / "latin1.csv"
        input_path.write_bytes(
            b"sku,name,price,quantity,category\nA1,Caf\xe9,29.99,5,AGD\n"
        )
        output_dir = tmp_path / "out"

        exit_code = main(["--input", str(input_path), "--output-dir", str(output_dir)])

        assert exit_code != 0
        captured = capsys.readouterr()
        assert "Traceback" not in captured.err
        assert "UTF-8" in captured.err
        assert str(input_path) in captured.err

    def test_missing_output_dir_is_created_automatically(self, tmp_path: Path) -> None:
        input_path = _write_csv(
            tmp_path, "sku,name,price,quantity,category\nA1,Czajnik,29.99,5,AGD\n"
        )
        output_dir = tmp_path / "nested" / "out"

        exit_code = main(["--input", str(input_path), "--output-dir", str(output_dir)])

        assert exit_code == 0
        assert (output_dir / "clean.parquet").exists()
        assert (output_dir / "report.json").exists()

    def test_empty_input_file_succeeds_with_empty_outputs(self, tmp_path: Path) -> None:
        input_path = _write_csv(tmp_path, "sku,name,price,quantity,category\n")
        output_dir = tmp_path / "out"

        exit_code = main(["--input", str(input_path), "--output-dir", str(output_dir)])

        assert exit_code == 0
        table = pq.read_table(output_dir / "clean.parquet")
        assert table.num_rows == 0
        report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
        assert report["row_counts"]["total"] == 0

    def test_success_with_some_rejected_records_exits_zero(self, tmp_path: Path) -> None:
        content = (
            "sku,name,price,quantity,category\n"
            "A1,Czajnik,29.99,5,AGD\n"
            ",Ekspres,49.99,3,AGD\n"
        )
        input_path = _write_csv(tmp_path, content)
        output_dir = tmp_path / "out"

        exit_code = main(["--input", str(input_path), "--output-dir", str(output_dir)])

        assert exit_code == 0
        report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
        assert report["row_counts"]["rejected"] == 1
        assert report["row_counts"]["ok"] == 1

    def test_end_to_end_creates_both_output_files(self, tmp_path: Path) -> None:
        input_path = _write_csv(
            tmp_path, "sku,name,price,quantity,category\nA1,Czajnik,29.99,5,AGD\n"
        )
        output_dir = tmp_path / "out"

        exit_code = main(["--input", str(input_path), "--output-dir", str(output_dir)])

        assert exit_code == 0
        assert (output_dir / "clean.parquet").exists()
        assert (output_dir / "report.json").exists()
