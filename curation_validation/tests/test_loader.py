import json
from pathlib import Path

import pytest

from curation_validation.core.loader import DataSource, DataLoader
from curation_validation.core.exceptions import DataLoadError


class TestDataSource:
    def test_from_json_file(self, tmp_path):
        data = [
            {"id": "https://ror.org/012345", "names": [{"value": "Test", "types": ["ror_display"]}]},
            {"id": "https://ror.org/067890", "names": [{"value": "Other", "types": ["ror_display"]}]},
        ]
        file_path = tmp_path / "dump.json"
        file_path.write_text(json.dumps(data))
        ds = DataSource.from_file(file_path)
        assert len(ds) == 2

    def test_get_record(self, tmp_path):
        data = [{"id": "https://ror.org/012345"}]
        file_path = tmp_path / "dump.json"
        file_path.write_text(json.dumps(data))
        ds = DataSource.from_file(file_path)
        assert ds.get_record("https://ror.org/012345") is not None
        assert ds.get_record("https://ror.org/999999") is None

    def test_id_exists(self, tmp_path):
        data = [{"id": "https://ror.org/012345"}]
        file_path = tmp_path / "dump.json"
        file_path.write_text(json.dumps(data))
        ds = DataSource.from_file(file_path)
        assert ds.id_exists("https://ror.org/012345")
        assert not ds.id_exists("https://ror.org/999999")

    def test_get_all_ids(self, tmp_path):
        data = [{"id": "https://ror.org/012345"}, {"id": "https://ror.org/067890"}]
        file_path = tmp_path / "dump.json"
        file_path.write_text(json.dumps(data))
        ds = DataSource.from_file(file_path)
        assert len(ds.get_all_ids()) == 2

    def test_get_all_records(self, tmp_path):
        data = [{"id": "https://ror.org/012345"}]
        file_path = tmp_path / "dump.json"
        file_path.write_text(json.dumps(data))
        ds = DataSource.from_file(file_path)
        assert len(ds.get_all_records()) == 1

    def test_find_related_records(self, tmp_path):
        data = [
            {"id": "https://ror.org/012345", "relationships": []},
            {"id": "https://ror.org/067890", "relationships": [{"id": "https://ror.org/012345", "type": "related"}]},
        ]
        file_path = tmp_path / "dump.json"
        file_path.write_text(json.dumps(data))
        ds = DataSource.from_file(file_path)
        related = ds.find_related_records("https://ror.org/012345")
        assert len(related) == 1

    def test_file_not_found(self, tmp_path):
        with pytest.raises(DataLoadError):
            DataSource.from_file(tmp_path / "missing.json")


class TestDataLoader:
    def test_loads_from_file(self, tmp_path):
        data = [{"id": "https://ror.org/012345"}]
        file_path = tmp_path / "dump.json"
        file_path.write_text(json.dumps(data))
        loader = DataLoader(file_path)
        ds = loader.load()
        assert len(ds) == 1
