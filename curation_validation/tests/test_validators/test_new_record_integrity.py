import csv
import json
from pathlib import Path

import pytest

from curation_validation.validators.base import ValidatorContext
from curation_validation.validators.new_record_integrity import (
    NewRecordIntegrityValidator,
    ROR_DATA_FIELDS,
)


def _make_json_file(json_dir, ror_id_suffix, record):
    (json_dir / f"{ror_id_suffix}.json").write_text(
        json.dumps(record), encoding="utf-8"
    )


def _make_ctx(tmp_path, csv_rows, json_records):
    csv_file = tmp_path / "input.csv"
    if csv_rows:
        fieldnames = list(csv_rows[0].keys())
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_rows)
    else:
        csv_file.write_text("id\n", encoding="utf-8")

    json_dir = tmp_path / "json"
    json_dir.mkdir(parents=True, exist_ok=True)
    for suffix, record in json_records.items():
        _make_json_file(json_dir, suffix, record)

    return ValidatorContext(
        csv_file=csv_file,
        json_dir=json_dir,
        output_dir=tmp_path / "output",
        data_source=None,
        geonames_user=None,
    )


def _minimal_csv_row(ror_id="https://ror.org/00test123", **overrides):
    row = {"id": ror_id}
    for field in ROR_DATA_FIELDS:
        row[field] = ""
    row.update(overrides)
    return row


def _minimal_json_record(**overrides):
    record = {
        "status": "active",
        "types": ["education"],
        "names": [
            {"value": "Test University", "types": ["ror_display"]},
        ],
        "links": [],
        "external_ids": [],
        "locations": [
            {"geonames_id": 5128581},
        ],
        "established": 1900,
    }
    record.update(overrides)
    return record


class TestNewRecordIntegrityValidatorMetadata:
    def test_name(self):
        v = NewRecordIntegrityValidator()
        assert v.name == "new-record-integrity"

    def test_supported_formats(self):
        v = NewRecordIntegrityValidator()
        assert v.supported_formats == {"csv_json"}

    def test_output_filename(self):
        v = NewRecordIntegrityValidator()
        assert v.output_filename == "new_record_integrity.csv"

    def test_output_fields(self):
        v = NewRecordIntegrityValidator()
        assert v.output_fields == ["issue_url", "id", "type", "field", "value"]

    def test_does_not_require_data_source(self):
        v = NewRecordIntegrityValidator()
        assert v.requires_data_source is False

    def test_does_not_require_geonames(self):
        v = NewRecordIntegrityValidator()
        assert v.requires_geonames is False

    def test_can_run_always(self, tmp_path):
        v = NewRecordIntegrityValidator()
        ctx = ValidatorContext(
            csv_file=None,
            json_dir=None,
            output_dir=tmp_path,
            data_source=None,
            geonames_user=None,
        )
        can, _ = v.can_run(ctx)
        assert can is True


class TestValidRecords:
    def test_matching_single_value_fields(self, tmp_path):
        json_record = _minimal_json_record()
        csv_row = _minimal_csv_row(
            **{
                "status": "active",
                "types": "education",
                "names.types.ror_display": "Test University",
                "established": "1900",
                "locations.geonames_id": "5128581",
            }
        )
        ctx = _make_ctx(
            tmp_path,
            [csv_row],
            {"00test123": json_record},
        )
        v = NewRecordIntegrityValidator()
        results = v.run(ctx)
        assert results == []

    def test_empty_csv_fields_no_errors(self, tmp_path):
        json_record = _minimal_json_record()
        csv_row = _minimal_csv_row()
        ctx = _make_ctx(
            tmp_path,
            [csv_row],
            {"00test123": json_record},
        )
        v = NewRecordIntegrityValidator()
        results = v.run(ctx)
        assert results == []

    def test_multiple_valid_records(self, tmp_path):
        json1 = _minimal_json_record()
        json2 = _minimal_json_record(
            status="active",
            types=["facility"],
            names=[{"value": "Org Two", "types": ["ror_display"]}],
            established=2000,
            locations=[{"geonames_id": 1234567}],
        )
        row1 = _minimal_csv_row(
            ror_id="https://ror.org/00test111",
            status="active",
            types="education",
            **{"names.types.ror_display": "Test University"},
        )
        row2 = _minimal_csv_row(
            ror_id="https://ror.org/00test222",
            status="active",
            types="facility",
            **{"names.types.ror_display": "Org Two"},
        )
        ctx = _make_ctx(
            tmp_path,
            [row1, row2],
            {"00test111": json1, "00test222": json2},
        )
        v = NewRecordIntegrityValidator()
        results = v.run(ctx)
        assert results == []


