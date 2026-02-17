import csv
import json
from pathlib import Path

import pytest

from curation_validation.validators.base import ValidatorContext
from curation_validation.validators.duplicate_values import (
    DuplicateValuesValidator,
    should_ignore_duplicate,
)


@pytest.fixture
def validator():
    return DuplicateValuesValidator()


def _make_json_ctx(tmp_path, records):
    json_dir = tmp_path / "json"
    json_dir.mkdir()
    for i, record in enumerate(records):
        ror_id = record.get("id", f"https://ror.org/0{i:08d}")
        filename = ror_id.rsplit("/", 1)[-1] + ".json"
        (json_dir / filename).write_text(json.dumps(record))
    return ValidatorContext(
        csv_file=None,
        json_dir=json_dir,
        output_dir=tmp_path / "output",
        data_source=None,
        geonames_user=None,
    )


def _make_csv_ctx(tmp_path, rows, fieldnames=None):
    csv_file = tmp_path / "input.csv"
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return ValidatorContext(
        csv_file=csv_file,
        json_dir=None,
        output_dir=tmp_path / "output",
        data_source=None,
        geonames_user=None,
    )


def _base_csv_row(**overrides):
    row = {
        "id": "https://ror.org/012345678",
        "names.types.ror_display": "Test University",
        "status": "active",
        "types": "education",
        "names.types.acronym": "",
        "names.types.alias": "",
        "names.types.label": "",
        "links.type.website": "https://example.com",
        "links.type.wikipedia": "",
        "established": "2000",
        "external_ids.type.isni.all": "",
        "external_ids.type.isni.preferred": "",
        "external_ids.type.wikidata.all": "",
        "external_ids.type.wikidata.preferred": "",
        "external_ids.type.fundref.all": "",
        "external_ids.type.fundref.preferred": "",
        "locations.geonames_id": "1234567",
        "domains": "",
    }
    row.update(overrides)
    return row


def _base_json_record(**overrides):
    record = {
        "id": "https://ror.org/012345678",
        "names": [
            {"value": "Test University", "types": ["ror_display"], "lang": "en"}
        ],
        "status": "active",
        "types": ["education"],
        "links": [
            {"type": "website", "value": "https://example.com"}
        ],
        "external_ids": [],
        "locations": [
            {
                "geonames_id": 5007400,
                "geonames_details": {
                    "country_code": "US",
                    "country_name": "United States",
                    "lat": 42.0,
                    "lng": -83.0,
                    "name": "Rochester",
                },
            }
        ],
        "relationships": [],
        "domains": [],
        "established": 2000,
        "admin": {
            "created": {"date": "2026-01-01", "schema_version": "2.1"},
            "last_modified": {"date": "2026-01-01", "schema_version": "2.1"},
        },
    }
    record.update(overrides)
    return record


class TestValidatorProperties:
    def test_name(self, validator):
        assert validator.name == "duplicate_values"

    def test_supported_formats(self, validator):
        assert validator.supported_formats == {"csv", "json"}

    def test_output_filename(self, validator):
        assert validator.output_filename == "duplicate_values.csv"

    def test_output_fields(self, validator):
        assert validator.output_fields == [
            "issue_url", "record_id", "value", "field1", "field2"
        ]


class TestShouldIgnoreDuplicate:
    def test_ignore_empty_value(self):
        assert should_ignore_duplicate("", "field_a", "field_b") is True

    def test_ignore_none_value(self):
        assert should_ignore_duplicate(None, "field_a", "field_b") is True

    def test_ignore_null_string(self):
        assert should_ignore_duplicate("null", "field_a", "field_b") is True

    def test_ignore_admin_fields_both(self):
        assert should_ignore_duplicate(
            "2026-01-01",
            "admin_created_date",
            "admin_last_modified_date",
        ) is True

    def test_ignore_admin_field_one(self):
        assert should_ignore_duplicate(
            "2.1",
            "admin_created_schema_version",
            "admin_last_modified_schema_version",
        ) is True

    def test_ignore_preferred_all_same_index(self):
        assert should_ignore_duplicate(
            "0000 0001 2111 6211",
            "external_ids_0_preferred",
            "external_ids_0_all_0",
        ) is True

    def test_do_not_ignore_preferred_all_different_index(self):
        assert should_ignore_duplicate(
            "Q123",
            "external_ids_0_preferred",
            "external_ids_1_all_0",
        ) is False

    def test_ignore_lang_fields(self):
        assert should_ignore_duplicate(
            "en",
            "names_0_lang",
            "names_1_lang",
        ) is True

    def test_ignore_relationship_type_fields(self):
        assert should_ignore_duplicate(
            "related",
            "relationships_0_type",
            "relationships_1_type",
        ) is True

    def test_ignore_name_type_fields(self):
        assert should_ignore_duplicate(
            "ror_display",
            "names_0_types_0",
            "names_1_types_0",
        ) is True

    def test_do_not_ignore_real_duplicate(self):
        assert should_ignore_duplicate(
            "University of Testing",
            "names_0_value",
            "names_1_value",
        ) is False

    def test_ignore_common_relationship_type_value(self):
        for value in ("related", "parent", "child", "predecessor", "successor"):
            assert should_ignore_duplicate(
                value,
                "relationships_0_type",
                "relationships_1_type",
            ) is True


