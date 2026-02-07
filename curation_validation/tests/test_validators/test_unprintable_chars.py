import csv
import json
from pathlib import Path

import pytest

from curation_validation.validators.unprintable_chars import UnprintableCharsValidator
from curation_validation.validators.base import ValidatorContext


def _make_ctx(tmp_path, csv_file=None, json_dir=None):
    return ValidatorContext(
        csv_file=csv_file,
        json_dir=json_dir,
        output_dir=tmp_path / "out",
        data_source=None,
        geonames_user=None,
    )


def _write_json_record(json_dir: Path, record: dict, filename: str = "rec.json"):
    json_dir.mkdir(parents=True, exist_ok=True)
    (json_dir / filename).write_text(json.dumps(record), encoding="utf-8")


def _write_csv(csv_file: Path, rows: list[dict]):
    if not rows:
        csv_file.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class TestUnprintableCharsValidatorMetadata:
    def test_name(self):
        v = UnprintableCharsValidator()
        assert v.name == "unprintable-chars"

    def test_supported_formats(self):
        v = UnprintableCharsValidator()
        assert v.supported_formats == {"csv", "json"}

    def test_output_fields(self):
        v = UnprintableCharsValidator()
        assert "record_id" in v.output_fields
        assert "field" in v.output_fields
        assert "value" in v.output_fields
        assert "unprintable_chars" in v.output_fields

    def test_output_filename(self):
        v = UnprintableCharsValidator()
        assert v.output_filename == "unprintable_chars.csv"


class TestUnprintableCharsJSON:
    def test_detects_null_byte_in_name(self, tmp_path):
        json_dir = tmp_path / "json"
        record = {
            "id": "https://ror.org/001",
            "names": [{"value": "Hello\x00World", "types": ["ror_display"]}],
        }
        _write_json_record(json_dir, record)
        v = UnprintableCharsValidator()
        ctx = _make_ctx(tmp_path, json_dir=json_dir)
        results = v.run(ctx)
        assert len(results) >= 1
        hit = results[0]
        assert hit["record_id"] == "https://ror.org/001"
        assert "Hello\x00World" in hit["value"]
        assert "\\x00" in hit["unprintable_chars"]

    def test_detects_control_char_x01(self, tmp_path):
        json_dir = tmp_path / "json"
        record = {
            "id": "https://ror.org/002",
            "status": "active",
            "names": [{"value": "Test\x01Org", "types": ["ror_display"]}],
        }
        _write_json_record(json_dir, record)
        v = UnprintableCharsValidator()
        ctx = _make_ctx(tmp_path, json_dir=json_dir)
        results = v.run(ctx)
        assert len(results) >= 1
        found_chars = [r["unprintable_chars"] for r in results]
        assert any("\\x01" in c for c in found_chars)

    def test_ignores_clean_printable_values(self, tmp_path):
        json_dir = tmp_path / "json"
        record = {
            "id": "https://ror.org/003",
            "status": "active",
            "names": [{"value": "Clean University", "types": ["ror_display"]}],
            "links": [{"type": "website", "value": "https://example.com"}],
            "types": ["education"],
            "established": 2000,
        }
        _write_json_record(json_dir, record)
        v = UnprintableCharsValidator()
        ctx = _make_ctx(tmp_path, json_dir=json_dir)
        results = v.run(ctx)
        assert results == []

    def test_ignores_non_string_values(self, tmp_path):
        json_dir = tmp_path / "json"
        record = {
            "id": "https://ror.org/004",
            "established": 1999,
            "status": "active",
            "names": [],
        }
        _write_json_record(json_dir, record)
        v = UnprintableCharsValidator()
        ctx = _make_ctx(tmp_path, json_dir=json_dir)
        results = v.run(ctx)
        assert results == []

    def test_ignores_empty_string_values(self, tmp_path):
        json_dir = tmp_path / "json"
        record = {
            "id": "https://ror.org/005",
            "status": "",
            "names": [{"value": "", "types": ["ror_display"]}],
        }
        _write_json_record(json_dir, record)
        v = UnprintableCharsValidator()
        ctx = _make_ctx(tmp_path, json_dir=json_dir)
        results = v.run(ctx)
        assert results == []

    def test_multiple_unprintable_chars_in_one_value(self, tmp_path):
        json_dir = tmp_path / "json"
        record = {
            "id": "https://ror.org/006",
            "names": [{"value": "\x00Test\x01Org\x02", "types": ["ror_display"]}],
        }
        _write_json_record(json_dir, record)
        v = UnprintableCharsValidator()
        ctx = _make_ctx(tmp_path, json_dir=json_dir)
        results = v.run(ctx)
        assert len(results) >= 1
        chars_str = results[0]["unprintable_chars"]
        assert "\\x00" in chars_str
        assert "\\x01" in chars_str
        assert "\\x02" in chars_str

    def test_multiple_records(self, tmp_path):
        json_dir = tmp_path / "json"
        json_dir.mkdir(parents=True, exist_ok=True)
        rec1 = {
            "id": "https://ror.org/010",
            "names": [{"value": "Good Uni", "types": ["ror_display"]}],
        }
        rec2 = {
            "id": "https://ror.org/011",
            "names": [{"value": "Bad\x00Uni", "types": ["ror_display"]}],
        }
        (json_dir / "rec1.json").write_text(json.dumps(rec1), encoding="utf-8")
        (json_dir / "rec2.json").write_text(json.dumps(rec2), encoding="utf-8")
        v = UnprintableCharsValidator()
        ctx = _make_ctx(tmp_path, json_dir=json_dir)
        results = v.run(ctx)
        assert len(results) >= 1
        ids = [r["record_id"] for r in results]
        assert "https://ror.org/011" in ids
        assert "https://ror.org/010" not in ids

    def test_detects_in_nested_fields(self, tmp_path):
        json_dir = tmp_path / "json"
        record = {
            "id": "https://ror.org/007",
            "links": [{"type": "website", "value": "https://bad\x07.com"}],
            "names": [{"value": "Good Name", "types": ["ror_display"]}],
        }
        _write_json_record(json_dir, record)
        v = UnprintableCharsValidator()
        ctx = _make_ctx(tmp_path, json_dir=json_dir)
        results = v.run(ctx)
        assert len(results) >= 1
        assert any("bad" in r["value"] for r in results)