class TestMissingValues:
    def test_missing_single_value(self, tmp_path):
        json_record = _minimal_json_record()
        csv_row = _minimal_csv_row(
            **{"names.types.ror_display": "Nonexistent University"}
        )
        ctx = _make_ctx(
            tmp_path,
            [csv_row],
            {"00test123": json_record},
        )
        v = NewRecordIntegrityValidator()
        results = v.run(ctx)
        assert len(results) >= 1
        missing = [r for r in results if r["type"] == "missing"]
        assert len(missing) >= 1
        assert missing[0]["field"] == "names.types.ror_display"
        assert missing[0]["value"] == "Nonexistent University"

    def test_missing_status(self, tmp_path):
        json_record = _minimal_json_record(status="active")
        csv_row = _minimal_csv_row(status="inactive")
        ctx = _make_ctx(
            tmp_path,
            [csv_row],
            {"00test123": json_record},
        )
        v = NewRecordIntegrityValidator()
        results = v.run(ctx)
        missing = [r for r in results if r["type"] == "missing"]
        assert len(missing) >= 1
        assert any(r["field"] == "status" for r in missing)

    def test_missing_external_id(self, tmp_path):
        json_record = _minimal_json_record(external_ids=[
            {"type": "isni", "all": ["0000 0001 2222 3333"], "preferred": "0000 0001 2222 3333"}
        ])
        csv_row = _minimal_csv_row(
            **{"external_ids.type.isni.preferred": "9999 9999 9999 9999"}
        )
        ctx = _make_ctx(
            tmp_path,
            [csv_row],
            {"00test123": json_record},
        )
        v = NewRecordIntegrityValidator()
        results = v.run(ctx)
        missing = [r for r in results if r["type"] == "missing"]
        assert len(missing) >= 1


class TestTranspositions:
    def test_transposition_name_in_wrong_field(self, tmp_path):
        json_record = _minimal_json_record(
            names=[
                {"value": "Main Name", "types": ["ror_display"]},
                {"value": "Alias Name", "types": ["alias"]},
            ]
        )
        csv_row = _minimal_csv_row(
            **{"names.types.ror_display": "Alias Name"}
        )
        ctx = _make_ctx(
            tmp_path,
            [csv_row],
            {"00test123": json_record},
        )
        v = NewRecordIntegrityValidator()
        results = v.run(ctx)
        transpositions = [r for r in results if r["type"] == "transposition"]
        assert len(transpositions) >= 1
        assert transpositions[0]["field"] == "names.types.ror_display"
        assert transpositions[0]["value"] == "Alias Name"

    def test_transposition_external_id_wrong_type(self, tmp_path):
        json_record = _minimal_json_record(external_ids=[
            {
                "type": "isni",
                "all": ["0000 0001 2222 3333"],
                "preferred": "0000 0001 2222 3333",
            },
            {
                "type": "wikidata",
                "all": ["Q123456"],
                "preferred": "Q123456",
            },
        ])
        csv_row = _minimal_csv_row(
            **{"external_ids.type.isni.preferred": "Q123456"}
        )
        ctx = _make_ctx(
            tmp_path,
            [csv_row],
            {"00test123": json_record},
        )
        v = NewRecordIntegrityValidator()
        results = v.run(ctx)
        transpositions = [r for r in results if r["type"] == "transposition"]
        assert len(transpositions) >= 1
        assert transpositions[0]["field"] == "external_ids.type.isni.preferred"

    def test_transposition_website_in_wikipedia(self, tmp_path):
        json_record = _minimal_json_record(
            links=[
                {"type": "website", "value": "https://example.com"},
                {"type": "wikipedia", "value": "https://en.wikipedia.org/wiki/Example"},
            ],
        )
        csv_row = _minimal_csv_row(
            **{"links.type.wikipedia": "https://example.com"}
        )
        ctx = _make_ctx(
            tmp_path,
            [csv_row],
            {"00test123": json_record},
        )
        v = NewRecordIntegrityValidator()
        results = v.run(ctx)
        transpositions = [r for r in results if r["type"] == "transposition"]
        assert len(transpositions) >= 1
        assert transpositions[0]["field"] == "links.type.wikipedia"


