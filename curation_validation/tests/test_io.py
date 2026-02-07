import json
from pathlib import Path

import pytest

from curation_validation.core.io import read_csv, write_csv, read_json_dir, detect_file_type


class TestReadCsv:
    def test_reads_simple_csv(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("name,status\nTest Org,active\n")
        records = read_csv(csv_file)
        assert len(records) == 1
        assert records[0]["name"] == "Test Org"

    def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            read_csv(tmp_path / "missing.csv")


class TestWriteCsv:
    def test_writes_csv(self, tmp_path):
        output = tmp_path / "output.csv"
        data = [{"name": "Test", "value": "123"}]
        write_csv(data, output, ["name", "value"])
        content = output.read_text()
        assert "name,value" in content
        assert "Test,123" in content

    def test_creates_parent_dirs(self, tmp_path):
        output = tmp_path / "sub" / "dir" / "output.csv"
        write_csv([], output, ["a"])
        assert output.exists()


class TestReadJsonDir:
    def test_reads_json_files(self, tmp_path):
        record = {"id": "https://ror.org/012345", "status": "active"}
        (tmp_path / "012345.json").write_text(json.dumps(record))
        records = read_json_dir(tmp_path)
        assert len(records) == 1
        assert records[0]["id"] == "https://ror.org/012345"

    def test_reads_multiple_sorted(self, tmp_path):
        (tmp_path / "aaa.json").write_text(json.dumps({"id": "a"}))
        (tmp_path / "bbb.json").write_text(json.dumps({"id": "b"}))
        records = read_json_dir(tmp_path)
        assert len(records) == 2
        assert records[0]["id"] == "a"

    def test_ignores_non_json(self, tmp_path):
        (tmp_path / "readme.txt").write_text("not json")
        (tmp_path / "test.json").write_text(json.dumps({"id": "x"}))
        records = read_json_dir(tmp_path)
        assert len(records) == 1

    def test_empty_dir(self, tmp_path):
        records = read_json_dir(tmp_path)
        assert records == []

    def test_dir_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            read_json_dir(tmp_path / "missing")


class TestDetectFileType:
    def test_detects_updates(self):
        records = [{"id": "https://ror.org/012345", "status": "active"}]
        assert detect_file_type(records) == "updates"

    def test_detects_new(self):
        records = [{"id": "", "status": "active"}]
        assert detect_file_type(records) == "new"

    def test_detects_new_no_id(self):
        records = [{"status": "active"}]
        assert detect_file_type(records) == "new"
