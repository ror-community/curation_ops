import csv
import json
from pathlib import Path

import pytest

from curation_validation.validators.base import ValidatorContext
from curation_validation.validators.leading_trailing import (
    LeadingTrailingValidator,
    WHITESPACE_AND_PUNCTUATION,
)


@pytest.fixture
def validator():
    return LeadingTrailingValidator()


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


class TestValidatorProperties:
    def test_name(self, validator):
        assert validator.name == "leading_trailing"

    def test_supported_formats(self, validator):
        assert validator.supported_formats == {"csv", "json"}

    def test_output_filename(self, validator):
        assert validator.output_filename == "leading_trailing.csv"

    def test_output_fields(self, validator):
        assert validator.output_fields == ["issue_url", "record_id", "field", "value", "issue"]


class TestPunctuationSet:
    def test_contains_space(self):
        assert " " in WHITESPACE_AND_PUNCTUATION

    def test_contains_tab(self):
        assert "\t" in WHITESPACE_AND_PUNCTUATION

    def test_contains_newline(self):
        assert "\n" in WHITESPACE_AND_PUNCTUATION

    def test_contains_punctuation_marks(self):
        for ch in "!#$%&*+,-./:;<=>?@\\^_`{|}~":
            assert ch in WHITESPACE_AND_PUNCTUATION, f"Missing: {ch!r}"

    def test_contains_carriage_return(self):
        assert "\r" in WHITESPACE_AND_PUNCTUATION

    def test_contains_vertical_tab(self):
        assert "\v" in WHITESPACE_AND_PUNCTUATION

    def test_contains_form_feed(self):
        assert "\f" in WHITESPACE_AND_PUNCTUATION

    def test_does_not_contain_letters(self):
        assert "a" not in WHITESPACE_AND_PUNCTUATION
        assert "Z" not in WHITESPACE_AND_PUNCTUATION

    def test_does_not_contain_digits(self):
        assert "0" not in WHITESPACE_AND_PUNCTUATION
        assert "9" not in WHITESPACE_AND_PUNCTUATION