class TestMultiValueFields:
    def test_semicolon_separated_values_all_valid(self, tmp_path):
        json_record = _minimal_json_record(
            names=[
                {"value": "Main Name", "types": ["ror_display"]},
                {"value": "Alias One", "types": ["alias"]},
                {"value": "Alias Two", "types": ["alias"]},
            ]
        )
        csv_row = _minimal_csv_row(
            **{"names.types.alias": "Alias One;Alias Two"}
        )
        ctx = _make_ctx(
            tmp_path,
            [csv_row],
            {"00test123": json_record},
        )
        v = NewRecordIntegrityValidator()
        results = v.run(ctx)
        alias_issues = [r for r in results if r["field"] == "names.types.alias"]
        assert alias_issues == []

    def test_semicolon_separated_one_missing(self, tmp_path):
        json_record = _minimal_json_record(
            names=[
                {"value": "Main Name", "types": ["ror_display"]},
                {"value": "Alias One", "types": ["alias"]},
            ]
        )
        csv_row = _minimal_csv_row(
            **{"names.types.alias": "Alias One;Missing Alias"}
        )
        ctx = _make_ctx(
            tmp_path,
            [csv_row],
            {"00test123": json_record},
        )
        v = NewRecordIntegrityValidator()
        results = v.run(ctx)
        missing = [r for r in results if r["type"] == "missing"]
        assert len(missing) >= 1
        assert any(r["value"] == "Missing Alias" for r in missing)

    def test_semicolon_with_asterisk_suffix_stripped(self, tmp_path):
        json_record = _minimal_json_record(
            names=[
                {"value": "Main Name", "types": ["ror_display"]},
                {"value": "Label Fr", "types": ["label"]},
                {"value": "Label De", "types": ["label"]},
            ]
        )
        csv_row = _minimal_csv_row(
            **{"names.types.label": "Label Fr*fr;Label De*de"}
        )
        ctx = _make_ctx(
            tmp_path,
            [csv_row],
            {"00test123": json_record},
        )
        v = NewRecordIntegrityValidator()
        results = v.run(ctx)
        label_issues = [r for r in results if r["field"] == "names.types.label"]
        assert label_issues == []

    def test_single_value_with_asterisk(self, tmp_path):
        json_record = _minimal_json_record(
            names=[
                {"value": "Main Name", "types": ["ror_display"]},
                {"value": "Label Fr", "types": ["label"]},
            ]
        )
        csv_row = _minimal_csv_row(
            **{"names.types.label": "Label Fr*fr"}
        )
        ctx = _make_ctx(
            tmp_path,
            [csv_row],
            {"00test123": json_record},
        )
        v = NewRecordIntegrityValidator()
        results = v.run(ctx)
        label_issues = [r for r in results if r["field"] == "names.types.label"]
        assert label_issues == []

    def test_semicolon_separated_external_ids(self, tmp_path):
        json_record = _minimal_json_record(external_ids=[
            {
                "type": "isni",
                "all": ["0000 0001 1111 1111", "0000 0001 2222 2222"],
                "preferred": "0000 0001 1111 1111",
            }
        ])
        csv_row = _minimal_csv_row(
            **{"external_ids.type.isni.all": "0000 0001 1111 1111;0000 0001 2222 2222"}
        )
        ctx = _make_ctx(
            tmp_path,
            [csv_row],
            {"00test123": json_record},
        )
        v = NewRecordIntegrityValidator()
        results = v.run(ctx)
        isni_issues = [r for r in results if r["field"] == "external_ids.type.isni.all"]
        assert isni_issues == []


