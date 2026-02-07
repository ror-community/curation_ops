import csv
import json
from pathlib import Path

import pytest

from curation_validation.validators.base import ValidatorContext
from curation_validation.core.loader import DataSource
from curation_validation.validators.duplicate_urls import (
    DuplicateUrlsValidator,
    get_ror_display_name,
    get_website_url,
    preprocess_data_source,
)


def _make_data_source(records: list[dict]) -> DataSource:
    return DataSource(records)


def _make_json_ctx(tmp_path, records, data_source=None):
    json_dir = tmp_path / "json"
    json_dir.mkdir(parents=True, exist_ok=True)
    for i, record in enumerate(records):
        ror_id = record.get("id") or f"https://ror.org/0{i:08d}"
        filename = ror_id.rsplit("/", 1)[-1] + ".json"
        (json_dir / filename).write_text(json.dumps(record), encoding="utf-8")
    return ValidatorContext(
        csv_file=None,
        json_dir=json_dir,
        output_dir=tmp_path / "output",
        data_source=data_source,
        geonames_user=None,
    )


def _make_csv_ctx(tmp_path, rows, data_source=None):
    csv_file = tmp_path / "input.csv"
    if not rows:
        csv_file.write_text("", encoding="utf-8")
    else:
        fieldnames = list(rows[0].keys())
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    return ValidatorContext(
        csv_file=csv_file,
        json_dir=None,
        output_dir=tmp_path / "output",
        data_source=data_source,
        geonames_user=None,
    )


def _dump_record(ror_id, display_name, website_url):
    return {
        "id": ror_id,
        "names": [{"value": display_name, "types": ["ror_display"]}],
        "links": [{"type": "website", "value": website_url}],
    }


class TestDuplicateUrlsValidatorMetadata:
    def test_name(self):
        v = DuplicateUrlsValidator()
        assert v.name == "duplicate-urls"

    def test_supported_formats(self):
        v = DuplicateUrlsValidator()
        assert v.supported_formats == {"csv", "json"}

    def test_requires_data_source(self):
        v = DuplicateUrlsValidator()
        assert v.requires_data_source is True

    def test_output_filename(self):
        v = DuplicateUrlsValidator()
        assert v.output_filename == "duplicate_urls.csv"

    def test_output_fields(self):
        v = DuplicateUrlsValidator()
        expected = [
            "ror_display_name",
            "ror_id",
            "data_dump_id",
            "data_dump_ror_display_name",
            "csv_url",
            "data_dump_url",
        ]
        assert v.output_fields == expected

    def test_can_run_without_data_source(self, tmp_path):
        v = DuplicateUrlsValidator()
        ctx = ValidatorContext(
            csv_file=None,
            json_dir=None,
            output_dir=tmp_path,
            data_source=None,
            geonames_user=None,
        )
        can, msg = v.can_run(ctx)
        assert can is False
        assert "data" in msg.lower() or "dump" in msg.lower()

    def test_can_run_with_data_source(self, tmp_path):
        ds = _make_data_source([])
        ctx = ValidatorContext(
            csv_file=None,
            json_dir=None,
            output_dir=tmp_path,
            data_source=ds,
            geonames_user=None,
        )
        v = DuplicateUrlsValidator()
        can, _ = v.can_run(ctx)
        assert can is True


class TestGetRorDisplayName:
    def test_returns_display_name(self):
        record = {
            "names": [
                {"value": "Alias Name", "types": ["alias"]},
                {"value": "Main Name", "types": ["ror_display"]},
            ]
        }
        assert get_ror_display_name(record) == "Main Name"

    def test_returns_empty_when_no_ror_display(self):
        record = {"names": [{"value": "Alias", "types": ["alias"]}]}
        assert get_ror_display_name(record) == ""

    def test_returns_empty_when_no_names(self):
        record = {"names": []}
        assert get_ror_display_name(record) == ""

    def test_returns_empty_when_names_key_missing(self):
        record = {}
        assert get_ror_display_name(record) == ""


class TestGetWebsiteUrl:
    def test_returns_website_url(self):
        record = {
            "links": [
                {"type": "wikipedia", "value": "https://en.wikipedia.org/wiki/Foo"},
                {"type": "website", "value": "https://example.com"},
            ]
        }
        assert get_website_url(record) == "https://example.com"

    def test_returns_none_when_no_website(self):
        record = {
            "links": [
                {"type": "wikipedia", "value": "https://en.wikipedia.org/wiki/Foo"},
            ]
        }
        assert get_website_url(record) is None

    def test_returns_none_when_no_links(self):
        record = {"links": []}
        assert get_website_url(record) is None

    def test_returns_none_when_links_key_missing(self):
        record = {}
        assert get_website_url(record) is None


