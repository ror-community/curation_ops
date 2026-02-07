import csv
import json
from pathlib import Path

import pytest

from curation_validation.validators.base import ValidatorContext
from curation_validation.validators.validate_fields import (
    ValidateFieldsValidator,
    validate_status,
    validate_types,
    validate_acronyms,
    validate_names,
    validate_links,
    validate_established,
    validate_wikipedia_url,
    validate_isni,
    validate_wikidata,
    validate_fundref,
    validate_geonames,
    validate_city,
    validate_country,
    validate_field_value,
    parse_update_field,
    validate_updates,
    FIELD_VALIDATORS,
)


@pytest.fixture
def validator():
    return ValidateFieldsValidator()


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


def _minimal_json_record(**overrides):
    record = {
        "id": "https://ror.org/012345678",
        "status": "active",
        "types": ["education"],
        "names": [
            {"value": "Test University", "types": ["ror_display"], "lang": "en"}
        ],
        "links": [
            {"type": "website", "value": "https://example.com"}
        ],
        "external_ids": [],
        "locations": [
            {
                "geonames_id": 5007400,
                "geonames_details": {
                    "name": "City",
                    "country_name": "Country",
                    "country_code": "US",
                    "lat": 42.0,
                    "lng": -83.0,
                },
            }
        ],
        "relationships": [],
        "domains": [],
        "established": 2000,
        "admin": {},
    }
    record.update(overrides)
    return record


def _new_csv_row(**overrides):
    row = {
        "status": "active",
        "types": "education",
        "names.types.ror_display": "Test University*en",
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
        "locations.geonames_id": "5007400",
        "domains": "",
        "city": "Rochester",
        "country": "US",
    }
    row.update(overrides)
    return row


def _update_csv_row(**overrides):
    row = {
        "id": "https://ror.org/012345678",
        "status": "active",
        "types": "education",
        "names.types.ror_display": "",
        "names.types.acronym": "",
        "names.types.alias": "",
        "names.types.label": "",
        "links.type.website": "",
        "links.type.wikipedia": "",
        "established": "",
        "external_ids.type.isni.all": "",
        "external_ids.type.isni.preferred": "",
        "external_ids.type.wikidata.all": "",
        "external_ids.type.wikidata.preferred": "",
        "external_ids.type.fundref.all": "",
        "external_ids.type.fundref.preferred": "",
        "locations.geonames_id": "",
        "domains": "",
    }
    row.update(overrides)
    return row


class TestValidatorProperties:
    def test_name(self, validator):
        assert validator.name == "validate_fields"

    def test_supported_formats(self, validator):
        assert validator.supported_formats == {"csv", "json"}

    def test_output_filename(self, validator):
        assert validator.output_filename == "validate_fields.csv"

    def test_output_fields(self, validator):
        assert validator.output_fields == ["issue_url", "ror_id", "error_warning"]


class TestValidateStatus:
    def test_valid_statuses(self):
        for status in ["active", "inactive", "withdrawn"]:
            assert validate_status(status) == []

    def test_invalid_status(self):
        errors = validate_status("closed")
        assert len(errors) == 1
        assert "Invalid value" in errors[0]

    def test_empty_status(self):
        errors = validate_status("")
        assert len(errors) == 1


class TestValidateTypes:
    def test_valid_types(self):
        for t in ["education", "healthcare", "company", "funder", "archive",
                   "nonprofit", "government", "facility", "other"]:
            assert validate_types(t) == []

    def test_valid_type_with_parenthetical(self):
        assert validate_types("education(primary)") == []

    def test_invalid_type(self):
        errors = validate_types("university")
        assert len(errors) == 1
        assert "Invalid value(s)" in errors[0]

    def test_empty_type(self):
        errors = validate_types("")
        assert len(errors) == 1


