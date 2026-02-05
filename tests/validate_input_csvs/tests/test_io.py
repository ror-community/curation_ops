import csv
from pathlib import Path
import pytest
from validate_ror_records_input_csvs.core.io import read_csv, write_csv, detect_file_type


FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestReadCsv:
    def test_read_simple_csv(self):
        records = read_csv(FIXTURES_DIR / "simple.csv")
        assert len(records) == 2
        assert records[0]["name"] == "Test Org"
        assert records[1]["status"] == "inactive"

    def test_read_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            read_csv(FIXTURES_DIR / "nonexistent.csv")


class TestWriteCsv:
    def test_write_csv(self, tmp_path):
        output_path = tmp_path / "output.csv"
        data = [
            {"id": "1", "name": "Test", "error": "Invalid"},
            {"id": "2", "name": "Test2", "error": "Missing"},
        ]
        write_csv(data, output_path, ["id", "name", "error"])

        # Read back and verify
        with open(output_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2
        assert rows[0]["id"] == "1"
        assert rows[1]["error"] == "Missing"


class TestDetectFileType:
    def test_new_records_empty_id(self):
        records = [{"id": "", "name": "Test"}]
        assert detect_file_type(records) == "new"

    def test_new_records_missing_id(self):
        records = [{"name": "Test"}]
        assert detect_file_type(records) == "new"

    def test_updates_populated_id(self):
        records = [{"id": "https://ror.org/012345", "name": "Test"}]
        assert detect_file_type(records) == "updates"

    def test_mixed_defaults_to_updates(self):
        records = [
            {"id": "", "name": "Test1"},
            {"id": "https://ror.org/012345", "name": "Test2"},
        ]
        assert detect_file_type(records) == "updates"
