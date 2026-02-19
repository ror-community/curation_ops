import csv

import pytest

from curation_validation.validators.base import ValidatorContext
from curation_validation.validators.input_file_structure import (
    InputFileStructureValidator,
    _validate_ror_id,
    _validate_name_format,
    _get_actions_values,
)


@pytest.fixture
def validator():
    return InputFileStructureValidator()


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


def _complete_csv_row(**overrides):
    row = {
        "id": "",
        "domains": "",
        "established": "2000",
        "external_ids.type.fundref.all": "",
        "external_ids.type.fundref.preferred": "",
        "external_ids.type.grid.all": "",
        "external_ids.type.grid.preferred": "",
        "external_ids.type.isni.all": "",
        "external_ids.type.isni.preferred": "",
        "external_ids.type.wikidata.all": "",
        "external_ids.type.wikidata.preferred": "",
        "links.type.website": "https://example.com",
        "links.type.wikipedia": "",
        "locations.geonames_id": "5007400",
        "names.types.acronym": "",
        "names.types.alias": "",
        "names.types.label": "",
        "names.types.ror_display": "Test University*en",
        "status": "active",
        "types": "education",
        "html_url": "https://github.com/ror-community/issues/123",
    }
    row.update(overrides)
    return row


def _update_csv_row(**overrides):
    row = _complete_csv_row(id="https://ror.org/012345678")
    row.update(overrides)
    return row


class TestValidatorProperties:
    def test_name(self, validator):
        assert validator.name == "input_file_structure"

    def test_supported_formats(self, validator):
        assert validator.supported_formats == {"csv"}

    def test_output_filename(self, validator):
        assert validator.output_filename == "input_file_structure.csv"

    def test_output_fields(self, validator):
        expected = ["issue_url", "row_number", "error_type", "field", "value", "message"]
        assert validator.output_fields == expected


class TestValidateRorId:
    def test_valid_ror_id(self):
        assert _validate_ror_id("https://ror.org/012345678") is None

    def test_valid_ror_id_with_letters(self):
        assert _validate_ror_id("https://ror.org/0abcdefgh") is None

    def test_empty_ror_id_valid(self):
        assert _validate_ror_id("") is None

    def test_whitespace_only_valid(self):
        assert _validate_ror_id("   ") is None

    def test_invalid_ror_id_wrong_prefix(self):
        error = _validate_ror_id("http://ror.org/012345678")
        assert error is not None
        assert "must start with 'https://ror.org/'" in error

    def test_invalid_ror_id_too_short(self):
        error = _validate_ror_id("https://ror.org/12345")
        assert error is not None
        assert "exactly 9 lowercase alphanumeric" in error

    def test_invalid_ror_id_too_long(self):
        error = _validate_ror_id("https://ror.org/0123456789")
        assert error is not None

    def test_invalid_ror_id_uppercase(self):
        error = _validate_ror_id("https://ror.org/0ABCDEFGH")
        assert error is not None

    def test_invalid_ror_id_with_spaces(self):
        error = _validate_ror_id("https://ror.org/012 345 678")
        assert error is not None
        assert "contains whitespace" in error


class TestValidateNameFormat:
    def test_valid_name_with_language(self):
        assert _validate_name_format("Test University*en") is None

    def test_valid_name_without_asterisk(self):
        assert _validate_name_format("Test University") is None

    def test_empty_name_valid(self):
        assert _validate_name_format("") is None

    def test_name_ending_with_asterisk(self):
        error = _validate_name_format("Test University*")
        assert error is not None
        assert "ends with asterisk" in error

    def test_name_with_invalid_lang_code_too_long(self):
        error = _validate_name_format("Test*eng")
        assert error is not None
        assert "exactly two letters" in error

    def test_name_with_invalid_lang_code_numeric(self):
        error = _validate_name_format("Test*12")
        assert error is not None
        assert "exactly two letters" in error

    def test_name_with_multiple_asterisks(self):
        error = _validate_name_format("Test*en*fr")
        assert error is not None
        assert "multiple '*'" in error


class TestGetActionsValues:
    def test_simple_value_implicit_replace(self):
        result = _get_actions_values("new value")
        assert result == {"replace": ["new value"]}

    def test_add_action(self):
        result = _get_actions_values("add==value1")
        assert result == {"add": ["value1"]}

    def test_delete_action_with_value(self):
        result = _get_actions_values("delete==value1")
        assert result == {"delete": ["value1"]}

    def test_standalone_delete(self):
        result = _get_actions_values("delete")
        assert result == {"delete": None}

    def test_replace_action(self):
        result = _get_actions_values("replace==value1")
        assert result == {"replace": ["value1"]}

    def test_multiple_values_semicolon(self):
        result = _get_actions_values("add==val1;val2;val3")
        assert result == {"add": ["val1", "val2", "val3"]}

    def test_combined_add_delete(self):
        result = _get_actions_values("add==new1 delete==old1")
        assert "add" in result
        assert "delete" in result

    def test_empty_string(self):
        result = _get_actions_values("")
        assert result == {}