class TestValidateAcronyms:
    def test_valid_acronym(self):
        assert validate_acronyms("MIT") == []

    def test_valid_acronym_with_numbers(self):
        assert validate_acronyms("A1B2") == []

    def test_valid_acronym_with_spaces(self):
        assert validate_acronyms("MIT LLE") == []

    def test_delete_value(self):
        assert validate_acronyms("delete") == []

    def test_acronym_with_star_suffix(self):
        assert validate_acronyms("MIT*en") == []

    def test_invalid_acronym_lowercase(self):
        errors = validate_acronyms("mit")
        assert len(errors) == 1
        assert "Potential invalid value" in errors[0]

    def test_empty_acronym(self):
        errors = validate_acronyms("")
        assert len(errors) == 1


class TestValidateNames:
    def test_valid_name_with_language(self):
        assert validate_names("University of Example*en") == []

    def test_delete_value(self):
        assert validate_names("delete") == []

    def test_invalid_name_no_language(self):
        errors = validate_names("University of Example")
        assert len(errors) == 1
        assert "Expected format" in errors[0]

    def test_empty_name(self):
        errors = validate_names("")
        assert len(errors) == 1


class TestValidateLinks:
    def test_valid_http_url(self):
        assert validate_links("http://example.com") == []

    def test_valid_https_url(self):
        assert validate_links("https://example.com") == []

    def test_delete_value(self):
        assert validate_links("delete") == []

    def test_invalid_url(self):
        errors = validate_links("example.com")
        assert len(errors) == 1
        assert "Invalid URL(s)" in errors[0]

    def test_empty_url(self):
        errors = validate_links("")
        assert len(errors) == 1


class TestValidateEstablished:
    def test_valid_year(self):
        assert validate_established("2000") == []

    def test_valid_old_year(self):
        assert validate_established("1000") == []

    def test_valid_future_year(self):
        assert validate_established("9999") == []

    def test_too_short_year(self):
        errors = validate_established("99")
        assert len(errors) == 1
        assert "Not a 4-digit year" in errors[0]

    def test_non_numeric(self):
        errors = validate_established("unknown")
        assert len(errors) == 1
        assert "not a valid year format" in errors[0]


class TestValidateWikipediaUrl:
    def test_valid_wikipedia_url(self):
        assert validate_wikipedia_url("https://en.wikipedia.org/wiki/MIT") == []

    def test_valid_wikipedia_with_http(self):
        assert validate_wikipedia_url("http://en.wikipedia.org/wiki/MIT") == []

    def test_invalid_wikipedia_url(self):
        errors = validate_wikipedia_url("https://example.com")
        assert len(errors) == 1
        assert "Invalid Wikipedia URL" in errors[0]

    def test_empty_wikipedia_url(self):
        errors = validate_wikipedia_url("")
        assert len(errors) == 1


class TestValidateIsni:
    def test_valid_isni(self):
        assert validate_isni("0000 0001 2111 6211") == []

    def test_valid_isni_with_x(self):
        assert validate_isni("0000 0004 1936 800X") == []

    def test_invalid_isni(self):
        errors = validate_isni("1234")
        assert len(errors) == 1
        assert "Invalid ISNI" in errors[0]

    def test_empty_isni(self):
        errors = validate_isni("")
        assert len(errors) == 1


class TestValidateWikidata:
    def test_valid_wikidata_id(self):
        assert validate_wikidata("Q6467294") == []

    def test_valid_wikidata_delete(self):
        assert validate_wikidata("delete") == []

    def test_invalid_wikidata(self):
        errors = validate_wikidata("P1234")
        assert len(errors) == 1
        assert "Invalid Wikidata" in errors[0]

    def test_empty_wikidata(self):
        errors = validate_wikidata("")
        assert len(errors) == 1


class TestValidateFundref:
    def test_valid_fundref(self):
        assert validate_fundref("100000001") == []

    def test_valid_fundref_delete(self):
        assert validate_fundref("delete") == []

    def test_invalid_fundref(self):
        errors = validate_fundref("abc")
        assert len(errors) == 1
        assert "Invalid FundRef" in errors[0]

    def test_empty_fundref(self):
        errors = validate_fundref("")
        assert len(errors) == 1


