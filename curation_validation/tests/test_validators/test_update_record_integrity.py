import csv
import json
from pathlib import Path

import pytest

from curation_validation.validators.base import ValidatorContext
from curation_validation.validators.update_record_integrity import (
    UpdateRecordIntegrityValidator,
    parse_update_field,
    parse_row_updates,
    parse_record_updates_file,
    check_if_updates_applied,
)


def _write_csv(tmp_path, rows, fieldnames=None):
    csv_file = tmp_path / "updates.csv"
    if not rows:
        csv_file.write_text("", encoding="utf-8")
        return csv_file
    if fieldnames is None:
        fieldnames = list(rows[0].keys())
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return csv_file


def _write_json(json_dir, ror_id_suffix, record):
    json_dir.mkdir(parents=True, exist_ok=True)
    filepath = json_dir / f"{ror_id_suffix}.json"
    filepath.write_text(json.dumps(record), encoding="utf-8")
    return filepath


def _make_ctx(tmp_path, csv_rows, json_records):
    csv_file = _write_csv(tmp_path, csv_rows)
    json_dir = tmp_path / "json"
    json_dir.mkdir(parents=True, exist_ok=True)
    for ror_id_suffix, record in json_records.items():
        _write_json(json_dir, ror_id_suffix, record)
    return ValidatorContext(
        csv_file=csv_file,
        json_dir=json_dir,
        output_dir=tmp_path / "output",
        data_source=None,
        geonames_user=None,
    )


def _minimal_json_record(names=None, types=None, status="active",
                          established=None, links=None, external_ids=None,
                          locations=None):
    record = {
        "status": status,
        "types": types or [],
        "names": names or [],
        "links": links or [],
        "external_ids": external_ids or [],
        "locations": locations or [],
    }
    if established is not None:
        record["established"] = established
    return record


class TestUpdateRecordIntegrityValidatorMetadata:
    def test_name(self):
        v = UpdateRecordIntegrityValidator()
        assert v.name == "update-record-integrity"

    def test_supported_formats(self):
        v = UpdateRecordIntegrityValidator()
        assert v.supported_formats == {"csv_json"}

    def test_output_filename(self):
        v = UpdateRecordIntegrityValidator()
        assert v.output_filename == "update_record_integrity.csv"

    def test_output_fields(self):
        v = UpdateRecordIntegrityValidator()
        expected = [
            "html_url", "ror_id", "field", "type", "value", "position", "status"
        ]
        assert v.output_fields == expected

    def test_does_not_require_data_source(self):
        v = UpdateRecordIntegrityValidator()
        assert v.requires_data_source is False

    def test_can_run_always(self, tmp_path):
        v = UpdateRecordIntegrityValidator()
        ctx = ValidatorContext(
            csv_file=None,
            json_dir=None,
            output_dir=tmp_path,
            data_source=None,
            geonames_user=None,
        )
        can, _ = v.can_run(ctx)
        assert can is True


class TestParseUpdateField:
    def test_single_add(self):
        result = parse_update_field("add==Test University")
        assert result == {"add": ["Test University"]}

    def test_single_delete(self):
        result = parse_update_field("delete==Old Name")
        assert result == {"delete": ["Old Name"]}

    def test_single_replace(self):
        result = parse_update_field("replace==New Name")
        assert result == {"replace": ["New Name"]}

    def test_multiple_values_same_type(self):
        result = parse_update_field("add==Value1;add==Value2")
        assert result == {"add": ["Value1", "Value2"]}

    def test_mixed_change_types(self):
        result = parse_update_field("add==New Name;delete==Old Name")
        assert result == {"add": ["New Name"], "delete": ["Old Name"]}

    def test_continuation_values(self):
        result = parse_update_field("add==Value1;Value2")
        assert result == {"add": ["Value1", "Value2"]}

    def test_bare_value_defaults_to_replace(self):
        result = parse_update_field("SomeValue")
        assert result == {"replace": ["SomeValue"]}

    def test_empty_string(self):
        result = parse_update_field("")
        assert result == {"replace": [""]}

    def test_value_with_asterisk(self):
        result = parse_update_field("add==University Name*en")
        assert result == {"add": ["University Name*en"]}

    def test_replace_delete(self):
        result = parse_update_field("replace==delete")
        assert result == {"replace": ["delete"]}


class TestParseRowUpdates:
    def test_parses_all_fields(self):
        row = {
            "names.types.label": "add==New Label*fr",
            "types": "replace==education",
            "status": "",
        }
        result = parse_row_updates(row)
        assert result["names.types.label"] == {"add": ["New Label*fr"]}
        assert result["types"] == {"replace": ["education"]}
        assert result["status"] == {"replace": [""]}