class TestHeaderValidation:
    def test_valid_header(self, validator, tmp_path):
        row = _complete_csv_row()
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        header_errors = [r for r in results if r["error_type"].startswith("header")]
        assert header_errors == []

    def test_missing_required_columns(self, validator, tmp_path):
        csv_file = tmp_path / "input.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            f.write("id,status\n")
            f.write("https://ror.org/012345678,active\n")
        ctx = ValidatorContext(
            csv_file=csv_file,
            json_dir=None,
            output_dir=tmp_path / "output",
            data_source=None,
            geonames_user=None,
        )
        results = validator.run(ctx)
        header_errors = [r for r in results if r["error_type"] == "header_missing_columns"]
        assert len(header_errors) == 1
        assert "missing required columns" in header_errors[0]["message"]


class TestRorIdValidation:
    def test_valid_ror_id_no_error(self, validator, tmp_path):
        row = _update_csv_row()
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        ror_errors = [r for r in results if r["error_type"] == "ror_id_invalid"]
        assert ror_errors == []

    def test_invalid_ror_id_format(self, validator, tmp_path):
        row = _update_csv_row(id="http://ror.org/012345678")
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        ror_errors = [r for r in results if r["error_type"] == "ror_id_invalid"]
        assert len(ror_errors) == 1

    def test_ror_id_too_short(self, validator, tmp_path):
        row = _update_csv_row(id="https://ror.org/12345")
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        ror_errors = [r for r in results if r["error_type"] == "ror_id_invalid"]
        assert len(ror_errors) == 1


class TestEmbeddedNewlines:
    def test_embedded_newline_detected(self, validator, tmp_path):
        row = _complete_csv_row()
        row["names.types.ror_display"] = "Test\nUniversity*en"
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        newline_errors = [r for r in results if r["error_type"] == "embedded_newline"]
        assert len(newline_errors) == 1
        assert "embedded newline" in newline_errors[0]["message"]

    def test_embedded_carriage_return_detected(self, validator, tmp_path):
        row = _complete_csv_row()
        row["status"] = "active\r"
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        newline_errors = [r for r in results if r["error_type"] == "embedded_newline"]
        assert len(newline_errors) == 1


class TestNewRecordValidation:
    def test_valid_new_record(self, validator, tmp_path):
        row = _complete_csv_row()
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        errors = [r for r in results if "error" in r["error_type"] or "invalid" in r["error_type"]]
        assert errors == []

    def test_new_record_missing_ror_display(self, validator, tmp_path):
        row = _complete_csv_row(**{"names.types.ror_display": ""})
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        missing_errors = [r for r in results if r["error_type"] == "new_record_missing_field"]
        assert any(r["field"] == "names.types.ror_display" for r in missing_errors)

    def test_new_record_missing_status(self, validator, tmp_path):
        row = _complete_csv_row(status="")
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        missing_errors = [r for r in results if r["error_type"] == "new_record_missing_field"]
        assert any(r["field"] == "status" for r in missing_errors)

    def test_new_record_missing_types(self, validator, tmp_path):
        row = _complete_csv_row(types="")
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        missing_errors = [r for r in results if r["error_type"] == "new_record_missing_field"]
        assert any(r["field"] == "types" for r in missing_errors)

    def test_new_record_missing_geonames(self, validator, tmp_path):
        row = _complete_csv_row(**{"locations.geonames_id": ""})
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        missing_errors = [r for r in results if r["error_type"] == "new_record_missing_field"]
        assert any(r["field"] == "locations.geonames_id" for r in missing_errors)

    def test_new_record_with_update_syntax_error(self, validator, tmp_path):
        row = _complete_csv_row(status="add==active")
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        syntax_errors = [r for r in results if r["error_type"] == "new_record_update_syntax"]
        assert len(syntax_errors) >= 1

    def test_new_record_with_delete_action_error(self, validator, tmp_path):
        row = _complete_csv_row(types="delete")
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        syntax_errors = [r for r in results if r["error_type"] == "new_record_update_syntax"]
        assert len(syntax_errors) >= 1