class TestValidateGeonames:
    def test_valid_geonames(self):
        assert validate_geonames("5007400") == []

    def test_invalid_geonames(self):
        errors = validate_geonames("abc")
        assert len(errors) == 1
        assert "Invalid or Null Geonames" in errors[0]

    def test_zero_geonames(self):
        errors = validate_geonames("0")
        assert len(errors) == 1

    def test_empty_geonames(self):
        errors = validate_geonames("")
        assert len(errors) == 1


class TestValidateCity:
    def test_valid_city(self):
        assert validate_city("Rochester") == []

    def test_empty_city(self):
        errors = validate_city("")
        assert len(errors) == 1
        assert "no city" in errors[0]


class TestValidateCountry:
    def test_valid_country(self):
        assert validate_country("US") == []

    def test_empty_country(self):
        errors = validate_country("")
        assert len(errors) == 1
        assert "no country" in errors[0]


class TestValidateFieldValue:
    def test_known_field_valid_value(self):
        assert validate_field_value("status", "active") == []

    def test_known_field_invalid_value(self):
        errors = validate_field_value("status", "closed")
        assert len(errors) >= 1

    def test_unknown_field_returns_empty(self):
        assert validate_field_value("unknown_field", "anything") == []

    def test_field_with_multiple_validators_short_circuits(self):
        errors = validate_field_value("names.types.acronym", "MIT")
        assert len(errors) >= 1

    def test_field_with_multiple_validators_first_fails(self):
        errors = validate_field_value("names.types.acronym", "mit")
        assert len(errors) >= 1
        assert "Potential invalid value" in errors[0]


class TestParseUpdateField:
    def test_simple_replace(self):
        result = parse_update_field("new_value")
        assert result == {"replace": ["new_value"]}

    def test_add_operation(self):
        result = parse_update_field("add==new_value")
        assert result == {"add": ["new_value"]}

    def test_delete_operation(self):
        result = parse_update_field("delete==old_value")
        assert result == {"delete": ["old_value"]}

    def test_multiple_operations(self):
        result = parse_update_field("add==val1;delete==val2")
        assert result == {"add": ["val1"], "delete": ["val2"]}

    def test_multiple_same_type(self):
        result = parse_update_field("add==val1;add==val2")
        assert result == {"add": ["val1", "val2"]}

    def test_mixed_operations_with_replace(self):
        result = parse_update_field("val1;add==val2")
        assert result == {"replace": ["val1"], "add": ["val2"]}


class TestValidateUpdates:
    def test_valid_update(self):
        row = {"status": "active", "types": "education"}
        errors, pairs = validate_updates(row)
        assert errors == []
        assert ("status", "active") in pairs
        assert ("types", "education") in pairs

    def test_empty_fields_skipped(self):
        row = {"status": "", "types": ""}
        errors, pairs = validate_updates(row)
        assert errors == []
        assert pairs == []

    def test_invalid_change_type(self):
        row = {"status": "invalid_op==active"}
        errors, pairs = validate_updates(row)
        assert len(errors) >= 1
        assert "Invalid change type" in errors[0]

    def test_delete_values_skipped(self):
        row = {"types": "delete==education"}
        errors, pairs = validate_updates(row)
        assert errors == []
        assert pairs == []

    def test_add_operation_included(self):
        row = {"types": "add==education"}
        errors, pairs = validate_updates(row)
        assert errors == []
        assert ("types", "education") in pairs

    def test_non_valid_field_ignored(self):
        row = {"unknown_field": "some_value"}
        errors, pairs = validate_updates(row)
        assert errors == []
        assert pairs == []