class TestJsonDuplicateDetection:
    def test_detects_duplicate_name_value(self, validator, tmp_path):
        record = _base_json_record(
            names=[
                {"value": "Duplicate Name", "types": ["ror_display"], "lang": "en"},
                {"value": "Duplicate Name", "types": ["alias"], "lang": "en"},
            ]
        )
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        dup_results = [r for r in results if r["value"] == "Duplicate Name"]
        assert len(dup_results) >= 1

    def test_detects_name_matching_link(self, validator, tmp_path):
        record = _base_json_record(
            names=[
                {"value": "https://example.com", "types": ["ror_display"], "lang": "en"},
            ],
            links=[
                {"type": "website", "value": "https://example.com"},
            ],
        )
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        dup_results = [r for r in results if r["value"] == "https://example.com"]
        assert len(dup_results) >= 1

    def test_no_duplicates_clean_record(self, validator, tmp_path):
        record = _base_json_record()
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        assert len(results) == 0

    def test_record_id_in_output(self, validator, tmp_path):
        record = _base_json_record(
            id="https://ror.org/099abcdef",
            names=[
                {"value": "Dup Val", "types": ["ror_display"], "lang": "en"},
                {"value": "Dup Val", "types": ["alias"], "lang": "en"},
            ],
        )
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        assert len(results) >= 1
        assert results[0]["record_id"] == "https://ror.org/099abcdef"

    def test_output_contains_field_names(self, validator, tmp_path):
        record = _base_json_record(
            names=[
                {"value": "Dup Val", "types": ["ror_display"], "lang": "en"},
                {"value": "Dup Val", "types": ["alias"], "lang": "en"},
            ],
        )
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        assert len(results) >= 1
        r = results[0]
        assert "field1" in r
        assert "field2" in r
        assert r["value"] == "Dup Val"

    def test_multiple_records(self, validator, tmp_path):
        records = [
            _base_json_record(
                id="https://ror.org/000000001",
                names=[
                    {"value": "Org A", "types": ["ror_display"], "lang": "en"},
                    {"value": "Org A", "types": ["alias"], "lang": "en"},
                ],
            ),
            _base_json_record(
                id="https://ror.org/000000002",
                names=[
                    {"value": "Org B", "types": ["ror_display"], "lang": "en"},
                    {"value": "Org B", "types": ["alias"], "lang": "en"},
                ],
            ),
        ]
        ctx = _make_json_ctx(tmp_path, records)
        results = validator.run(ctx)
        record_ids = {r["record_id"] for r in results}
        assert "https://ror.org/000000001" in record_ids
        assert "https://ror.org/000000002" in record_ids


class TestJsonIgnoredDuplicates:
    def test_admin_duplicates_ignored(self, validator, tmp_path):
        record = _base_json_record(
            admin={
                "created": {"date": "2026-01-01", "schema_version": "2.1"},
                "last_modified": {"date": "2026-01-01", "schema_version": "2.1"},
            }
        )
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        admin_results = [
            r for r in results
            if "admin" in r.get("field1", "") or "admin" in r.get("field2", "")
        ]
        assert len(admin_results) == 0

    def test_preferred_all_same_type_ignored(self, validator, tmp_path):
        record = _base_json_record(
            external_ids=[
                {
                    "type": "isni",
                    "all": ["0000 0001 2111 6211"],
                    "preferred": "0000 0001 2111 6211",
                }
            ],
        )
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        isni_results = [
            r for r in results if r["value"] == "0000 0001 2111 6211"
        ]
        assert len(isni_results) == 0

    def test_lang_duplicates_ignored(self, validator, tmp_path):
        record = _base_json_record(
            names=[
                {"value": "Name A", "types": ["ror_display"], "lang": "en"},
                {"value": "Name B", "types": ["alias"], "lang": "en"},
            ]
        )
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        lang_results = [r for r in results if r["value"] == "en"]
        assert len(lang_results) == 0

    def test_name_types_duplicates_ignored(self, validator, tmp_path):
        record = _base_json_record(
            names=[
                {"value": "Name A", "types": ["ror_display", "label"], "lang": "en"},
                {"value": "Name B", "types": ["ror_display"], "lang": "en"},
            ]
        )
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        type_results = [r for r in results if r["value"] == "ror_display"]
        assert len(type_results) == 0

    def test_relationship_types_duplicates_ignored(self, validator, tmp_path):
        record = _base_json_record(
            relationships=[
                {"id": "https://ror.org/000000001", "type": "related", "label": "Org A"},
                {"id": "https://ror.org/000000002", "type": "related", "label": "Org B"},
            ]
        )
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        rel_results = [r for r in results if r["value"] == "related"]
        assert len(rel_results) == 0

    def test_empty_string_values_ignored(self, validator, tmp_path):
        record = _base_json_record()
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        empty_results = [r for r in results if r["value"] == ""]
        assert len(empty_results) == 0

    def test_multiple_external_ids_preferred_all_ignored(self, validator, tmp_path):
        record = _base_json_record(
            external_ids=[
                {
                    "type": "isni",
                    "all": ["0000 0001 2111 6211"],
                    "preferred": "0000 0001 2111 6211",
                },
                {
                    "type": "wikidata",
                    "all": ["Q6467294"],
                    "preferred": "Q6467294",
                },
            ],
        )
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        ext_id_results = [
            r for r in results
            if r["value"] in ("0000 0001 2111 6211", "Q6467294")
        ]
        assert len(ext_id_results) == 0