class TestParseRecordUpdatesFile:
    def test_basic_parsing(self):
        records = [
            {
                "id": "https://ror.org/01abc2345",
                "html_url": "https://github.com/ror-community/issues/1",
                "names.types.label": "add==New Label*fr",
                "types": "",
                "status": "",
            }
        ]
        result = parse_record_updates_file(records)
        assert "https://ror.org/01abc2345" in result
        updates = result["https://ror.org/01abc2345"]
        assert len(updates) == 1
        assert updates[0]["field"] == "names.types.label"
        assert updates[0]["change_type"] == "add"
        assert updates[0]["value"] == "New Label*fr"

    def test_filters_invalid_fields(self):
        records = [
            {
                "id": "https://ror.org/01abc2345",
                "html_url": "https://github.com/issues/1",
                "some_invalid_field": "add==value",
                "names.types.label": "add==Valid*en",
            }
        ]
        result = parse_record_updates_file(records)
        updates = result["https://ror.org/01abc2345"]
        fields = [u["field"] for u in updates]
        assert "some_invalid_field" not in fields
        assert "names.types.label" in fields

    def test_skips_empty_values(self):
        records = [
            {
                "id": "https://ror.org/01abc2345",
                "html_url": "https://github.com/issues/1",
                "names.types.label": "",
            }
        ]
        result = parse_record_updates_file(records)
        updates = result.get("https://ror.org/01abc2345", [])
        assert len(updates) == 0

    def test_multiple_records(self):
        records = [
            {
                "id": "https://ror.org/01abc2345",
                "html_url": "https://github.com/issues/1",
                "names.types.label": "add==Label A*en",
            },
            {
                "id": "https://ror.org/02def6789",
                "html_url": "https://github.com/issues/2",
                "types": "replace==education",
            },
        ]
        result = parse_record_updates_file(records)
        assert len(result["https://ror.org/01abc2345"]) == 1
        assert len(result["https://ror.org/02def6789"]) == 1


class TestMissingAdditions:
    def test_detects_missing_added_name(self, tmp_path):
        csv_rows = [{
            "id": "https://ror.org/01abc2345",
            "html_url": "https://github.com/issues/1",
            "names.types.label": "add==Missing Label*en",
        }]
        json_record = _minimal_json_record(
            names=[{"value": "Some Other Name", "types": ["ror_display"]}]
        )
        json_records = {"01abc2345": json_record}
        ctx = _make_ctx(tmp_path, csv_rows, json_records)
        results = check_if_updates_applied(ctx.csv_file, ctx.json_dir)
        assert len(results) == 1
        assert results[0]["status"] == "missing"
        assert results[0]["field"] == "names.types.label"
        assert results[0]["type"] == "add"
        assert results[0]["value"] == "Missing Label"
        assert results[0]["ror_id"] == "https://ror.org/01abc2345"
        assert results[0]["html_url"] == "https://github.com/issues/1"

    def test_detects_missing_replaced_value(self, tmp_path):
        csv_rows = [{
            "id": "https://ror.org/01abc2345",
            "html_url": "https://github.com/issues/1",
            "names.types.ror_display": "replace==New Display Name",
        }]
        json_record = _minimal_json_record(
            names=[{"value": "Old Display Name", "types": ["ror_display"]}]
        )
        json_records = {"01abc2345": json_record}
        ctx = _make_ctx(tmp_path, csv_rows, json_records)
        results = check_if_updates_applied(ctx.csv_file, ctx.json_dir)
        assert len(results) == 1
        assert results[0]["status"] == "missing"
        assert results[0]["type"] == "replace"

    def test_no_error_when_addition_present(self, tmp_path):
        csv_rows = [{
            "id": "https://ror.org/01abc2345",
            "html_url": "https://github.com/issues/1",
            "names.types.label": "add==Present Label*en",
        }]
        json_record = _minimal_json_record(
            names=[
                {"value": "Display Name", "types": ["ror_display"]},
                {"value": "Present Label", "types": ["label"]},
            ]
        )
        json_records = {"01abc2345": json_record}
        ctx = _make_ctx(tmp_path, csv_rows, json_records)
        results = check_if_updates_applied(ctx.csv_file, ctx.json_dir)
        assert len(results) == 0