class TestFieldValidatorsMapping:
    def test_all_expected_fields_present(self):
        expected_fields = [
            "types", "status", "names.types.acronym", "names.types.alias",
            "names.types.label", "names.types.ror_display", "links.type.website",
            "established", "links.type.wikipedia",
            "external_ids.type.isni.preferred", "external_ids.type.isni.all",
            "external_ids.type.wikidata.preferred", "external_ids.type.wikidata.all",
            "external_ids.type.fundref.preferred", "external_ids.type.fundref.all",
            "geonames", "locations.geonames_id", "city", "country",
        ]
        for field in expected_fields:
            assert field in FIELD_VALIDATORS, f"Missing field: {field}"

    def test_acronym_has_two_validators(self):
        assert len(FIELD_VALIDATORS["names.types.acronym"]) == 2

    def test_status_has_one_validator(self):
        assert len(FIELD_VALIDATORS["status"]) == 1


class TestCsvNewRecords:
    def test_valid_new_record_no_errors(self, validator, tmp_path):
        row = _new_csv_row()
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        error_results = [r for r in results if "Error" in r["message"]]
        assert error_results == []

    def test_invalid_status_new(self, validator, tmp_path):
        row = _new_csv_row(status="closed")
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        status_errors = [r for r in results if r["field"] == "status"]
        assert len(status_errors) >= 1
        assert "Invalid value" in status_errors[0]["message"]

    def test_invalid_types_new(self, validator, tmp_path):
        row = _new_csv_row(types="university")
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        type_errors = [r for r in results if r["field"] == "types"]
        assert len(type_errors) >= 1

    def test_invalid_website_new(self, validator, tmp_path):
        row = _new_csv_row(**{"links.type.website": "not-a-url"})
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        link_errors = [r for r in results if r["field"] == "links.type.website"]
        assert len(link_errors) >= 1
        assert "Invalid URL" in link_errors[0]["message"]

    def test_invalid_established_new(self, validator, tmp_path):
        row = _new_csv_row(established="abc")
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        est_errors = [r for r in results if r["field"] == "established"]
        assert len(est_errors) >= 1

    def test_invalid_geonames_new(self, validator, tmp_path):
        row = _new_csv_row(**{"locations.geonames_id": "abc"})
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        geo_errors = [r for r in results if r["field"] == "locations.geonames_id"]
        assert len(geo_errors) >= 1

    def test_invalid_isni_new(self, validator, tmp_path):
        row = _new_csv_row(**{"external_ids.type.isni.all": "bad-isni"})
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        isni_errors = [r for r in results if r["field"] == "external_ids.type.isni.all"]
        assert len(isni_errors) >= 1

    def test_invalid_wikidata_new(self, validator, tmp_path):
        row = _new_csv_row(**{"external_ids.type.wikidata.all": "bad-wikidata"})
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        wiki_errors = [r for r in results if r["field"] == "external_ids.type.wikidata.all"]
        assert len(wiki_errors) >= 1

    def test_invalid_fundref_new(self, validator, tmp_path):
        row = _new_csv_row(**{"external_ids.type.fundref.all": "bad-fundref"})
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        fr_errors = [r for r in results if r["field"] == "external_ids.type.fundref.all"]
        assert len(fr_errors) >= 1

    def test_missing_city_warning(self, validator, tmp_path):
        row = _new_csv_row(city="")
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        city_warnings = [r for r in results if r["field"] == "city"]
        assert len(city_warnings) >= 1
        assert "no city" in city_warnings[0]["message"]

    def test_missing_country_warning(self, validator, tmp_path):
        row = _new_csv_row(country="")
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        country_warnings = [r for r in results if r["field"] == "country"]
        assert len(country_warnings) >= 1
        assert "no country" in country_warnings[0]["message"]

    def test_multiple_errors_new(self, validator, tmp_path):
        row = _new_csv_row(
            status="closed",
            types="university",
            **{"links.type.website": "not-a-url"},
        )
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        error_fields = {r["field"] for r in results if "Error" in r["message"]}
        assert "status" in error_fields
        assert "types" in error_fields
        assert "links.type.website" in error_fields

    def test_record_id_empty_for_new(self, validator, tmp_path):
        row = _new_csv_row(status="closed")
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        assert len(results) >= 1
        assert results[0]["record_id"] == ""

    def test_valid_name_with_language_tag(self, validator, tmp_path):
        row = _new_csv_row(**{"names.types.ror_display": "Test Uni*en"})
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        name_errors = [r for r in results if r["field"] == "names.types.ror_display"]
        assert name_errors == []

    def test_invalid_name_no_language_tag(self, validator, tmp_path):
        row = _new_csv_row(**{"names.types.ror_display": "Test Uni"})
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        name_errors = [r for r in results if r["field"] == "names.types.ror_display"]
        assert len(name_errors) >= 1
        assert "Expected format" in name_errors[0]["message"]

    def test_valid_acronym_new(self, validator, tmp_path):
        row = _new_csv_row(**{"names.types.acronym": "MIT*en"})
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        acro_errors = [r for r in results if r["field"] == "names.types.acronym"]
        assert acro_errors == []

    def test_invalid_wikipedia_url(self, validator, tmp_path):
        row = _new_csv_row(**{"links.type.wikipedia": "https://example.com/wiki"})
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        wp_errors = [r for r in results if r["field"] == "links.type.wikipedia"]
        assert len(wp_errors) >= 1
        assert "Invalid Wikipedia URL" in wp_errors[0]["message"]

    def test_valid_wikipedia_url(self, validator, tmp_path):
        row = _new_csv_row(**{"links.type.wikipedia": "https://en.wikipedia.org/wiki/MIT"})
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        wp_errors = [r for r in results if r["field"] == "links.type.wikipedia"]
        assert wp_errors == []