class TestCsvDuplicateDetection:
    def test_detects_duplicate_across_fields(self, validator, tmp_path):
        row = _base_csv_row(**{
            "names.types.ror_display": "Duplicate Org",
            "names.types.alias": "Duplicate Org",
        })
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        dup_results = [r for r in results if r["value"] == "Duplicate Org"]
        assert len(dup_results) >= 1

    def test_no_duplicates_clean_csv(self, validator, tmp_path):
        row = _base_csv_row()
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        assert len(results) == 0

    def test_csv_record_id_in_output(self, validator, tmp_path):
        row = _base_csv_row(**{
            "id": "https://ror.org/099abcdef",
            "names.types.ror_display": "Dup Val",
            "names.types.alias": "Dup Val",
        })
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        assert len(results) >= 1
        assert results[0]["record_id"] == "https://ror.org/099abcdef"

    def test_csv_detects_name_matching_website(self, validator, tmp_path):
        row = _base_csv_row(**{
            "names.types.ror_display": "https://example.com",
            "links.type.website": "https://example.com",
        })
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        dup_results = [r for r in results if r["value"] == "https://example.com"]
        assert len(dup_results) >= 1

    def test_csv_semicolon_values_checked(self, validator, tmp_path):
        row = _base_csv_row(**{
            "names.types.ror_display": "Org Name",
            "names.types.alias": "Alias1; Org Name",
        })
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        dup_results = [r for r in results if r["value"] == "Org Name"]
        assert len(dup_results) >= 1


class TestCsvIgnoredDuplicates:
    def test_preferred_all_same_type_ignored(self, validator, tmp_path):
        row = _base_csv_row(**{
            "external_ids.type.isni.all": "0000 0001 2111 6211",
            "external_ids.type.isni.preferred": "0000 0001 2111 6211",
        })
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        isni_results = [r for r in results if r["value"] == "0000 0001 2111 6211"]
        assert len(isni_results) == 0

    def test_empty_fields_ignored(self, validator, tmp_path):
        row = _base_csv_row()
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        assert len(results) == 0

    def test_ror_display_label_same_value_ignored(self, validator, tmp_path):
        """ror_display must also have label type, so same value is expected."""
        row = _base_csv_row(**{
            "names.types.ror_display": "University Name",
            "names.types.label": "University Name",
        })
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        dup_results = [r for r in results if r["value"] == "University Name"]
        assert len(dup_results) == 0

    def test_ror_display_alias_same_value_detected(self, validator, tmp_path):
        """ror_display + alias with same value should still be flagged."""
        row = _base_csv_row(**{
            "names.types.ror_display": "Duplicate Org",
            "names.types.alias": "Duplicate Org",
        })
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        dup_results = [r for r in results if r["value"] == "Duplicate Org"]
        assert len(dup_results) >= 1


class TestEdgeCases:
    def test_no_json_dir_no_csv_returns_empty(self, validator, tmp_path):
        ctx = ValidatorContext(
            csv_file=None,
            json_dir=None,
            output_dir=tmp_path,
            data_source=None,
            geonames_user=None,
        )
        results = validator.run(ctx)
        assert results == []

    def test_empty_json_dir(self, validator, tmp_path):
        json_dir = tmp_path / "empty_json"
        json_dir.mkdir()
        ctx = ValidatorContext(
            csv_file=None,
            json_dir=json_dir,
            output_dir=tmp_path,
            data_source=None,
            geonames_user=None,
        )
        results = validator.run(ctx)
        assert results == []

    def test_value_appears_three_times(self, validator, tmp_path):
        record = _base_json_record(
            names=[
                {"value": "Triple Name", "types": ["ror_display"], "lang": "en"},
                {"value": "Triple Name", "types": ["alias"], "lang": "en"},
                {"value": "Triple Name", "types": ["label"], "lang": "fr"},
            ],
        )
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        triple_results = [r for r in results if r["value"] == "Triple Name"]
        assert len(triple_results) >= 1

    def test_non_string_values_not_compared(self, validator, tmp_path):
        record = _base_json_record()
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        assert len(results) == 0

    def test_cross_external_id_type_not_ignored(self, validator, tmp_path):
        record = _base_json_record(
            external_ids=[
                {
                    "type": "isni",
                    "all": ["SHARED_VALUE"],
                    "preferred": "SHARED_VALUE",
                },
                {
                    "type": "wikidata",
                    "all": ["SHARED_VALUE"],
                    "preferred": "SHARED_VALUE",
                },
            ],
        )
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        cross_results = [r for r in results if r["value"] == "SHARED_VALUE"]
        assert len(cross_results) >= 1