class TestPreprocessDataSource:
    def test_builds_url_dict(self):
        records = [
            _dump_record("https://ror.org/001", "University A", "https://unia.edu"),
        ]
        url_dict = preprocess_data_source(records)
        assert len(url_dict) > 0
        found = any("unia.edu" in k for k in url_dict)
        assert found

    def test_adds_www_variant(self):
        records = [
            _dump_record("https://ror.org/001", "University A", "https://unia.edu"),
        ]
        url_dict = preprocess_data_source(records)
        assert any("www.unia.edu" in k for k in url_dict)

    def test_skips_records_without_website(self):
        records = [
            {
                "id": "https://ror.org/001",
                "names": [{"value": "No Website Org", "types": ["ror_display"]}],
                "links": [{"type": "wikipedia", "value": "https://en.wikipedia.org/wiki/Foo"}],
            }
        ]
        url_dict = preprocess_data_source(records)
        assert len(url_dict) == 0

    def test_skips_empty_website(self):
        records = [
            {
                "id": "https://ror.org/001",
                "names": [{"value": "Empty URL Org", "types": ["ror_display"]}],
                "links": [{"type": "website", "value": ""}],
            }
        ]
        url_dict = preprocess_data_source(records)
        assert len(url_dict) == 0

    def test_stores_record_info(self):
        records = [
            _dump_record("https://ror.org/001", "University A", "https://unia.edu"),
        ]
        url_dict = preprocess_data_source(records)
        info = None
        for k, v in url_dict.items():
            if "unia.edu" in k:
                info = v
                break
        assert info is not None
        assert info["ror_id"] == "https://ror.org/001"
        assert info["ror_display_name"] == "University A"
        assert info["original_url"] == "https://unia.edu"