class TestCsvUpdateRecords:
    def test_valid_update_no_errors(self, validator, tmp_path):
        row = _update_csv_row(status="active", types="education")
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        error_results = [r for r in results if "Error" in r["message"]]
        assert error_results == []

    def test_invalid_status_update(self, validator, tmp_path):
        row = _update_csv_row(status="closed")
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        status_errors = [r for r in results if r["field"] == "status"]
        assert len(status_errors) >= 1

    def test_record_id_in_output(self, validator, tmp_path):
        row = _update_csv_row(status="closed")
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        assert len(results) >= 1
        assert results[0]["record_id"] == "https://ror.org/012345678"

    def test_add_operation_validated(self, validator, tmp_path):
        row = _update_csv_row(
            **{"external_ids.type.isni.all": "add==bad-isni"}
        )
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        isni_errors = [r for r in results if r["field"] == "external_ids.type.isni.all"]
        assert len(isni_errors) >= 1

    def test_delete_operation_not_validated(self, validator, tmp_path):
        row = _update_csv_row(
            **{"external_ids.type.isni.all": "delete==0000 0001 2111 6211"}
        )
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        isni_errors = [r for r in results if r["field"] == "external_ids.type.isni.all"]
        assert isni_errors == []

    def test_invalid_change_type_update(self, validator, tmp_path):
        row = _update_csv_row(status="badop==active")
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        change_type_errors = [r for r in results if "Invalid change type" in r["message"]]
        assert len(change_type_errors) >= 1

    def test_multiple_semicolon_values_update(self, validator, tmp_path):
        row = _update_csv_row(
            **{"external_ids.type.wikidata.all": "add==Q1234;add==bad-id"}
        )
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        wiki_errors = [r for r in results if r["field"] == "external_ids.type.wikidata.all"]
        assert len(wiki_errors) >= 1

    def test_empty_update_fields_no_errors(self, validator, tmp_path):
        row = _update_csv_row()
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        assert results == []

    def test_replace_operation_validated(self, validator, tmp_path):
        row = _update_csv_row(
            **{"links.type.website": "replace==not-a-url"}
        )
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        link_errors = [r for r in results if r["field"] == "links.type.website"]
        assert len(link_errors) >= 1