class TestJsonValidation:
    def test_detects_leading_space(self, validator, tmp_path):
        record = {
            "id": "https://ror.org/012345678",
            "names": [
                {"value": " Leading Space Org", "types": ["ror_display"], "lang": "en"}
            ],
            "status": "active",
            "types": ["education"],
            "links": [],
            "external_ids": [],
            "locations": [],
            "relationships": [],
            "domains": [],
            "established": 2000,
            "admin": {},
        }
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        assert len(results) >= 1
        leading_results = [r for r in results if r["issue"] == "leading"]
        assert any(
            r["value"] == " Leading Space Org" for r in leading_results
        )

    def test_detects_trailing_space(self, validator, tmp_path):
        record = {
            "id": "https://ror.org/012345678",
            "names": [
                {"value": "Trailing Space Org ", "types": ["ror_display"], "lang": "en"}
            ],
            "status": "active",
            "types": ["education"],
            "links": [],
            "external_ids": [],
            "locations": [],
            "relationships": [],
            "domains": [],
            "established": 2000,
            "admin": {},
        }
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        assert len(results) >= 1
        trailing_results = [r for r in results if r["issue"] == "trailing"]
        assert any(
            r["value"] == "Trailing Space Org " for r in trailing_results
        )

    def test_detects_leading_punctuation(self, validator, tmp_path):
        record = {
            "id": "https://ror.org/012345678",
            "names": [
                {"value": ".Dot Leading", "types": ["ror_display"], "lang": "en"}
            ],
            "status": "active",
            "types": ["education"],
            "links": [],
            "external_ids": [],
            "locations": [],
            "relationships": [],
            "domains": [],
            "established": 2000,
            "admin": {},
        }
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        leading_results = [r for r in results if r["issue"] == "leading"]
        assert any(r["value"] == ".Dot Leading" for r in leading_results)

    def test_detects_trailing_punctuation(self, validator, tmp_path):
        record = {
            "id": "https://ror.org/012345678",
            "names": [
                {"value": "Trailing Punctuation!", "types": ["ror_display"], "lang": "en"}
            ],
            "status": "active",
            "types": ["education"],
            "links": [],
            "external_ids": [],
            "locations": [],
            "relationships": [],
            "domains": [],
            "established": 2000,
            "admin": {},
        }
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        trailing_results = [r for r in results if r["issue"] == "trailing"]
        assert any(
            r["value"] == "Trailing Punctuation!" for r in trailing_results
        )

    def test_detects_both_leading_and_trailing(self, validator, tmp_path):
        record = {
            "id": "https://ror.org/012345678",
            "names": [
                {"value": " Both Issues! ", "types": ["ror_display"], "lang": "en"}
            ],
            "status": "active",
            "types": ["education"],
            "links": [],
            "external_ids": [],
            "locations": [],
            "relationships": [],
            "domains": [],
            "established": 2000,
            "admin": {},
        }
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        issues = {r["issue"] for r in results if " Both Issues! " in r["value"]}
        assert "leading" in issues
        assert "trailing" in issues

    def test_ignores_clean_values(self, validator, tmp_path):
        record = {
            "id": "https://ror.org/012345678",
            "names": [
                {"value": "Clean University Name", "types": ["ror_display"], "lang": "en"}
            ],
            "status": "active",
            "types": ["education"],
            "links": [
                {"type": "website", "value": "https://example.com"}
            ],
            "external_ids": [],
            "locations": [
                {
                    "geonames_id": 1234567,
                    "geonames_details": {
                        "name": "City",
                        "country_name": "Country",
                        "country_code": "XX",
                        "lat": 0.0,
                        "lng": 0.0,
                    },
                }
            ],
            "relationships": [],
            "domains": ["example.com"],
            "established": 2000,
            "admin": {},
        }
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        assert len(results) == 0

    def test_ignores_empty_strings(self, validator, tmp_path):
        record = {
            "id": "https://ror.org/012345678",
            "names": [
                {"value": "", "types": ["ror_display"], "lang": "en"}
            ],
            "status": "active",
            "types": ["education"],
            "links": [],
            "external_ids": [],
            "locations": [],
            "relationships": [],
            "domains": [],
            "established": 2000,
            "admin": {},
        }
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        assert len(results) == 0

    def test_ignores_non_string_values(self, validator, tmp_path):
        record = {
            "id": "https://ror.org/012345678",
            "names": [
                {"value": "Clean Name", "types": ["ror_display"], "lang": "en"}
            ],
            "status": "active",
            "types": ["education"],
            "links": [],
            "external_ids": [],
            "locations": [
                {
                    "geonames_id": 1234567,
                    "geonames_details": {
                        "name": "City",
                        "country_name": "Country",
                        "lat": 42.0,
                        "lng": -71.0,
                    },
                }
            ],
            "relationships": [],
            "domains": [],
            "established": 2000,
            "admin": {},
        }
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        assert len(results) == 0

    def test_record_id_in_output(self, validator, tmp_path):
        record = {
            "id": "https://ror.org/099abcdef",
            "names": [
                {"value": " BadName", "types": ["ror_display"], "lang": "en"}
            ],
            "status": "active",
            "types": ["education"],
            "links": [],
            "external_ids": [],
            "locations": [],
            "relationships": [],
            "domains": [],
            "established": 2000,
            "admin": {},
        }
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        assert len(results) >= 1
        assert results[0]["record_id"] == "https://ror.org/099abcdef"

    def test_multiple_records(self, validator, tmp_path):
        records = [
            {
                "id": "https://ror.org/000000001",
                "names": [
                    {"value": " LeadingSpace", "types": ["ror_display"], "lang": "en"}
                ],
                "status": "active",
                "types": ["education"],
                "links": [],
                "external_ids": [],
                "locations": [],
                "relationships": [],
                "domains": [],
                "established": 2000,
                "admin": {},
            },
            {
                "id": "https://ror.org/000000002",
                "names": [
                    {"value": "TrailingPunct!", "types": ["ror_display"], "lang": "en"}
                ],
                "status": "active",
                "types": ["education"],
                "links": [],
                "external_ids": [],
                "locations": [],
                "relationships": [],
                "domains": [],
                "established": 2000,
                "admin": {},
            },
        ]
        ctx = _make_json_ctx(tmp_path, records)
        results = validator.run(ctx)
        record_ids = {r["record_id"] for r in results}
        assert "https://ror.org/000000001" in record_ids
        assert "https://ror.org/000000002" in record_ids

    def test_various_punctuation_chars(self, validator, tmp_path):
        test_chars = ["!", "#", "$", "%", "&", "*", "+", ",", "-", ".",
                       "/", ":", ";", "<", "=", ">", "?", "@", "\\",
                       "^", "_", "`", "{", "|", "}", "~"]
        records = []
        for i, ch in enumerate(test_chars):
            records.append({
                "id": f"https://ror.org/{i:09d}",
                "names": [
                    {"value": f"{ch}Leading", "types": ["ror_display"], "lang": "en"}
                ],
                "status": "active",
                "types": ["education"],
                "links": [],
                "external_ids": [],
                "locations": [],
                "relationships": [],
                "domains": [],
                "established": 2000,
                "admin": {},
            })
        ctx = _make_json_ctx(tmp_path, records)
        results = validator.run(ctx)
        detected_ids = {r["record_id"] for r in results}
        for i in range(len(test_chars)):
            assert f"https://ror.org/{i:09d}" in detected_ids, \
                f"Failed to detect leading {test_chars[i]!r}"

    def test_whitespace_chars_detected(self, validator, tmp_path):
        record = {
            "id": "https://ror.org/012345678",
            "names": [
                {"value": "\tTabbed Name", "types": ["ror_display"], "lang": "en"},
                {"value": "Newline Name\n", "types": ["alias"], "lang": "en"},
            ],
            "status": "active",
            "types": ["education"],
            "links": [],
            "external_ids": [],
            "locations": [],
            "relationships": [],
            "domains": [],
            "established": 2000,
            "admin": {},
        }
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        assert len(results) >= 2
        issues = [(r["value"], r["issue"]) for r in results]
        assert ("\tTabbed Name", "leading") in issues
        assert ("Newline Name\n", "trailing") in issues