class TestStillPresentDeletions:
    def test_detects_still_present_deletion(self, tmp_path):
        csv_rows = [{
            "id": "https://ror.org/01abc2345",
            "html_url": "https://github.com/issues/1",
            "names.types.alias": "delete==Old Alias",
        }]
        json_record = _minimal_json_record(
            names=[
                {"value": "Main Name", "types": ["ror_display"]},
                {"value": "Old Alias", "types": ["alias"]},
            ]
        )
        json_records = {"01abc2345": json_record}
        ctx = _make_ctx(tmp_path, csv_rows, json_records)
        results = check_if_updates_applied(ctx.csv_file, ctx.json_dir)
        assert len(results) == 1
        assert results[0]["status"] == "still_present"
        assert results[0]["field"] == "names.types.alias"
        assert results[0]["type"] == "delete"
        assert results[0]["position"] == "Old Alias"
        assert results[0]["value"] == ""

    def test_no_error_when_deletion_applied(self, tmp_path):
        csv_rows = [{
            "id": "https://ror.org/01abc2345",
            "html_url": "https://github.com/issues/1",
            "names.types.alias": "delete==Removed Alias",
        }]
        json_record = _minimal_json_record(
            names=[{"value": "Main Name", "types": ["ror_display"]}]
        )
        json_records = {"01abc2345": json_record}
        ctx = _make_ctx(tmp_path, csv_rows, json_records)
        results = check_if_updates_applied(ctx.csv_file, ctx.json_dir)
        assert len(results) == 0


class TestReplaceDelete:
    def test_detects_replace_delete_still_present(self, tmp_path):
        csv_rows = [{
            "id": "https://ror.org/01abc2345",
            "html_url": "https://github.com/issues/1",
            "links.type.wikipedia": "replace==delete",
        }]
        json_record = _minimal_json_record(
            links=[{"type": "wikipedia", "value": "https://en.wikipedia.org/wiki/Org"}]
        )
        json_records = {"01abc2345": json_record}
        ctx = _make_ctx(tmp_path, csv_rows, json_records)
        results = check_if_updates_applied(ctx.csv_file, ctx.json_dir)
        assert len(results) == 1
        assert results[0]["status"] == "still_present"
        assert results[0]["type"] == "replace"
        assert results[0]["value"] == "delete"

    def test_replace_delete_not_flagged_when_field_empty(self, tmp_path):
        csv_rows = [{
            "id": "https://ror.org/01abc2345",
            "html_url": "https://github.com/issues/1",
            "links.type.wikipedia": "replace==delete",
        }]
        json_record = _minimal_json_record(links=[])
        json_records = {"01abc2345": json_record}
        ctx = _make_ctx(tmp_path, csv_rows, json_records)
        results = check_if_updates_applied(ctx.csv_file, ctx.json_dir)
        assert len(results) == 0

    def test_replace_delete_case_insensitive(self, tmp_path):
        csv_rows = [{
            "id": "https://ror.org/01abc2345",
            "html_url": "https://github.com/issues/1",
            "links.type.website": "replace==Delete",
        }]
        json_record = _minimal_json_record(
            links=[{"type": "website", "value": "https://example.com"}]
        )
        json_records = {"01abc2345": json_record}
        ctx = _make_ctx(tmp_path, csv_rows, json_records)
        results = check_if_updates_applied(ctx.csv_file, ctx.json_dir)
        assert len(results) == 1
        assert results[0]["status"] == "still_present"


class TestIntegerFields:
    def test_established_as_integer(self, tmp_path):
        csv_rows = [{
            "id": "https://ror.org/01abc2345",
            "html_url": "https://github.com/issues/1",
            "established": "replace==1990",
        }]
        json_record = _minimal_json_record(established=1990)
        json_records = {"01abc2345": json_record}
        ctx = _make_ctx(tmp_path, csv_rows, json_records)
        results = check_if_updates_applied(ctx.csv_file, ctx.json_dir)
        assert len(results) == 0

    def test_established_missing(self, tmp_path):
        csv_rows = [{
            "id": "https://ror.org/01abc2345",
            "html_url": "https://github.com/issues/1",
            "established": "replace==1990",
        }]
        json_record = _minimal_json_record(established=2000)
        json_records = {"01abc2345": json_record}
        ctx = _make_ctx(tmp_path, csv_rows, json_records)
        results = check_if_updates_applied(ctx.csv_file, ctx.json_dir)
        assert len(results) == 1
        assert results[0]["status"] == "missing"
        assert results[0]["value"] == "1990"

    def test_geonames_id_as_integer(self, tmp_path):
        csv_rows = [{
            "id": "https://ror.org/01abc2345",
            "html_url": "https://github.com/issues/1",
            "locations.geonames_id": "replace==5128581",
        }]
        json_record = _minimal_json_record(
            locations=[{"geonames_id": 5128581}]
        )
        json_records = {"01abc2345": json_record}
        ctx = _make_ctx(tmp_path, csv_rows, json_records)
        results = check_if_updates_applied(ctx.csv_file, ctx.json_dir)
        assert len(results) == 0

    def test_geonames_id_missing(self, tmp_path):
        csv_rows = [{
            "id": "https://ror.org/01abc2345",
            "html_url": "https://github.com/issues/1",
            "locations.geonames_id": "replace==5128581",
        }]
        json_record = _minimal_json_record(
            locations=[{"geonames_id": 9999999}]
        )
        json_records = {"01abc2345": json_record}
        ctx = _make_ctx(tmp_path, csv_rows, json_records)
        results = check_if_updates_applied(ctx.csv_file, ctx.json_dir)
        assert len(results) == 1
        assert results[0]["status"] == "missing"