class TestJsonValidation:
    def test_valid_record_no_errors(self, validator, tmp_path):
        record = _minimal_json_record()
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        assert results == []

    def test_invalid_status_json(self, validator, tmp_path):
        record = _minimal_json_record(status="closed")
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        status_errors = [r for r in results if r["field"] == "status"]
        assert len(status_errors) >= 1
        assert "Invalid value" in status_errors[0]["message"]

    def test_invalid_type_json(self, validator, tmp_path):
        record = _minimal_json_record(types=["university"])
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        type_errors = [r for r in results if r["field"] == "types"]
        assert len(type_errors) >= 1

    def test_invalid_website_json(self, validator, tmp_path):
        record = _minimal_json_record(
            links=[{"type": "website", "value": "not-a-url"}]
        )
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        link_errors = [r for r in results if r["field"] == "links.type.website"]
        assert len(link_errors) >= 1

    def test_invalid_wikipedia_json(self, validator, tmp_path):
        record = _minimal_json_record(
            links=[
                {"type": "website", "value": "https://example.com"},
                {"type": "wikipedia", "value": "https://example.com/not-wiki"},
            ]
        )
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        wp_errors = [r for r in results if r["field"] == "links.type.wikipedia"]
        assert len(wp_errors) >= 1

    def test_invalid_established_json(self, validator, tmp_path):
        record = _minimal_json_record(established=99)
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        est_errors = [r for r in results if r["field"] == "established"]
        assert len(est_errors) >= 1

    def test_invalid_isni_json(self, validator, tmp_path):
        record = _minimal_json_record(
            external_ids=[
                {"type": "isni", "all": ["bad-isni"], "preferred": "bad-isni"}
            ]
        )
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        isni_errors = [r for r in results if "isni" in r["field"]]
        assert len(isni_errors) >= 1

    def test_invalid_wikidata_json(self, validator, tmp_path):
        record = _minimal_json_record(
            external_ids=[
                {"type": "wikidata", "all": ["bad-id"], "preferred": "bad-id"}
            ]
        )
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        wiki_errors = [r for r in results if "wikidata" in r["field"]]
        assert len(wiki_errors) >= 1

    def test_invalid_fundref_json(self, validator, tmp_path):
        record = _minimal_json_record(
            external_ids=[
                {"type": "fundref", "all": ["bad-id"], "preferred": "bad-id"}
            ]
        )
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        fr_errors = [r for r in results if "fundref" in r["field"]]
        assert len(fr_errors) >= 1

    def test_invalid_geonames_json(self, validator, tmp_path):
        record = _minimal_json_record(
            locations=[
                {
                    "geonames_id": 0,
                    "geonames_details": {
                        "name": "City",
                        "country_name": "Country",
                        "country_code": "US",
                        "lat": 42.0,
                        "lng": -83.0,
                    },
                }
            ]
        )
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        geo_errors = [r for r in results if r["field"] == "locations.geonames_id"]
        assert len(geo_errors) >= 1

    def test_record_id_in_json_output(self, validator, tmp_path):
        record = _minimal_json_record(
            id="https://ror.org/099abcdef",
            status="closed",
        )
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        assert len(results) >= 1
        assert results[0]["record_id"] == "https://ror.org/099abcdef"

    def test_multiple_records_json(self, validator, tmp_path):
        records = [
            _minimal_json_record(
                id="https://ror.org/000000001",
                status="closed",
            ),
            _minimal_json_record(
                id="https://ror.org/000000002",
                types=["university"],
            ),
        ]
        ctx = _make_json_ctx(tmp_path, records)
        results = validator.run(ctx)
        record_ids = {r["record_id"] for r in results}
        assert "https://ror.org/000000001" in record_ids
        assert "https://ror.org/000000002" in record_ids

    def test_multiple_types_one_invalid(self, validator, tmp_path):
        record = _minimal_json_record(types=["education", "university"])
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        type_errors = [r for r in results if r["field"] == "types"]
        assert len(type_errors) >= 1

    def test_valid_isni_json(self, validator, tmp_path):
        record = _minimal_json_record(
            external_ids=[
                {
                    "type": "isni",
                    "all": ["0000 0001 2111 6211"],
                    "preferred": "0000 0001 2111 6211",
                }
            ]
        )
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        isni_errors = [r for r in results if "isni" in r["field"]]
        assert isni_errors == []

    def test_valid_wikidata_json(self, validator, tmp_path):
        record = _minimal_json_record(
            external_ids=[
                {
                    "type": "wikidata",
                    "all": ["Q6467294"],
                    "preferred": "Q6467294",
                }
            ]
        )
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        wiki_errors = [r for r in results if "wikidata" in r["field"]]
        assert wiki_errors == []

    def test_null_established_no_error(self, validator, tmp_path):
        record = _minimal_json_record(established=None)
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        est_errors = [r for r in results if r["field"] == "established"]
        assert est_errors == []

    def test_no_external_ids_no_error(self, validator, tmp_path):
        record = _minimal_json_record(external_ids=[])
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        ext_errors = [r for r in results if "external_ids" in r["field"]]
        assert ext_errors == []


