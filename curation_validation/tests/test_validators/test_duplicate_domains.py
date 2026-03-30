import csv
import json
from pathlib import Path

import pytest

from curation_validation.validators.base import ValidatorContext
from curation_validation.core.loader import DataSource
from curation_validation.validators.duplicate_domains import (
    DuplicateDomainsValidator,
    get_ror_display_name,
    get_domains,
    normalize_domain,
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


def _dump_record(ror_id, display_name, domains):
    return {
        "id": ror_id,
        "names": [{"value": display_name, "types": ["ror_display"]}],
        "domains": domains,
    }


class TestDuplicateDomainsValidatorMetadata:
    def test_name(self):
        v = DuplicateDomainsValidator()
        assert v.name == "duplicate-domains"

    def test_supported_formats(self):
        v = DuplicateDomainsValidator()
        assert v.supported_formats == {"csv", "json"}

    def test_requires_data_source(self):
        v = DuplicateDomainsValidator()
        assert v.requires_data_source is True

    def test_output_filename(self):
        v = DuplicateDomainsValidator()
        assert v.output_filename == "duplicate_domains.csv"

    def test_output_fields(self):
        v = DuplicateDomainsValidator()
        expected = [
            "issue_url",
            "ror_display_name",
            "ror_id",
            "data_dump_id",
            "data_dump_ror_display_name",
            "input_domain",
            "data_dump_domain",
        ]
        assert v.output_fields == expected

    def test_can_run_without_data_source(self, tmp_path):
        v = DuplicateDomainsValidator()
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
        v = DuplicateDomainsValidator()
        can, _ = v.can_run(ctx)
        assert can is True


class TestNormalizeDomain:
    def test_lowercases(self):
        assert normalize_domain("Example.COM") == "example.com"

    def test_strips_whitespace(self):
        assert normalize_domain("  example.com  ") == "example.com"

    def test_strips_www(self):
        assert normalize_domain("www.example.com") == "example.com"

    def test_strips_trailing_dot(self):
        assert normalize_domain("example.com.") == "example.com"

    def test_preserves_subdomains(self):
        assert normalize_domain("dept.university.edu") == "dept.university.edu"

    def test_strips_www_but_preserves_other_subdomains(self):
        assert normalize_domain("www.dept.university.edu") == "dept.university.edu"

    def test_returns_none_for_empty(self):
        assert normalize_domain("") is None

    def test_returns_none_for_whitespace_only(self):
        assert normalize_domain("   ") is None

    def test_combined_normalization(self):
        assert normalize_domain("  WWW.Example.COM.  ") == "example.com"


class TestGetDomains:
    def test_returns_domains_list(self):
        record = {"domains": ["a.com", "b.com"]}
        assert get_domains(record) == ["a.com", "b.com"]

    def test_returns_empty_when_no_domains_key(self):
        assert get_domains({}) == []

    def test_returns_empty_list_when_empty(self):
        record = {"domains": []}
        assert get_domains(record) == []


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
        assert get_ror_display_name({}) == ""


class TestPreprocessDataSource:
    def test_builds_domain_dict(self):
        records = [
            _dump_record("https://ror.org/001", "University A", ["unia.edu"]),
        ]
        domain_dict = preprocess_data_source(records)
        assert "unia.edu" in domain_dict

    def test_adds_www_variant(self):
        records = [
            _dump_record("https://ror.org/001", "University A", ["unia.edu"]),
        ]
        domain_dict = preprocess_data_source(records)
        assert "www.unia.edu" in domain_dict

    def test_skips_records_without_domains(self):
        records = [
            {
                "id": "https://ror.org/001",
                "names": [{"value": "No Domain Org", "types": ["ror_display"]}],
                "domains": [],
            }
        ]
        domain_dict = preprocess_data_source(records)
        assert len(domain_dict) == 0

    def test_skips_empty_domain_strings(self):
        records = [
            _dump_record("https://ror.org/001", "Org", [""]),
        ]
        domain_dict = preprocess_data_source(records)
        assert len(domain_dict) == 0

    def test_stores_record_info(self):
        records = [
            _dump_record("https://ror.org/001", "University A", ["unia.edu"]),
        ]
        domain_dict = preprocess_data_source(records)
        info = domain_dict["unia.edu"]
        assert info["ror_id"] == "https://ror.org/001"
        assert info["ror_display_name"] == "University A"
        assert info["original_domain"] == "unia.edu"

    def test_multiple_domains_per_record(self):
        records = [
            _dump_record("https://ror.org/001", "University A", ["unia.edu", "unia.org"]),
        ]
        domain_dict = preprocess_data_source(records)
        assert "unia.edu" in domain_dict
        assert "unia.org" in domain_dict


class TestDuplicateDomainsJSON:
    def test_exact_domain_match(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", ["example.com"]),
        ]
        ds = _make_data_source(dump_records)
        input_records = [
            {
                "id": "",
                "names": [{"value": "New Org", "types": ["ror_display"]}],
                "domains": ["example.com"],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateDomainsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["ror_display_name"] == "New Org"
        assert results[0]["data_dump_id"] == "https://ror.org/dump001"
        assert results[0]["data_dump_ror_display_name"] == "Dump Org"

    def test_case_insensitive_match(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", ["Example.COM"]),
        ]
        ds = _make_data_source(dump_records)
        input_records = [
            {
                "id": "",
                "names": [{"value": "New Org", "types": ["ror_display"]}],
                "domains": ["example.com"],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateDomainsValidator()
        results = v.run(ctx)
        assert len(results) == 1

    def test_www_match(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", ["example.com"]),
        ]
        ds = _make_data_source(dump_records)
        input_records = [
            {
                "id": "",
                "names": [{"value": "New Org", "types": ["ror_display"]}],
                "domains": ["www.example.com"],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateDomainsValidator()
        results = v.run(ctx)
        assert len(results) == 1

    def test_no_match_different_domains(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", ["example.com"]),
        ]
        ds = _make_data_source(dump_records)
        input_records = [
            {
                "id": "",
                "names": [{"value": "New Org", "types": ["ror_display"]}],
                "domains": ["different.org"],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateDomainsValidator()
        results = v.run(ctx)
        assert len(results) == 0

    def test_no_match_subdomain_vs_root(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", ["example.com"]),
        ]
        ds = _make_data_source(dump_records)
        input_records = [
            {
                "id": "",
                "names": [{"value": "New Org", "types": ["ror_display"]}],
                "domains": ["sub.example.com"],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateDomainsValidator()
        results = v.run(ctx)
        assert len(results) == 0

    def test_no_match_root_vs_subdomain(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", ["dept.university.edu"]),
        ]
        ds = _make_data_source(dump_records)
        input_records = [
            {
                "id": "",
                "names": [{"value": "New Org", "types": ["ror_display"]}],
                "domains": ["university.edu"],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateDomainsValidator()
        results = v.run(ctx)
        assert len(results) == 0

    def test_multiple_domains_in_input_one_match(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", ["example.com"]),
        ]
        ds = _make_data_source(dump_records)
        input_records = [
            {
                "id": "",
                "names": [{"value": "New Org", "types": ["ror_display"]}],
                "domains": ["example.com", "unique.org"],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateDomainsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["input_domain"] == "example.com"

    def test_multiple_input_records(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", ["example.com"]),
        ]
        ds = _make_data_source(dump_records)
        input_records = [
            {
                "id": "",
                "names": [{"value": "Match Org", "types": ["ror_display"]}],
                "domains": ["example.com"],
            },
            {
                "id": "",
                "names": [{"value": "No Match Org", "types": ["ror_display"]}],
                "domains": ["unique.org"],
            },
        ]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateDomainsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["ror_display_name"] == "Match Org"

    def test_output_format_fields(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", ["example.com"]),
        ]
        ds = _make_data_source(dump_records)
        input_records = [
            {
                "id": "https://ror.org/input001",
                "names": [{"value": "New Org", "types": ["ror_display"]}],
                "domains": ["example.com"],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateDomainsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        result = results[0]
        assert "issue_url" in result
        assert "ror_display_name" in result
        assert "ror_id" in result
        assert "data_dump_id" in result
        assert "data_dump_ror_display_name" in result
        assert "input_domain" in result
        assert "data_dump_domain" in result

    def test_preserves_original_domains(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", ["Example.COM"]),
        ]
        ds = _make_data_source(dump_records)
        input_records = [
            {
                "id": "",
                "names": [{"value": "New Org", "types": ["ror_display"]}],
                "domains": ["EXAMPLE.com"],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateDomainsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["input_domain"] == "EXAMPLE.com"
        assert results[0]["data_dump_domain"] == "Example.COM"

    def test_empty_json_dir(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", ["example.com"]),
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
        v = DuplicateDomainsValidator()
        results = v.run(ctx)
        assert results == []

    def test_record_with_no_domains_key(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", ["example.com"]),
        ]
        ds = _make_data_source(dump_records)
        input_records = [
            {
                "id": "",
                "names": [{"value": "No Domains Org", "types": ["ror_display"]}],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateDomainsValidator()
        results = v.run(ctx)
        assert results == []

    def test_record_with_id_populated(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", ["example.com"]),
        ]
        ds = _make_data_source(dump_records)
        input_records = [
            {
                "id": "https://ror.org/myrecord",
                "names": [{"value": "My Org", "types": ["ror_display"]}],
                "domains": ["example.com"],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateDomainsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["ror_id"] == "https://ror.org/myrecord"
        assert results[0]["issue_url"] == "https://ror.org/myrecord"


class TestDuplicateDomainsCSV:
    def test_exact_domain_match_csv(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", ["example.com"]),
        ]
        ds = _make_data_source(dump_records)
        rows = [
            {
                "id": "",
                "names.types.ror_display": "New Org",
                "domains": "example.com",
            }
        ]
        ctx = _make_csv_ctx(tmp_path, rows, data_source=ds)
        v = DuplicateDomainsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["ror_display_name"] == "New Org"
        assert results[0]["data_dump_id"] == "https://ror.org/dump001"

    def test_case_insensitive_match_csv(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", ["Example.COM"]),
        ]
        ds = _make_data_source(dump_records)
        rows = [
            {
                "id": "",
                "names.types.ror_display": "New Org",
                "domains": "example.com",
            }
        ]
        ctx = _make_csv_ctx(tmp_path, rows, data_source=ds)
        v = DuplicateDomainsValidator()
        results = v.run(ctx)
        assert len(results) == 1

    def test_www_match_csv(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", ["example.com"]),
        ]
        ds = _make_data_source(dump_records)
        rows = [
            {
                "id": "",
                "names.types.ror_display": "New Org",
                "domains": "www.example.com",
            }
        ]
        ctx = _make_csv_ctx(tmp_path, rows, data_source=ds)
        v = DuplicateDomainsValidator()
        results = v.run(ctx)
        assert len(results) == 1

    def test_no_match_different_domains_csv(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", ["example.com"]),
        ]
        ds = _make_data_source(dump_records)
        rows = [
            {
                "id": "",
                "names.types.ror_display": "Other Org",
                "domains": "different.org",
            }
        ]
        ctx = _make_csv_ctx(tmp_path, rows, data_source=ds)
        v = DuplicateDomainsValidator()
        results = v.run(ctx)
        assert len(results) == 0

    def test_no_match_subdomain_vs_root_csv(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", ["example.com"]),
        ]
        ds = _make_data_source(dump_records)
        rows = [
            {
                "id": "",
                "names.types.ror_display": "Sub Org",
                "domains": "sub.example.com",
            }
        ]
        ctx = _make_csv_ctx(tmp_path, rows, data_source=ds)
        v = DuplicateDomainsValidator()
        results = v.run(ctx)
        assert len(results) == 0

    def test_semicolon_separated_domains_csv(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", ["example.com"]),
        ]
        ds = _make_data_source(dump_records)
        rows = [
            {
                "id": "",
                "names.types.ror_display": "New Org",
                "domains": "example.com;unique.org",
            }
        ]
        ctx = _make_csv_ctx(tmp_path, rows, data_source=ds)
        v = DuplicateDomainsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["input_domain"] == "example.com"

    def test_csv_no_domains_column(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", ["example.com"]),
        ]
        ds = _make_data_source(dump_records)
        rows = [
            {
                "id": "",
                "names.types.ror_display": "No Domain Org",
                "domains": "",
            }
        ]
        ctx = _make_csv_ctx(tmp_path, rows, data_source=ds)
        v = DuplicateDomainsValidator()
        results = v.run(ctx)
        assert len(results) == 0

    def test_csv_output_fields(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", ["example.com"]),
        ]
        ds = _make_data_source(dump_records)
        rows = [
            {
                "id": "https://ror.org/input001",
                "html_url": "https://github.com/issues/1",
                "names.types.ror_display": "New Org",
                "domains": "example.com",
            }
        ]
        ctx = _make_csv_ctx(tmp_path, rows, data_source=ds)
        v = DuplicateDomainsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        result = results[0]
        assert result["ror_display_name"] == "New Org"
        assert result["ror_id"] == "https://ror.org/input001"
        assert result["issue_url"] == "https://github.com/issues/1"
        assert result["data_dump_id"] == "https://ror.org/dump001"
        assert result["data_dump_ror_display_name"] == "Dump Org"
        assert result["input_domain"] == "example.com"
        assert result["data_dump_domain"] == "example.com"

    def test_csv_multiple_rows(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", ["example.com"]),
        ]
        ds = _make_data_source(dump_records)
        rows = [
            {
                "id": "",
                "names.types.ror_display": "Match Org",
                "domains": "example.com",
            },
            {
                "id": "",
                "names.types.ror_display": "No Match Org",
                "domains": "unique.org",
            },
        ]
        ctx = _make_csv_ctx(tmp_path, rows, data_source=ds)
        v = DuplicateDomainsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["ror_display_name"] == "Match Org"


class TestDuplicateDomainsEdgeCases:
    def test_returns_empty_when_no_input(self, tmp_path):
        ds = _make_data_source([])
        ctx = ValidatorContext(
            csv_file=None,
            json_dir=None,
            output_dir=tmp_path,
            data_source=ds,
            geonames_user=None,
        )
        v = DuplicateDomainsValidator()
        results = v.run(ctx)
        assert results == []

    def test_empty_data_source(self, tmp_path):
        ds = _make_data_source([])
        input_records = [
            {
                "id": "",
                "names": [{"value": "New Org", "types": ["ror_display"]}],
                "domains": ["example.com"],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateDomainsValidator()
        results = v.run(ctx)
        assert results == []

    def test_multiple_dump_records(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Org A", ["orga.com"]),
            _dump_record("https://ror.org/dump002", "Org B", ["orgb.com"]),
            _dump_record("https://ror.org/dump003", "Org C", ["orgc.com"]),
        ]
        ds = _make_data_source(dump_records)
        input_records = [
            {
                "id": "",
                "names": [{"value": "New Org", "types": ["ror_display"]}],
                "domains": ["orgb.com"],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateDomainsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["data_dump_id"] == "https://ror.org/dump002"
        assert results[0]["data_dump_ror_display_name"] == "Org B"

    def test_prefers_json_over_csv(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", ["example.com"]),
        ]
        ds = _make_data_source(dump_records)

        json_dir = tmp_path / "json"
        json_dir.mkdir(parents=True, exist_ok=True)
        json_record = {
            "id": "",
            "names": [{"value": "JSON Org", "types": ["ror_display"]}],
            "domains": ["example.com"],
        }
        (json_dir / "rec.json").write_text(json.dumps(json_record), encoding="utf-8")

        csv_file = tmp_path / "input.csv"
        fieldnames = ["id", "names.types.ror_display", "domains"]
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow({
                "id": "",
                "names.types.ror_display": "CSV Org",
                "domains": "example.com",
            })

        ctx = ValidatorContext(
            csv_file=csv_file,
            json_dir=json_dir,
            output_dir=tmp_path / "output",
            data_source=ds,
            geonames_user=None,
        )
        v = DuplicateDomainsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["ror_display_name"] == "JSON Org"

    def test_trailing_dot_normalization(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", ["example.com"]),
        ]
        ds = _make_data_source(dump_records)
        input_records = [
            {
                "id": "",
                "names": [{"value": "New Org", "types": ["ror_display"]}],
                "domains": ["example.com."],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateDomainsValidator()
        results = v.run(ctx)
        assert len(results) == 1

    def test_input_record_no_names_key(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", ["example.com"]),
        ]
        ds = _make_data_source(dump_records)
        input_records = [
            {
                "id": "",
                "domains": ["example.com"],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateDomainsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["ror_display_name"] == ""