class TestTypesLowercasing:
    def test_types_lowercased_for_comparison(self, tmp_path):
        csv_rows = [{
            "id": "https://ror.org/01abc2345",
            "html_url": "https://github.com/issues/1",
            "types": "replace==Education",
        }]
        json_record = _minimal_json_record(types=["education"])
        json_records = {"01abc2345": json_record}
        ctx = _make_ctx(tmp_path, csv_rows, json_records)
        results = check_if_updates_applied(ctx.csv_file, ctx.json_dir)
        assert len(results) == 0

    def test_types_missing(self, tmp_path):
        csv_rows = [{
            "id": "https://ror.org/01abc2345",
            "html_url": "https://github.com/issues/1",
            "types": "replace==Education",
        }]
        json_record = _minimal_json_record(types=["nonprofit"])
        json_records = {"01abc2345": json_record}
        ctx = _make_ctx(tmp_path, csv_rows, json_records)
        results = check_if_updates_applied(ctx.csv_file, ctx.json_dir)
        assert len(results) == 1
        assert results[0]["status"] == "missing"


class TestAsteriskStripping:
    def test_strips_language_suffix(self, tmp_path):
        csv_rows = [{
            "id": "https://ror.org/01abc2345",
            "html_url": "https://github.com/issues/1",
            "names.types.label": "add==Universite de Paris*fr",
        }]
        json_record = _minimal_json_record(
            names=[
                {"value": "Main Name", "types": ["ror_display"]},
                {"value": "Universite de Paris", "types": ["label"]},
            ]
        )
        json_records = {"01abc2345": json_record}
        ctx = _make_ctx(tmp_path, csv_rows, json_records)
        results = check_if_updates_applied(ctx.csv_file, ctx.json_dir)
        assert len(results) == 0

    def test_asterisk_stripped_for_missing_detection(self, tmp_path):
        csv_rows = [{
            "id": "https://ror.org/01abc2345",
            "html_url": "https://github.com/issues/1",
            "names.types.label": "add==NotThere*fr",
        }]
        json_record = _minimal_json_record(
            names=[{"value": "Main Name", "types": ["ror_display"]}]
        )
        json_records = {"01abc2345": json_record}
        ctx = _make_ctx(tmp_path, csv_rows, json_records)
        results = check_if_updates_applied(ctx.csv_file, ctx.json_dir)
        assert len(results) == 1
        assert results[0]["value"] == "NotThere"


class TestValidUpdatesNoErrors:
    def test_all_additions_present(self, tmp_path):
        csv_rows = [{
            "id": "https://ror.org/01abc2345",
            "html_url": "https://github.com/issues/1",
            "names.types.alias": "add==New Alias",
            "names.types.label": "add==New Label*fr",
            "links.type.website": "replace==https://example.com",
        }]
        json_record = _minimal_json_record(
            names=[
                {"value": "Display Name", "types": ["ror_display"]},
                {"value": "New Alias", "types": ["alias"]},
                {"value": "New Label", "types": ["label"]},
            ],
            links=[{"type": "website", "value": "https://example.com"}],
        )
        json_records = {"01abc2345": json_record}
        ctx = _make_ctx(tmp_path, csv_rows, json_records)
        results = check_if_updates_applied(ctx.csv_file, ctx.json_dir)
        assert len(results) == 0

    def test_all_deletions_applied(self, tmp_path):
        csv_rows = [{
            "id": "https://ror.org/01abc2345",
            "html_url": "https://github.com/issues/1",
            "names.types.alias": "delete==Old Alias",
        }]
        json_record = _minimal_json_record(
            names=[{"value": "Display Name", "types": ["ror_display"]}]
        )
        json_records = {"01abc2345": json_record}
        ctx = _make_ctx(tmp_path, csv_rows, json_records)
        results = check_if_updates_applied(ctx.csv_file, ctx.json_dir)
        assert len(results) == 0

    def test_empty_csv_no_errors(self, tmp_path):
        csv_file = _write_csv(tmp_path, [])
        json_dir = tmp_path / "json"
        json_dir.mkdir(parents=True, exist_ok=True)
        results = check_if_updates_applied(csv_file, json_dir)
        assert len(results) == 0