class TestJsonNameValidation:
    def test_json_names_not_validated_with_names_pattern(self, validator, tmp_path):
        record = _minimal_json_record(
            names=[
                {"value": "Test University", "types": ["ror_display"], "lang": "en"}
            ]
        )
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        name_errors = [r for r in results if "names" in r["field"]]
        assert name_errors == []

    def test_json_acronym_not_validated_with_names_pattern(self, validator, tmp_path):
        record = _minimal_json_record(
            names=[
                {"value": "MIT", "types": ["acronym"], "lang": "en"},
                {"value": "Test University", "types": ["ror_display"], "lang": "en"},
            ]
        )
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        name_errors = [r for r in results if "names" in r["field"]]
        assert name_errors == []


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

    def test_empty_csv_file(self, validator, tmp_path):
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("id,status\n")
        ctx = ValidatorContext(
            csv_file=csv_file,
            json_dir=None,
            output_dir=tmp_path,
            data_source=None,
            geonames_user=None,
        )
        results = validator.run(ctx)
        assert results == []

    def test_csv_preferred_over_json_when_both_set(self, validator, tmp_path):
        json_dir = tmp_path / "json"
        json_dir.mkdir()
        record = _minimal_json_record(status="closed")
        filename = "012345678.json"
        (json_dir / filename).write_text(json.dumps(record))

        csv_file = tmp_path / "input.csv"
        csv_file.write_text("id,status\nhttps://ror.org/012345678,active\n")

        ctx = ValidatorContext(
            csv_file=csv_file,
            json_dir=json_dir,
            output_dir=tmp_path,
            data_source=None,
            geonames_user=None,
        )
        results = validator.run(ctx)
        status_errors = [r for r in results if r["field"] == "status"]
        assert len(status_errors) >= 1

    def test_multiple_csv_rows(self, validator, tmp_path):
        rows = [
            _new_csv_row(status="closed"),
            _new_csv_row(status="invalid"),
        ]
        ctx = _make_csv_ctx(tmp_path, rows)
        results = validator.run(ctx)
        status_errors = [r for r in results if r["field"] == "status"]
        assert len(status_errors) >= 2

    def test_semicolon_separated_csv_values(self, validator, tmp_path):
        row = _new_csv_row(
            **{"external_ids.type.wikidata.all": "Q1234;bad-id"}
        )
        ctx = _make_csv_ctx(tmp_path, [row])
        results = validator.run(ctx)
        wiki_errors = [r for r in results if r["field"] == "external_ids.type.wikidata.all"]
        assert len(wiki_errors) >= 1