class TestIntegerFields:
    def test_established_matches(self, tmp_path):
        json_record = _minimal_json_record(established=1970)
        csv_row = _minimal_csv_row(established="1970")
        ctx = _make_ctx(
            tmp_path,
            [csv_row],
            {"00test123": json_record},
        )
        v = NewRecordIntegrityValidator()
        results = v.run(ctx)
        est_issues = [r for r in results if r["field"] == "established"]
        assert est_issues == []

    def test_established_mismatch_missing(self, tmp_path):
        json_record = _minimal_json_record(established=1970)
        csv_row = _minimal_csv_row(established="2020")
        ctx = _make_ctx(
            tmp_path,
            [csv_row],
            {"00test123": json_record},
        )
        v = NewRecordIntegrityValidator()
        results = v.run(ctx)
        missing = [r for r in results if r["type"] == "missing" and r["field"] == "established"]
        assert len(missing) >= 1

    def test_geonames_id_matches(self, tmp_path):
        json_record = _minimal_json_record(
            locations=[{"geonames_id": 5128581}]
        )
        csv_row = _minimal_csv_row(**{"locations.geonames_id": "5128581"})
        ctx = _make_ctx(
            tmp_path,
            [csv_row],
            {"00test123": json_record},
        )
        v = NewRecordIntegrityValidator()
        results = v.run(ctx)
        geo_issues = [r for r in results if r["field"] == "locations.geonames_id"]
        assert geo_issues == []

    def test_geonames_id_mismatch_missing(self, tmp_path):
        json_record = _minimal_json_record(
            locations=[{"geonames_id": 5128581}]
        )
        csv_row = _minimal_csv_row(**{"locations.geonames_id": "9999999"})
        ctx = _make_ctx(
            tmp_path,
            [csv_row],
            {"00test123": json_record},
        )
        v = NewRecordIntegrityValidator()
        results = v.run(ctx)
        missing = [r for r in results if r["type"] == "missing" and r["field"] == "locations.geonames_id"]
        assert len(missing) >= 1

    def test_multiple_geonames_ids_semicolon(self, tmp_path):
        json_record = _minimal_json_record(
            locations=[
                {"geonames_id": 1111111},
                {"geonames_id": 2222222},
            ]
        )
        csv_row = _minimal_csv_row(**{"locations.geonames_id": "1111111;2222222"})
        ctx = _make_ctx(
            tmp_path,
            [csv_row],
            {"00test123": json_record},
        )
        v = NewRecordIntegrityValidator()
        results = v.run(ctx)
        geo_issues = [r for r in results if r["field"] == "locations.geonames_id"]
        assert geo_issues == []