class TestExternalIds:
    def test_isni_present(self, tmp_path):
        csv_rows = [{
            "id": "https://ror.org/01abc2345",
            "html_url": "https://github.com/issues/1",
            "external_ids.type.isni.all": "add==0000 0001 2345 6789",
        }]
        json_record = _minimal_json_record(
            external_ids=[{
                "type": "isni",
                "preferred": "0000 0001 2345 6789",
                "all": ["0000 0001 2345 6789"],
            }]
        )
        json_records = {"01abc2345": json_record}
        ctx = _make_ctx(tmp_path, csv_rows, json_records)
        results = check_if_updates_applied(ctx.csv_file, ctx.json_dir)
        assert len(results) == 0

    def test_isni_missing(self, tmp_path):
        csv_rows = [{
            "id": "https://ror.org/01abc2345",
            "html_url": "https://github.com/issues/1",
            "external_ids.type.isni.all": "add==0000 0001 2345 6789",
        }]
        json_record = _minimal_json_record(external_ids=[])
        json_records = {"01abc2345": json_record}
        ctx = _make_ctx(tmp_path, csv_rows, json_records)
        results = check_if_updates_applied(ctx.csv_file, ctx.json_dir)
        assert len(results) == 1
        assert results[0]["status"] == "missing"


class TestMultipleUpdates:
    def test_multiple_updates_in_one_field(self, tmp_path):
        csv_rows = [{
            "id": "https://ror.org/01abc2345",
            "html_url": "https://github.com/issues/1",
            "names.types.alias": "add==Alias One;add==Alias Two",
        }]
        json_record = _minimal_json_record(
            names=[
                {"value": "Display", "types": ["ror_display"]},
                {"value": "Alias One", "types": ["alias"]},
            ]
        )
        json_records = {"01abc2345": json_record}
        ctx = _make_ctx(tmp_path, csv_rows, json_records)
        results = check_if_updates_applied(ctx.csv_file, ctx.json_dir)
        assert len(results) == 1
        assert results[0]["value"] == "Alias Two"
        assert results[0]["status"] == "missing"


class TestOutputFieldStructure:
    def test_output_has_all_required_fields(self, tmp_path):
        csv_rows = [{
            "id": "https://ror.org/01abc2345",
            "html_url": "https://github.com/issues/1",
            "names.types.label": "add==Missing*en",
        }]
        json_record = _minimal_json_record(
            names=[{"value": "Other", "types": ["ror_display"]}]
        )
        json_records = {"01abc2345": json_record}
        ctx = _make_ctx(tmp_path, csv_rows, json_records)
        results = check_if_updates_applied(ctx.csv_file, ctx.json_dir)
        assert len(results) == 1
        expected_fields = {"html_url", "ror_id", "field", "type", "value", "position", "status"}
        assert set(results[0].keys()) == expected_fields


class TestValidatorRun:
    def test_run_detects_missing_addition(self, tmp_path):
        csv_rows = [{
            "id": "https://ror.org/01abc2345",
            "html_url": "https://github.com/issues/1",
            "names.types.label": "add==Missing Label*en",
        }]
        json_record = _minimal_json_record(
            names=[{"value": "Other", "types": ["ror_display"]}]
        )
        ctx = _make_ctx(tmp_path, csv_rows, {"01abc2345": json_record})
        v = UpdateRecordIntegrityValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["status"] == "missing"

    def test_run_returns_empty_for_valid_updates(self, tmp_path):
        csv_rows = [{
            "id": "https://ror.org/01abc2345",
            "html_url": "https://github.com/issues/1",
            "names.types.label": "add==Present Label*en",
        }]
        json_record = _minimal_json_record(
            names=[
                {"value": "Display", "types": ["ror_display"]},
                {"value": "Present Label", "types": ["label"]},
            ]
        )
        ctx = _make_ctx(tmp_path, csv_rows, {"01abc2345": json_record})
        v = UpdateRecordIntegrityValidator()
        results = v.run(ctx)
        assert len(results) == 0