class TestDuplicateUrlsJSON:
    def test_exact_url_match(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", "https://example.com"),
        ]
        ds = _make_data_source(dump_records)
        input_records = [
            {
                "id": "",
                "names": [{"value": "New Org", "types": ["ror_display"]}],
                "links": [{"type": "website", "value": "https://example.com"}],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateUrlsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["ror_display_name"] == "New Org"
        assert results[0]["data_dump_id"] == "https://ror.org/dump001"
        assert results[0]["data_dump_ror_display_name"] == "Dump Org"

    def test_normalized_www_match(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", "https://example.com"),
        ]
        ds = _make_data_source(dump_records)
        input_records = [
            {
                "id": "",
                "names": [{"value": "New Org", "types": ["ror_display"]}],
                "links": [{"type": "website", "value": "https://www.example.com"}],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateUrlsValidator()
        results = v.run(ctx)
        assert len(results) == 1

    def test_normalized_scheme_match(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", "https://example.com"),
        ]
        ds = _make_data_source(dump_records)
        input_records = [
            {
                "id": "",
                "names": [{"value": "New Org", "types": ["ror_display"]}],
                "links": [{"type": "website", "value": "http://example.com"}],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateUrlsValidator()
        results = v.run(ctx)
        assert len(results) == 1

    def test_normalized_case_match(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", "https://Example.COM"),
        ]
        ds = _make_data_source(dump_records)
        input_records = [
            {
                "id": "",
                "names": [{"value": "New Org", "types": ["ror_display"]}],
                "links": [{"type": "website", "value": "https://example.com"}],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateUrlsValidator()
        results = v.run(ctx)
        assert len(results) == 1

    def test_no_match_different_domains(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", "https://example.com"),
        ]
        ds = _make_data_source(dump_records)
        input_records = [
            {
                "id": "",
                "names": [{"value": "New Org", "types": ["ror_display"]}],
                "links": [{"type": "website", "value": "https://different.org"}],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateUrlsValidator()
        results = v.run(ctx)
        assert len(results) == 0

    def test_no_website_link_in_input(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", "https://example.com"),
        ]
        ds = _make_data_source(dump_records)
        input_records = [
            {
                "id": "",
                "names": [{"value": "No Website Org", "types": ["ror_display"]}],
                "links": [{"type": "wikipedia", "value": "https://en.wikipedia.org/wiki/Foo"}],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateUrlsValidator()
        results = v.run(ctx)
        assert len(results) == 0

    def test_multiple_input_records(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", "https://example.com"),
        ]
        ds = _make_data_source(dump_records)
        input_records = [
            {
                "id": "",
                "names": [{"value": "Match Org", "types": ["ror_display"]}],
                "links": [{"type": "website", "value": "https://example.com"}],
            },
            {
                "id": "",
                "names": [{"value": "No Match Org", "types": ["ror_display"]}],
                "links": [{"type": "website", "value": "https://unique.org"}],
            },
        ]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateUrlsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["ror_display_name"] == "Match Org"

    def test_output_format_fields(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", "https://example.com"),
        ]
        ds = _make_data_source(dump_records)
        input_records = [
            {
                "id": "https://ror.org/input001",
                "names": [{"value": "New Org", "types": ["ror_display"]}],
                "links": [{"type": "website", "value": "https://example.com"}],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateUrlsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        result = results[0]
        assert "ror_display_name" in result
        assert "ror_id" in result
        assert "data_dump_id" in result
        assert "data_dump_ror_display_name" in result
        assert "csv_url" in result
        assert "data_dump_url" in result

    def test_preserves_original_urls(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", "https://www.Example.COM/path"),
        ]
        ds = _make_data_source(dump_records)
        input_records = [
            {
                "id": "",
                "names": [{"value": "New Org", "types": ["ror_display"]}],
                "links": [{"type": "website", "value": "http://example.com"}],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateUrlsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["csv_url"] == "http://example.com"
        assert results[0]["data_dump_url"] == "https://www.Example.COM/path"

    def test_empty_json_dir(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", "https://example.com"),
        ]
        ds = _make_data_source(dump_records)
        json_dir = tmp_path / "json"
        json_dir.mkdir(parents=True, exist_ok=True)
        ctx = ValidatorContext(
            csv_file=None,
            json_dir=json_dir,
            output_dir=tmp_path / "output",
            data_source=ds,
            geonames_user=None,
        )
        v = DuplicateUrlsValidator()
        results = v.run(ctx)
        assert results == []

    def test_record_with_id_populated(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", "https://example.com"),
        ]
        ds = _make_data_source(dump_records)
        input_records = [
            {
                "id": "https://ror.org/myrecord",
                "names": [{"value": "My Org", "types": ["ror_display"]}],
                "links": [{"type": "website", "value": "https://example.com"}],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateUrlsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["ror_id"] == "https://ror.org/myrecord"

    def test_www_variant_match(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", "https://example.com"),
        ]
        ds = _make_data_source(dump_records)
        input_records = [
            {
                "id": "",
                "names": [{"value": "New Org", "types": ["ror_display"]}],
                "links": [{"type": "website", "value": "https://www.example.com"}],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateUrlsValidator()
        results = v.run(ctx)
        assert len(results) == 1


class TestDuplicateUrlsCSV:
    def test_exact_url_match_csv(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", "https://example.com"),
        ]
        ds = _make_data_source(dump_records)
        rows = [
            {
                "id": "",
                "names.types.ror_display": "New Org",
                "links.type.website": "https://example.com",
            }
        ]
        ctx = _make_csv_ctx(tmp_path, rows, data_source=ds)
        v = DuplicateUrlsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["ror_display_name"] == "New Org"
        assert results[0]["data_dump_id"] == "https://ror.org/dump001"

    def test_normalized_www_match_csv(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", "https://example.com"),
        ]
        ds = _make_data_source(dump_records)
        rows = [
            {
                "id": "",
                "names.types.ror_display": "New Org",
                "links.type.website": "https://www.example.com",
            }
        ]
        ctx = _make_csv_ctx(tmp_path, rows, data_source=ds)
        v = DuplicateUrlsValidator()
        results = v.run(ctx)
        assert len(results) == 1

    def test_no_match_different_domains_csv(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", "https://example.com"),
        ]
        ds = _make_data_source(dump_records)
        rows = [
            {
                "id": "",
                "names.types.ror_display": "Other Org",
                "links.type.website": "https://different.org",
            }
        ]
        ctx = _make_csv_ctx(tmp_path, rows, data_source=ds)
        v = DuplicateUrlsValidator()
        results = v.run(ctx)
        assert len(results) == 0

    def test_csv_no_website_column(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", "https://example.com"),
        ]
        ds = _make_data_source(dump_records)
        rows = [
            {
                "id": "",
                "names.types.ror_display": "No Link Org",
                "links.type.website": "",
            }
        ]
        ctx = _make_csv_ctx(tmp_path, rows, data_source=ds)
        v = DuplicateUrlsValidator()
        results = v.run(ctx)
        assert len(results) == 0

    def test_csv_output_fields(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", "https://example.com"),
        ]
        ds = _make_data_source(dump_records)
        rows = [
            {
                "id": "https://ror.org/input001",
                "names.types.ror_display": "New Org",
                "links.type.website": "https://example.com",
            }
        ]
        ctx = _make_csv_ctx(tmp_path, rows, data_source=ds)
        v = DuplicateUrlsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        result = results[0]
        assert result["ror_display_name"] == "New Org"
        assert result["ror_id"] == "https://ror.org/input001"
        assert result["data_dump_id"] == "https://ror.org/dump001"
        assert result["data_dump_ror_display_name"] == "Dump Org"
        assert result["csv_url"] == "https://example.com"
        assert result["data_dump_url"] == "https://example.com"

    def test_csv_scheme_normalization(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", "https://example.com"),
        ]
        ds = _make_data_source(dump_records)
        rows = [
            {
                "id": "",
                "names.types.ror_display": "New Org",
                "links.type.website": "http://example.com",
            }
        ]
        ctx = _make_csv_ctx(tmp_path, rows, data_source=ds)
        v = DuplicateUrlsValidator()
        results = v.run(ctx)
        assert len(results) == 1

    def test_csv_case_normalization(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", "https://Example.COM"),
        ]
        ds = _make_data_source(dump_records)
        rows = [
            {
                "id": "",
                "names.types.ror_display": "New Org",
                "links.type.website": "https://example.com",
            }
        ]
        ctx = _make_csv_ctx(tmp_path, rows, data_source=ds)
        v = DuplicateUrlsValidator()
        results = v.run(ctx)
        assert len(results) == 1

    def test_csv_multiple_rows(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", "https://example.com"),
        ]
        ds = _make_data_source(dump_records)
        rows = [
            {
                "id": "",
                "names.types.ror_display": "Match Org",
                "links.type.website": "https://example.com",
            },
            {
                "id": "",
                "names.types.ror_display": "No Match Org",
                "links.type.website": "https://unique.org",
            },
        ]
        ctx = _make_csv_ctx(tmp_path, rows, data_source=ds)
        v = DuplicateUrlsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["ror_display_name"] == "Match Org"


class TestDuplicateUrlsEdgeCases:
    def test_returns_empty_when_no_input(self, tmp_path):
        ds = _make_data_source([])
        ctx = ValidatorContext(
            csv_file=None,
            json_dir=None,
            output_dir=tmp_path,
            data_source=ds,
            geonames_user=None,
        )
        v = DuplicateUrlsValidator()
        results = v.run(ctx)
        assert results == []

    def test_empty_data_source(self, tmp_path):
        ds = _make_data_source([])
        input_records = [
            {
                "id": "",
                "names": [{"value": "New Org", "types": ["ror_display"]}],
                "links": [{"type": "website", "value": "https://example.com"}],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateUrlsValidator()
        results = v.run(ctx)
        assert results == []

    def test_multiple_dump_records(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Org A", "https://orga.com"),
            _dump_record("https://ror.org/dump002", "Org B", "https://orgb.com"),
            _dump_record("https://ror.org/dump003", "Org C", "https://orgc.com"),
        ]
        ds = _make_data_source(dump_records)
        input_records = [
            {
                "id": "",
                "names": [{"value": "New Org", "types": ["ror_display"]}],
                "links": [{"type": "website", "value": "https://orgb.com"}],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateUrlsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["data_dump_id"] == "https://ror.org/dump002"
        assert results[0]["data_dump_ror_display_name"] == "Org B"

    def test_prefers_json_over_csv(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", "https://example.com"),
        ]
        ds = _make_data_source(dump_records)

        json_dir = tmp_path / "json"
        json_dir.mkdir(parents=True, exist_ok=True)
        json_record = {
            "id": "",
            "names": [{"value": "JSON Org", "types": ["ror_display"]}],
            "links": [{"type": "website", "value": "https://example.com"}],
        }
        (json_dir / "rec.json").write_text(json.dumps(json_record), encoding="utf-8")

        csv_file = tmp_path / "input.csv"
        fieldnames = ["id", "names.types.ror_display", "links.type.website"]
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow({
                "id": "",
                "names.types.ror_display": "CSV Org",
                "links.type.website": "https://example.com",
            })

        ctx = ValidatorContext(
            csv_file=csv_file,
            json_dir=json_dir,
            output_dir=tmp_path / "output",
            data_source=ds,
            geonames_user=None,
        )
        v = DuplicateUrlsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["ror_display_name"] == "JSON Org"

    def test_input_record_no_links_key(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", "https://example.com"),
        ]
        ds = _make_data_source(dump_records)
        input_records = [
            {
                "id": "",
                "names": [{"value": "No Links Org", "types": ["ror_display"]}],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateUrlsValidator()
        results = v.run(ctx)
        assert results == []