class TestWikipediaUrlNormalization:
    def test_encoded_wikipedia_url_matches(self, tmp_path):
        wiki_url = "https://en.wikipedia.org/wiki/Laboratory_for_Laser_Energetics"
        json_record = _minimal_json_record(
            links=[
                {"type": "wikipedia", "value": wiki_url},
            ]
        )
        csv_row = _minimal_csv_row(
            **{"links.type.wikipedia": wiki_url}
        )
        ctx = _make_ctx(
            tmp_path,
            [csv_row],
            {"00test123": json_record},
        )
        v = NewRecordIntegrityValidator()
        results = v.run(ctx)
        wiki_issues = [r for r in results if r["field"] == "links.type.wikipedia"]
        assert wiki_issues == []

    def test_percent_encoded_wikipedia_url(self, tmp_path):
        json_record = _minimal_json_record(
            links=[
                {"type": "wikipedia", "value": "https://en.wikipedia.org/wiki/S%C3%A3o_Paulo"},
            ]
        )
        csv_row = _minimal_csv_row(
            **{"links.type.wikipedia": "https://en.wikipedia.org/wiki/S%C3%A3o_Paulo"}
        )
        ctx = _make_ctx(
            tmp_path,
            [csv_row],
            {"00test123": json_record},
        )
        v = NewRecordIntegrityValidator()
        results = v.run(ctx)
        wiki_issues = [r for r in results if r["field"] == "links.type.wikipedia"]
        assert wiki_issues == []

    def test_multiple_wikipedia_urls_semicolon(self, tmp_path):
        json_record = _minimal_json_record(
            links=[
                {"type": "wikipedia", "value": "https://en.wikipedia.org/wiki/Foo"},
                {"type": "wikipedia", "value": "https://en.wikipedia.org/wiki/Bar"},
            ]
        )
        csv_row = _minimal_csv_row(
            **{"links.type.wikipedia": "https://en.wikipedia.org/wiki/Foo;https://en.wikipedia.org/wiki/Bar"}
        )
        ctx = _make_ctx(
            tmp_path,
            [csv_row],
            {"00test123": json_record},
        )
        v = NewRecordIntegrityValidator()
        results = v.run(ctx)
        wiki_issues = [r for r in results if r["field"] == "links.type.wikipedia"]
        assert wiki_issues == []

    def test_wikipedia_url_mismatch(self, tmp_path):
        json_record = _minimal_json_record(
            links=[
                {"type": "wikipedia", "value": "https://en.wikipedia.org/wiki/Correct"},
            ]
        )
        csv_row = _minimal_csv_row(
            **{"links.type.wikipedia": "https://en.wikipedia.org/wiki/Wrong"}
        )
        ctx = _make_ctx(
            tmp_path,
            [csv_row],
            {"00test123": json_record},
        )
        v = NewRecordIntegrityValidator()
        results = v.run(ctx)
        missing = [r for r in results if r["type"] == "missing" and r["field"] == "links.type.wikipedia"]
        assert len(missing) >= 1


class TestOutputFormat:
    def test_output_contains_required_fields(self, tmp_path):
        json_record = _minimal_json_record()
        csv_row = _minimal_csv_row(
            **{"names.types.ror_display": "Wrong Name"}
        )
        ctx = _make_ctx(
            tmp_path,
            [csv_row],
            {"00test123": json_record},
        )
        v = NewRecordIntegrityValidator()
        results = v.run(ctx)
        assert len(results) >= 1
        for r in results:
            assert "id" in r
            assert "type" in r
            assert "field" in r
            assert "value" in r

    def test_id_field_is_full_ror_id(self, tmp_path):
        json_record = _minimal_json_record()
        csv_row = _minimal_csv_row(
            ror_id="https://ror.org/00test123",
            **{"names.types.ror_display": "Wrong Name"}
        )
        ctx = _make_ctx(
            tmp_path,
            [csv_row],
            {"00test123": json_record},
        )
        v = NewRecordIntegrityValidator()
        results = v.run(ctx)
        assert results[0]["id"] == "https://ror.org/00test123"


class TestUrlDecoding:
    def test_url_encoded_csv_value_decoded(self, tmp_path):
        json_record = _minimal_json_record(
            links=[
                {"type": "website", "value": "https://example.com/path with spaces"},
            ]
        )
        csv_row = _minimal_csv_row(
            **{"links.type.website": "https://example.com/path%20with%20spaces"}
        )
        ctx = _make_ctx(
            tmp_path,
            [csv_row],
            {"00test123": json_record},
        )
        v = NewRecordIntegrityValidator()
        results = v.run(ctx)
        website_issues = [r for r in results if r["field"] == "links.type.website"]
        assert website_issues == []


class TestRorDataFields:
    def test_contains_all_expected_fields(self):
        expected = [
            'status',
            'types',
            'names.types.acronym',
            'names.types.alias',
            'names.types.label',
            'names.types.ror_display',
            'links.type.website',
            'established',
            'links.type.wikipedia',
            'external_ids.type.isni.preferred',
            'external_ids.type.isni.all',
            'external_ids.type.wikidata.preferred',
            'external_ids.type.wikidata.all',
            'external_ids.type.fundref.preferred',
            'external_ids.type.fundref.all',
            'locations.geonames_id',
        ]
        assert ROR_DATA_FIELDS == expected