class TestUpdateRecordValidation:
    def test_valid_update_record(self, validator, tmp_path):
        row = _update_csv_row(status="replace==inactive")
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        errors = [r for r in results if "invalid" in r["error_type"] or "conflict" in r["error_type"]]
        assert errors == []

    def test_delete_on_required_field_error(self, validator, tmp_path):
        row = _update_csv_row(status="delete")
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        action_errors = [r for r in results if r["error_type"] == "update_action_invalid"]
        assert any(r["field"] == "status" for r in action_errors)

    def test_replace_with_add_conflict(self, validator, tmp_path):
        row = _update_csv_row(**{"links.type.website": "replace==https://new.com add==https://other.com"})
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        conflict_errors = [r for r in results if r["error_type"] == "update_action_conflict"]
        assert len(conflict_errors) >= 1

    def test_invalid_action_for_field(self, validator, tmp_path):
        row = _update_csv_row(**{"names.types.ror_display": "add==New Name*en"})
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        action_errors = [r for r in results if r["error_type"] == "update_action_invalid"]
        assert any(r["field"] == "names.types.ror_display" for r in action_errors)

    def test_ambiguous_multi_value_update(self, validator, tmp_path):
        row = _update_csv_row(domains="example.com")
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        ambiguous_errors = [r for r in results if r["error_type"] == "update_ambiguous"]
        assert any(r["field"] == "domains" for r in ambiguous_errors)


class TestNameFormatValidation:
    def test_valid_name_format(self, validator, tmp_path):
        row = _complete_csv_row(**{"names.types.ror_display": "Test University*en"})
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        name_errors = [r for r in results if r["error_type"] == "name_format_invalid"]
        assert name_errors == []

    def test_invalid_name_multiple_asterisks(self, validator, tmp_path):
        row = _complete_csv_row(**{"names.types.alias": "Test*en*fr"})
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        name_errors = [r for r in results if r["error_type"] == "name_format_invalid"]
        assert len(name_errors) >= 1

    def test_invalid_name_trailing_asterisk(self, validator, tmp_path):
        row = _complete_csv_row(**{"names.types.label": "Test*"})
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        name_errors = [r for r in results if r["error_type"] == "name_format_invalid"]
        assert len(name_errors) >= 1

    def test_name_validation_in_update_syntax(self, validator, tmp_path):
        row = _update_csv_row(**{"names.types.alias": "add==BadName*"})
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        name_errors = [r for r in results if r["error_type"] == "name_format_invalid"]
        assert len(name_errors) >= 1


class TestRowNumberTracking:
    def test_row_number_correct(self, validator, tmp_path):
        rows = [
            _complete_csv_row(),
            _complete_csv_row(status=""),
        ]
        ctx = _make_csv_ctx(tmp_path, rows)
        results = validator.run(ctx)
        missing_errors = [r for r in results if r["error_type"] == "new_record_missing_field"]
        assert any(r["row_number"] == 3 for r in missing_errors)

    def test_multiple_errors_same_row(self, validator, tmp_path):
        row = _complete_csv_row(status="", types="")
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        row_2_errors = [r for r in results if r["row_number"] == 2]
        assert len(row_2_errors) >= 2


class TestIssueUrl:
    def test_issue_url_extracted(self, validator, tmp_path):
        row = _complete_csv_row(
            status="",
            html_url="https://github.com/ror-community/issues/456"
        )
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        row_errors = [r for r in results if r["row_number"] > 1]
        assert len(row_errors) >= 1
        assert row_errors[0]["issue_url"] == "https://github.com/ror-community/issues/456"


class TestEdgeCases:
    def test_no_csv_file_returns_empty(self, validator, tmp_path):
        ctx = ValidatorContext(
            csv_file=None,
            json_dir=None,
            output_dir=tmp_path,
            data_source=None,
            geonames_user=None,
        )
        results = validator.run(ctx)
        assert results == []

    def test_file_not_found(self, validator, tmp_path):
        ctx = ValidatorContext(
            csv_file=tmp_path / "nonexistent.csv",
            json_dir=None,
            output_dir=tmp_path,
            data_source=None,
            geonames_user=None,
        )
        results = validator.run(ctx)
        assert len(results) == 1
        assert results[0]["error_type"] == "file_error"

    def test_empty_csv_no_data_rows(self, validator, tmp_path):
        row = _complete_csv_row()
        fieldnames = list(row.keys())
        csv_file = tmp_path / "input.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
        ctx = ValidatorContext(
            csv_file=csv_file,
            json_dir=None,
            output_dir=tmp_path / "output",
            data_source=None,
            geonames_user=None,
        )
        results = validator.run(ctx)
        assert results == []

    def test_column_mismatch_detected(self, validator, tmp_path):
        row = _complete_csv_row()
        fieldnames = list(row.keys())
        csv_file = tmp_path / "input.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, restval="", extrasaction="ignore")
            writer.writeheader()
            f.write(",".join(row.values()) + ",extra_value\n")
        ctx = ValidatorContext(
            csv_file=csv_file,
            json_dir=None,
            output_dir=tmp_path / "output",
            data_source=None,
            geonames_user=None,
        )
        results = validator.run(ctx)
        mismatch_errors = [r for r in results if r["error_type"] == "column_mismatch"]
        assert len(mismatch_errors) >= 1