class TestCsvValidation:
    def test_detects_leading_punctuation_csv(self, validator, tmp_path):
        rows = [
            {
                "id": "https://ror.org/012345678",
                "names.types.ror_display": ".Leading Dot Org",
                "status": "active",
                "types": "education",
                "names.types.acronym": "",
                "names.types.alias": "",
                "names.types.label": "",
                "links.type.website": "",
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
        ]
        ctx = _make_csv_ctx(tmp_path, rows)
        results = validator.run(ctx)
        leading_results = [r for r in results if r["issue"] == "leading"]
        assert len(leading_results) >= 1
        assert any(".Leading Dot Org" in r["value"] for r in leading_results)

    def test_csv_whitespace_stripped_by_extraction(self, validator, tmp_path):
        rows = [
            {
                "id": "https://ror.org/012345678",
                "names.types.ror_display": " Whitespace Org ",
                "status": "active",
                "types": "education",
                "names.types.acronym": "",
                "names.types.alias": "",
                "names.types.label": "",
                "links.type.website": "",
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
        ]
        ctx = _make_csv_ctx(tmp_path, rows)
        results = validator.run(ctx)
        assert len(results) == 0

    def test_detects_trailing_punctuation_csv(self, validator, tmp_path):
        rows = [
            {
                "id": "https://ror.org/012345678",
                "names.types.ror_display": "Trailing Punc!",
                "status": "active",
                "types": "education",
                "names.types.acronym": "",
                "names.types.alias": "",
                "names.types.label": "",
                "links.type.website": "",
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
        ]
        ctx = _make_csv_ctx(tmp_path, rows)
        results = validator.run(ctx)
        trailing_results = [r for r in results if r["issue"] == "trailing"]
        assert len(trailing_results) >= 1
        assert any("Trailing Punc!" in r["value"] for r in trailing_results)

    def test_ignores_clean_csv_values(self, validator, tmp_path):
        rows = [
            {
                "id": "https://ror.org/012345678",
                "names.types.ror_display": "Clean Name",
                "status": "active",
                "types": "education",
                "names.types.acronym": "CN",
                "names.types.alias": "",
                "names.types.label": "Clean Name",
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
        ]
        ctx = _make_csv_ctx(tmp_path, rows)
        results = validator.run(ctx)
        assert len(results) == 0

    def test_handles_empty_csv_values(self, validator, tmp_path):
        rows = [
            {
                "id": "https://ror.org/012345678",
                "names.types.ror_display": "",
                "status": "",
                "types": "",
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
        ]
        ctx = _make_csv_ctx(tmp_path, rows)
        results = validator.run(ctx)
        assert len(results) == 0

    def test_csv_record_id_in_output(self, validator, tmp_path):
        rows = [
            {
                "id": "https://ror.org/099abcdef",
                "names.types.ror_display": ".Bad",
                "status": "active",
                "types": "education",
                "names.types.acronym": "",
                "names.types.alias": "",
                "names.types.label": "",
                "links.type.website": "",
                "links.type.wikipedia": "",
                "established": "2000",
                "external_ids.type.isni.all": "",
                "external_ids.type.isni.preferred": "",
                "external_ids.type.wikidata.all": "",
                "external_ids.type.wikidata.preferred": "",
                "external_ids.type.fundref.all": "",
                "external_ids.type.fundref.preferred": "",
                "locations.geonames_id": "",
                "domains": "",
            }
        ]
        ctx = _make_csv_ctx(tmp_path, rows)
        results = validator.run(ctx)
        assert len(results) >= 1
        assert results[0]["record_id"] == "https://ror.org/099abcdef"

    def test_csv_semicolon_separated_values_checked(self, validator, tmp_path):
        rows = [
            {
                "id": "https://ror.org/012345678",
                "names.types.ror_display": "Clean Name",
                "status": "active",
                "types": "education",
                "names.types.acronym": "",
                "names.types.alias": "Good Alias; Bad Alias!",
                "names.types.label": "",
                "links.type.website": "",
                "links.type.wikipedia": "",
                "established": "2000",
                "external_ids.type.isni.all": "",
                "external_ids.type.isni.preferred": "",
                "external_ids.type.wikidata.all": "",
                "external_ids.type.wikidata.preferred": "",
                "external_ids.type.fundref.all": "",
                "external_ids.type.fundref.preferred": "",
                "locations.geonames_id": "",
                "domains": "",
            }
        ]
        ctx = _make_csv_ctx(tmp_path, rows)
        results = validator.run(ctx)
        trailing_results = [r for r in results if r["issue"] == "trailing"]
        assert any("Bad Alias!" in r["value"] for r in trailing_results)


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

    def test_single_char_value_leading(self, validator, tmp_path):
        record = {
            "id": "https://ror.org/012345678",
            "names": [
                {"value": "!", "types": ["ror_display"], "lang": "en"}
            ],
            "status": "active",
            "types": ["education"],
            "links": [],
            "external_ids": [],
            "locations": [],
            "relationships": [],
            "domains": [],
            "established": 2000,
            "admin": {},
        }
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        issues = {r["issue"] for r in results if r["value"] == "!"}
        assert "leading" in issues
        assert "trailing" in issues

    def test_handles_none_values_in_json(self, validator, tmp_path):
        record = {
            "id": "https://ror.org/012345678",
            "names": [
                {"value": "Clean Name", "types": ["ror_display"], "lang": None}
            ],
            "status": "active",
            "types": ["education"],
            "links": [],
            "external_ids": [],
            "locations": [],
            "relationships": [],
            "domains": [],
            "established": None,
            "admin": {},
        }
        ctx = _make_json_ctx(tmp_path, [record])
        results = validator.run(ctx)
        assert len(results) == 0