class TestUnprintableCharsCSV:
    def test_detects_unprintable_in_csv(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        _write_csv(csv_file, [
            {
                "id": "https://ror.org/100",
                "names.types.ror_display": "Test\x00Org",
                "status": "active",
            }
        ])
        v = UnprintableCharsValidator()
        ctx = _make_ctx(tmp_path, csv_file=csv_file)
        results = v.run(ctx)
        assert len(results) >= 1
        hit = results[0]
        assert hit["record_id"] == "https://ror.org/100"
        assert "\\x00" in hit["unprintable_chars"]

    def test_csv_clean_values_no_results(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        _write_csv(csv_file, [
            {
                "id": "https://ror.org/101",
                "names.types.ror_display": "Clean University",
                "status": "active",
                "links.type.website": "https://example.com",
            }
        ])
        v = UnprintableCharsValidator()
        ctx = _make_ctx(tmp_path, csv_file=csv_file)
        results = v.run(ctx)
        assert results == []

    def test_csv_empty_values_ignored(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        _write_csv(csv_file, [
            {
                "id": "https://ror.org/102",
                "names.types.ror_display": "",
                "status": "",
            }
        ])
        v = UnprintableCharsValidator()
        ctx = _make_ctx(tmp_path, csv_file=csv_file)
        results = v.run(ctx)
        assert results == []

    def test_csv_multiple_bad_fields(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        _write_csv(csv_file, [
            {
                "id": "https://ror.org/103",
                "names.types.ror_display": "Bad\x00Name",
                "names.types.alias": "Also\x01Bad",
                "status": "active",
            }
        ])
        v = UnprintableCharsValidator()
        ctx = _make_ctx(tmp_path, csv_file=csv_file)
        results = v.run(ctx)
        assert len(results) >= 2
        fields_reported = {r["field"] for r in results}
        assert "names.types.ror_display" in fields_reported
        assert "names.types.alias" in fields_reported

    def test_csv_reports_specific_chars(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        _write_csv(csv_file, [
            {
                "id": "https://ror.org/104",
                "names.types.ror_display": "Org\x1fName",
                "status": "active",
            }
        ])
        v = UnprintableCharsValidator()
        ctx = _make_ctx(tmp_path, csv_file=csv_file)
        results = v.run(ctx)
        assert len(results) == 1
        assert "\\x1f" in results[0]["unprintable_chars"]


class TestUnprintableCharsFormatDetection:
    def test_prefers_json_when_json_dir_set(self, tmp_path):
        json_dir = tmp_path / "json"
        record = {
            "id": "https://ror.org/200",
            "names": [{"value": "Bad\x00Name", "types": ["ror_display"]}],
        }
        _write_json_record(json_dir, record)
        v = UnprintableCharsValidator()
        ctx = _make_ctx(tmp_path, json_dir=json_dir)
        results = v.run(ctx)
        assert len(results) >= 1

    def test_uses_csv_when_csv_file_set(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        _write_csv(csv_file, [
            {
                "id": "https://ror.org/201",
                "names.types.ror_display": "Bad\x00Name",
                "status": "active",
            }
        ])
        v = UnprintableCharsValidator()
        ctx = _make_ctx(tmp_path, csv_file=csv_file)
        results = v.run(ctx)
        assert len(results) >= 1

    def test_returns_empty_when_no_input(self, tmp_path):
        v = UnprintableCharsValidator()
        ctx = _make_ctx(tmp_path)
        results = v.run(ctx)
        assert results == []
