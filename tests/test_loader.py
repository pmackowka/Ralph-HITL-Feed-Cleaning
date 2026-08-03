from pathlib import Path

from feed_cleaner.loader import load_feed
from feed_cleaner.models import Reason, Status


def _write_csv(tmp_path: Path, content: str, *, encoding: str = "utf-8") -> Path:
    path = tmp_path / "feed.csv"
    path.write_bytes(content.encode(encoding))
    return path


class TestLoadFeed:
    def test_header_only_returns_empty_list(self, tmp_path: Path) -> None:
        path = _write_csv(tmp_path, "sku,name,price,quantity,category\n")
        result = load_feed(path)
        assert result == []

    def test_bom_file_loads_correctly(self, tmp_path: Path) -> None:
        content = "sku,name,price,quantity,category\nA1,Czajnik,29.99,5,AGD\n"
        path = _write_csv(tmp_path, content, encoding="utf-8-sig")
        result = load_feed(path)
        assert len(result) == 1
        assert result[0].status is Status.CLEAN
        assert result[0].sku.value == "A1"

    def test_unknown_extra_column_is_ignored(self, tmp_path: Path) -> None:
        content = (
            "sku,name,price,quantity,category,warehouse\n"
            "A1,Czajnik,29.99,5,AGD,WAW-1\n"
        )
        path = _write_csv(tmp_path, content)
        result = load_feed(path)
        assert len(result) == 1
        assert result[0].status is Status.CLEAN

    def test_row_with_wrong_column_count_is_malformed_rest_loads_normally(
        self, tmp_path: Path
    ) -> None:
        content = (
            "sku,name,price,quantity,category\n"
            "A1,Czajnik,29.99,5\n"
            "A2,Ekspres,49.99,3,AGD\n"
        )
        path = _write_csv(tmp_path, content)
        result = load_feed(path)
        assert len(result) == 2
        assert result[0].status is Status.REJECTED
        assert result[0].reasons == [Reason.MALFORMED_ROW]
        assert result[1].status is Status.CLEAN
        assert result[1].sku.value == "A2"

    def test_row_with_too_many_columns_is_malformed(self, tmp_path: Path) -> None:
        content = (
            "sku,name,price,quantity,category\n"
            "A1,Czajnik,29.99,5,AGD,extra,extra2\n"
        )
        path = _write_csv(tmp_path, content)
        result = load_feed(path)
        assert len(result) == 1
        assert result[0].status is Status.REJECTED
        assert result[0].reasons == [Reason.MALFORMED_ROW]

    def test_input_order_is_preserved(self, tmp_path: Path) -> None:
        content = (
            "sku,name,price,quantity,category\n"
            "A1,Czajnik,29.99,5,AGD\n"
            "B2,Ekspres,49.99,3,AGD\n"
            "C3,Toster,19.99,2,AGD\n"
        )
        path = _write_csv(tmp_path, content)
        result = load_feed(path)
        assert [row.sku.value for row in result] == ["A1", "B2", "C3"]

    def test_dedup_runs_after_malformed_rows(self, tmp_path: Path) -> None:
        content = (
            "sku,name,price,quantity,category\n"
            "A1,Czajnik,29.99,5\n"
            "A1,Ekspres,49.99,3,AGD\n"
        )
        path = _write_csv(tmp_path, content)
        result = load_feed(path)
        assert len(result) == 2
        assert result[0].status is Status.REJECTED
        assert result[0].reasons == [Reason.MALFORMED_ROW]
        assert result[1].status is Status.CLEAN
