import json
from pathlib import Path
import pytest
from validate_ror_records_input_csvs.core.loader import DataSource, DataLoader
from validate_ror_records_input_csvs.core.exceptions import DataLoadError


FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestDataSource:
    def test_from_json_file(self):
        ds = DataSource.from_file(FIXTURES_DIR / "sample_dump.json")
        assert len(ds) == 2

    def test_get_record_exists(self):
        ds = DataSource.from_file(FIXTURES_DIR / "sample_dump.json")
        record = ds.get_record("https://ror.org/012345")
        assert record is not None
        assert record["id"] == "https://ror.org/012345"

    def test_get_record_not_exists(self):
        ds = DataSource.from_file(FIXTURES_DIR / "sample_dump.json")
        record = ds.get_record("https://ror.org/999999")
        assert record is None

    def test_id_exists_true(self):
        ds = DataSource.from_file(FIXTURES_DIR / "sample_dump.json")
        assert ds.id_exists("https://ror.org/012345") is True

    def test_id_exists_false(self):
        ds = DataSource.from_file(FIXTURES_DIR / "sample_dump.json")
        assert ds.id_exists("https://ror.org/999999") is False

    def test_get_all_ids(self):
        ds = DataSource.from_file(FIXTURES_DIR / "sample_dump.json")
        ids = ds.get_all_ids()
        assert len(ids) == 2
        assert "https://ror.org/012345" in ids

    def test_get_all_records(self):
        ds = DataSource.from_file(FIXTURES_DIR / "sample_dump.json")
        records = ds.get_all_records()
        assert len(records) == 2

    def test_find_related_records(self):
        ds = DataSource.from_file(FIXTURES_DIR / "sample_dump.json")
        related = ds.find_related_records("https://ror.org/012345")
        assert len(related) == 1
        assert related[0]["id"] == "https://ror.org/067890"

    def test_file_not_found(self):
        with pytest.raises(DataLoadError):
            DataSource.from_file(FIXTURES_DIR / "nonexistent.json")


class TestDataLoader:
    def test_load_from_file(self):
        loader = DataLoader(str(FIXTURES_DIR / "sample_dump.json"))
        ds = loader.load()
        assert len(ds) == 2

    def test_load_from_file_path_object(self):
        loader = DataLoader(FIXTURES_DIR / "sample_dump.json")
        ds = loader.load()
        assert len(ds) == 2
