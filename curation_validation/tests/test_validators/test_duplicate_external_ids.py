import csv
import json
from pathlib import Path

import pytest

from curation_validation.validators.base import ValidatorContext
from curation_validation.core.loader import DataSource
from curation_validation.validators.duplicate_external_ids import (
    DuplicateExternalIdsValidator,
    normalize_whitespace,
    process_input_csv,
    extract_external_ids,
    normalize_data_dump_external_ids,
    get_ror_display_name,
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


def _dump_record(ror_id, display_name, external_ids=None):
    record = {
        "id": ror_id,
        "names": [{"value": display_name, "types": ["ror_display"]}],
        "external_ids": external_ids or [],
    }
    return record


class TestDuplicateExternalIdsValidatorMetadata:
    def test_name(self):
        v = DuplicateExternalIdsValidator()
        assert v.name == "duplicate-external-ids"

    def test_supported_formats(self):
        v = DuplicateExternalIdsValidator()
        assert v.supported_formats == {"csv", "json"}

    def test_requires_data_source(self):
        v = DuplicateExternalIdsValidator()
        assert v.requires_data_source is True

    def test_output_filename(self):
        v = DuplicateExternalIdsValidator()
        assert v.output_filename == "duplicate_external_ids.csv"

    def test_output_fields(self):
        v = DuplicateExternalIdsValidator()
        expected = [
            "id",
            "ror_display_name",
            "data_dump_id",
            "data_dump_ror_display_name",
            "overlapping_external_id",
        ]
        assert v.output_fields == expected

    def test_can_run_without_data_source(self, tmp_path):
        v = DuplicateExternalIdsValidator()
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
        v = DuplicateExternalIdsValidator()
        can, _ = v.can_run(ctx)
        assert can is True


class TestNormalizeWhitespace:
    def test_collapses_multiple_spaces(self):
        assert normalize_whitespace("0000  0001  2222  3333") == "0000 0001 2222 3333"

    def test_strips_leading_trailing(self):
        assert normalize_whitespace("  Q12345  ") == "Q12345"

    def test_collapses_tabs_and_newlines(self):
        assert normalize_whitespace("0000\t0001\n2222\r3333") == "0000 0001 2222 3333"

    def test_already_normalized(self):
        assert normalize_whitespace("Q12345") == "Q12345"

    def test_empty_string(self):
        assert normalize_whitespace("") == ""


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


class TestExtractExternalIds:
    def test_extracts_all_ids(self):
        record = {
            "external_ids": [
                {"type": "isni", "all": ["0000 0001 2222 3333"], "preferred": "0000 0001 2222 3333"},
                {"type": "wikidata", "all": ["Q12345"], "preferred": "Q12345"},
            ]
        }
        ids = extract_external_ids(record)
        assert "0000 0001 2222 3333" in ids
        assert "Q12345" in ids

    def test_extracts_preferred_even_if_not_in_all(self):
        record = {
            "external_ids": [
                {"type": "isni", "all": [], "preferred": "0000 0001 2222 3333"},
            ]
        }
        ids = extract_external_ids(record)
        assert "0000 0001 2222 3333" in ids

    def test_empty_external_ids(self):
        record = {"external_ids": []}
        ids = extract_external_ids(record)
        assert ids == set()

    def test_no_external_ids_key(self):
        record = {}
        ids = extract_external_ids(record)
        assert ids == set()

    def test_multiple_all_values(self):
        record = {
            "external_ids": [
                {"type": "fundref", "all": ["100000001", "100000002"], "preferred": "100000001"},
            ]
        }
        ids = extract_external_ids(record)
        assert "100000001" in ids
        assert "100000002" in ids


class TestProcessInputCsv:
    def test_processes_csv_row_with_isni(self):
        rows = [{
            "id": "https://ror.org/001",
            "names.types.ror_display": "Test Org",
            "external_ids.type.isni.all": "0000 0001 2222 3333",
            "external_ids.type.isni.preferred": "0000 0001 2222 3333",
            "external_ids.type.wikidata.all": "",
            "external_ids.type.wikidata.preferred": "",
            "external_ids.type.fundref.all": "",
            "external_ids.type.fundref.preferred": "",
            "external_ids.type.grid.all": "",
            "external_ids.type.grid.preferred": "",
        }]
        processed = process_input_csv(rows)
        assert len(processed) == 1
        assert processed[0]["id"] == "https://ror.org/001"
        ids = extract_external_ids(processed[0])
        assert "0000 0001 2222 3333" in ids

    def test_processes_semicolon_separated_all(self):
        rows = [{
            "id": "",
            "names.types.ror_display": "Test Org",
            "external_ids.type.isni.all": "0000 0001 2222 3333;0000 0004 5555 6666",
            "external_ids.type.isni.preferred": "0000 0001 2222 3333",
            "external_ids.type.wikidata.all": "",
            "external_ids.type.wikidata.preferred": "",
            "external_ids.type.fundref.all": "",
            "external_ids.type.fundref.preferred": "",
            "external_ids.type.grid.all": "",
            "external_ids.type.grid.preferred": "",
        }]
        processed = process_input_csv(rows)
        ids = extract_external_ids(processed[0])
        assert "0000 0001 2222 3333" in ids
        assert "0000 0004 5555 6666" in ids

    def test_normalizes_whitespace_in_csv(self):
        rows = [{
            "id": "",
            "names.types.ror_display": "Test Org",
            "external_ids.type.isni.all": "0000  0001  2222  3333",
            "external_ids.type.isni.preferred": "0000  0001  2222  3333",
            "external_ids.type.wikidata.all": "",
            "external_ids.type.wikidata.preferred": "",
            "external_ids.type.fundref.all": "",
            "external_ids.type.fundref.preferred": "",
            "external_ids.type.grid.all": "",
            "external_ids.type.grid.preferred": "",
        }]
        processed = process_input_csv(rows)
        ids = extract_external_ids(processed[0])
        assert "0000 0001 2222 3333" in ids

    def test_no_external_ids_in_csv_row(self):
        rows = [{
            "id": "",
            "names.types.ror_display": "Test Org",
            "external_ids.type.isni.all": "",
            "external_ids.type.isni.preferred": "",
            "external_ids.type.wikidata.all": "",
            "external_ids.type.wikidata.preferred": "",
            "external_ids.type.fundref.all": "",
            "external_ids.type.fundref.preferred": "",
            "external_ids.type.grid.all": "",
            "external_ids.type.grid.preferred": "",
        }]
        processed = process_input_csv(rows)
        ids = extract_external_ids(processed[0])
        assert ids == set()


class TestNormalizeDataDumpExternalIds:
    def test_normalizes_whitespace_in_data_dump(self):
        records = [{
            "id": "https://ror.org/001",
            "external_ids": [
                {"type": "isni", "all": ["0000  0001  2222  3333"], "preferred": "0000  0001  2222  3333"},
            ]
        }]
        normalized = normalize_data_dump_external_ids(records)
        assert normalized[0]["external_ids"][0]["all"] == ["0000 0001 2222 3333"]
        assert normalized[0]["external_ids"][0]["preferred"] == "0000 0001 2222 3333"

    def test_handles_empty_preferred(self):
        records = [{
            "id": "https://ror.org/001",
            "external_ids": [
                {"type": "wikidata", "all": ["Q12345"], "preferred": ""},
            ]
        }]
        normalized = normalize_data_dump_external_ids(records)
        assert normalized[0]["external_ids"][0]["preferred"] == ""


class TestDuplicateExternalIdsJSON:
    def test_isni_overlap(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", [
                {"type": "isni", "all": ["0000 0001 2222 3333"], "preferred": "0000 0001 2222 3333"},
            ]),
        ]
        ds = _make_data_source(dump_records)
        input_records = [{
            "id": "",
            "names": [{"value": "New Org", "types": ["ror_display"]}],
            "external_ids": [
                {"type": "isni", "all": ["0000 0001 2222 3333"], "preferred": "0000 0001 2222 3333"},
            ],
        }]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateExternalIdsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["overlapping_external_id"] == "0000 0001 2222 3333"
        assert results[0]["ror_display_name"] == "New Org"
        assert results[0]["data_dump_id"] == "https://ror.org/dump001"
        assert results[0]["data_dump_ror_display_name"] == "Dump Org"

    def test_wikidata_overlap(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", [
                {"type": "wikidata", "all": ["Q12345"], "preferred": "Q12345"},
            ]),
        ]
        ds = _make_data_source(dump_records)
        input_records = [{
            "id": "",
            "names": [{"value": "New Org", "types": ["ror_display"]}],
            "external_ids": [
                {"type": "wikidata", "all": ["Q12345"], "preferred": "Q12345"},
            ],
        }]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateExternalIdsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["overlapping_external_id"] == "Q12345"

    def test_fundref_overlap(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", [
                {"type": "fundref", "all": ["100000001"], "preferred": "100000001"},
            ]),
        ]
        ds = _make_data_source(dump_records)
        input_records = [{
            "id": "",
            "names": [{"value": "New Org", "types": ["ror_display"]}],
            "external_ids": [
                {"type": "fundref", "all": ["100000001"], "preferred": "100000001"},
            ],
        }]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateExternalIdsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["overlapping_external_id"] == "100000001"

    def test_no_overlap(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", [
                {"type": "isni", "all": ["0000 0001 2222 3333"], "preferred": "0000 0001 2222 3333"},
            ]),
        ]
        ds = _make_data_source(dump_records)
        input_records = [{
            "id": "",
            "names": [{"value": "New Org", "types": ["ror_display"]}],
            "external_ids": [
                {"type": "isni", "all": ["0000 9999 8888 7777"], "preferred": "0000 9999 8888 7777"},
            ],
        }]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateExternalIdsValidator()
        results = v.run(ctx)
        assert len(results) == 0

    def test_whitespace_normalization_match(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", [
                {"type": "isni", "all": ["0000  0001  2222  3333"], "preferred": "0000  0001  2222  3333"},
            ]),
        ]
        ds = _make_data_source(dump_records)
        input_records = [{
            "id": "",
            "names": [{"value": "New Org", "types": ["ror_display"]}],
            "external_ids": [
                {"type": "isni", "all": ["0000 0001 2222 3333"], "preferred": "0000 0001 2222 3333"},
            ],
        }]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateExternalIdsValidator()
        results = v.run(ctx)
        assert len(results) == 1

    def test_multiple_overlapping_ids(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", [
                {"type": "isni", "all": ["0000 0001 2222 3333"], "preferred": "0000 0001 2222 3333"},
                {"type": "wikidata", "all": ["Q12345"], "preferred": "Q12345"},
            ]),
        ]
        ds = _make_data_source(dump_records)
        input_records = [{
            "id": "",
            "names": [{"value": "New Org", "types": ["ror_display"]}],
            "external_ids": [
                {"type": "isni", "all": ["0000 0001 2222 3333"], "preferred": "0000 0001 2222 3333"},
                {"type": "wikidata", "all": ["Q12345"], "preferred": "Q12345"},
            ],
        }]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateExternalIdsValidator()
        results = v.run(ctx)
        assert len(results) == 2
        overlapping = {r["overlapping_external_id"] for r in results}
        assert "0000 0001 2222 3333" in overlapping
        assert "Q12345" in overlapping

    def test_no_external_ids_in_input(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", [
                {"type": "isni", "all": ["0000 0001 2222 3333"], "preferred": "0000 0001 2222 3333"},
            ]),
        ]
        ds = _make_data_source(dump_records)
        input_records = [{
            "id": "",
            "names": [{"value": "No IDs Org", "types": ["ror_display"]}],
            "external_ids": [],
        }]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateExternalIdsValidator()
        results = v.run(ctx)
        assert len(results) == 0

    def test_empty_data_source(self, tmp_path):
        ds = _make_data_source([])
        input_records = [{
            "id": "",
            "names": [{"value": "New Org", "types": ["ror_display"]}],
            "external_ids": [
                {"type": "isni", "all": ["0000 0001 2222 3333"], "preferred": "0000 0001 2222 3333"},
            ],
        }]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateExternalIdsValidator()
        results = v.run(ctx)
        assert results == []

    def test_output_format_fields(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", [
                {"type": "isni", "all": ["0000 0001 2222 3333"], "preferred": "0000 0001 2222 3333"},
            ]),
        ]
        ds = _make_data_source(dump_records)
        input_records = [{
            "id": "https://ror.org/input001",
            "names": [{"value": "New Org", "types": ["ror_display"]}],
            "external_ids": [
                {"type": "isni", "all": ["0000 0001 2222 3333"], "preferred": "0000 0001 2222 3333"},
            ],
        }]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateExternalIdsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        result = results[0]
        assert "id" in result
        assert "ror_display_name" in result
        assert "data_dump_id" in result
        assert "data_dump_ror_display_name" in result
        assert "overlapping_external_id" in result

    def test_empty_json_dir(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", [
                {"type": "isni", "all": ["0000 0001 2222 3333"], "preferred": "0000 0001 2222 3333"},
            ]),
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
        v = DuplicateExternalIdsValidator()
        results = v.run(ctx)
        assert results == []

    def test_multiple_input_records(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", [
                {"type": "wikidata", "all": ["Q12345"], "preferred": "Q12345"},
            ]),
        ]
        ds = _make_data_source(dump_records)
        input_records = [
            {
                "id": "",
                "names": [{"value": "Match Org", "types": ["ror_display"]}],
                "external_ids": [
                    {"type": "wikidata", "all": ["Q12345"], "preferred": "Q12345"},
                ],
            },
            {
                "id": "",
                "names": [{"value": "No Match Org", "types": ["ror_display"]}],
                "external_ids": [
                    {"type": "wikidata", "all": ["Q99999"], "preferred": "Q99999"},
                ],
            },
        ]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateExternalIdsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["ror_display_name"] == "Match Org"

    def test_prefers_json_over_csv(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", [
                {"type": "isni", "all": ["0000 0001 2222 3333"], "preferred": "0000 0001 2222 3333"},
            ]),
        ]
        ds = _make_data_source(dump_records)

        json_dir = tmp_path / "json"
        json_dir.mkdir(parents=True, exist_ok=True)
        json_record = {
            "id": "",
            "names": [{"value": "JSON Org", "types": ["ror_display"]}],
            "external_ids": [
                {"type": "isni", "all": ["0000 0001 2222 3333"], "preferred": "0000 0001 2222 3333"},
            ],
        }
        (json_dir / "rec.json").write_text(json.dumps(json_record), encoding="utf-8")

        csv_file = tmp_path / "input.csv"
        fieldnames = [
            "id", "names.types.ror_display",
            "external_ids.type.isni.all", "external_ids.type.isni.preferred",
            "external_ids.type.wikidata.all", "external_ids.type.wikidata.preferred",
            "external_ids.type.fundref.all", "external_ids.type.fundref.preferred",
            "external_ids.type.grid.all", "external_ids.type.grid.preferred",
        ]
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow({
                "id": "",
                "names.types.ror_display": "CSV Org",
                "external_ids.type.isni.all": "0000 0001 2222 3333",
                "external_ids.type.isni.preferred": "0000 0001 2222 3333",
                "external_ids.type.wikidata.all": "",
                "external_ids.type.wikidata.preferred": "",
                "external_ids.type.fundref.all": "",
                "external_ids.type.fundref.preferred": "",
                "external_ids.type.grid.all": "",
                "external_ids.type.grid.preferred": "",
            })

        ctx = ValidatorContext(
            csv_file=csv_file,
            json_dir=json_dir,
            output_dir=tmp_path / "output",
            data_source=ds,
            geonames_user=None,
        )
        v = DuplicateExternalIdsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["ror_display_name"] == "JSON Org"


class TestDuplicateExternalIdsCSV:
    def test_isni_overlap_csv(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", [
                {"type": "isni", "all": ["0000 0001 2222 3333"], "preferred": "0000 0001 2222 3333"},
            ]),
        ]
        ds = _make_data_source(dump_records)
        rows = [{
            "id": "",
            "names.types.ror_display": "New Org",
            "external_ids.type.isni.all": "0000 0001 2222 3333",
            "external_ids.type.isni.preferred": "0000 0001 2222 3333",
            "external_ids.type.wikidata.all": "",
            "external_ids.type.wikidata.preferred": "",
            "external_ids.type.fundref.all": "",
            "external_ids.type.fundref.preferred": "",
            "external_ids.type.grid.all": "",
            "external_ids.type.grid.preferred": "",
        }]
        ctx = _make_csv_ctx(tmp_path, rows, data_source=ds)
        v = DuplicateExternalIdsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["overlapping_external_id"] == "0000 0001 2222 3333"
        assert results[0]["ror_display_name"] == "New Org"
        assert results[0]["data_dump_id"] == "https://ror.org/dump001"

    def test_wikidata_overlap_csv(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", [
                {"type": "wikidata", "all": ["Q12345"], "preferred": "Q12345"},
            ]),
        ]
        ds = _make_data_source(dump_records)
        rows = [{
            "id": "",
            "names.types.ror_display": "New Org",
            "external_ids.type.isni.all": "",
            "external_ids.type.isni.preferred": "",
            "external_ids.type.wikidata.all": "Q12345",
            "external_ids.type.wikidata.preferred": "Q12345",
            "external_ids.type.fundref.all": "",
            "external_ids.type.fundref.preferred": "",
            "external_ids.type.grid.all": "",
            "external_ids.type.grid.preferred": "",
        }]
        ctx = _make_csv_ctx(tmp_path, rows, data_source=ds)
        v = DuplicateExternalIdsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["overlapping_external_id"] == "Q12345"

    def test_fundref_overlap_csv(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", [
                {"type": "fundref", "all": ["100000001"], "preferred": "100000001"},
            ]),
        ]
        ds = _make_data_source(dump_records)
        rows = [{
            "id": "",
            "names.types.ror_display": "New Org",
            "external_ids.type.isni.all": "",
            "external_ids.type.isni.preferred": "",
            "external_ids.type.wikidata.all": "",
            "external_ids.type.wikidata.preferred": "",
            "external_ids.type.fundref.all": "100000001",
            "external_ids.type.fundref.preferred": "100000001",
            "external_ids.type.grid.all": "",
            "external_ids.type.grid.preferred": "",
        }]
        ctx = _make_csv_ctx(tmp_path, rows, data_source=ds)
        v = DuplicateExternalIdsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["overlapping_external_id"] == "100000001"

    def test_no_overlap_csv(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", [
                {"type": "isni", "all": ["0000 0001 2222 3333"], "preferred": "0000 0001 2222 3333"},
            ]),
        ]
        ds = _make_data_source(dump_records)
        rows = [{
            "id": "",
            "names.types.ror_display": "New Org",
            "external_ids.type.isni.all": "0000 9999 8888 7777",
            "external_ids.type.isni.preferred": "0000 9999 8888 7777",
            "external_ids.type.wikidata.all": "",
            "external_ids.type.wikidata.preferred": "",
            "external_ids.type.fundref.all": "",
            "external_ids.type.fundref.preferred": "",
            "external_ids.type.grid.all": "",
            "external_ids.type.grid.preferred": "",
        }]
        ctx = _make_csv_ctx(tmp_path, rows, data_source=ds)
        v = DuplicateExternalIdsValidator()
        results = v.run(ctx)
        assert len(results) == 0

    def test_whitespace_normalization_csv(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", [
                {"type": "isni", "all": ["0000 0001 2222 3333"], "preferred": "0000 0001 2222 3333"},
            ]),
        ]
        ds = _make_data_source(dump_records)
        rows = [{
            "id": "",
            "names.types.ror_display": "New Org",
            "external_ids.type.isni.all": "0000  0001  2222  3333",
            "external_ids.type.isni.preferred": "0000  0001  2222  3333",
            "external_ids.type.wikidata.all": "",
            "external_ids.type.wikidata.preferred": "",
            "external_ids.type.fundref.all": "",
            "external_ids.type.fundref.preferred": "",
            "external_ids.type.grid.all": "",
            "external_ids.type.grid.preferred": "",
        }]
        ctx = _make_csv_ctx(tmp_path, rows, data_source=ds)
        v = DuplicateExternalIdsValidator()
        results = v.run(ctx)
        assert len(results) == 1

    def test_csv_semicolon_separated_ids(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", [
                {"type": "fundref", "all": ["100000002"], "preferred": "100000002"},
            ]),
        ]
        ds = _make_data_source(dump_records)
        rows = [{
            "id": "",
            "names.types.ror_display": "New Org",
            "external_ids.type.isni.all": "",
            "external_ids.type.isni.preferred": "",
            "external_ids.type.wikidata.all": "",
            "external_ids.type.wikidata.preferred": "",
            "external_ids.type.fundref.all": "100000001;100000002",
            "external_ids.type.fundref.preferred": "100000001",
            "external_ids.type.grid.all": "",
            "external_ids.type.grid.preferred": "",
        }]
        ctx = _make_csv_ctx(tmp_path, rows, data_source=ds)
        v = DuplicateExternalIdsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["overlapping_external_id"] == "100000002"

    def test_csv_no_external_ids(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", [
                {"type": "isni", "all": ["0000 0001 2222 3333"], "preferred": "0000 0001 2222 3333"},
            ]),
        ]
        ds = _make_data_source(dump_records)
        rows = [{
            "id": "",
            "names.types.ror_display": "New Org",
            "external_ids.type.isni.all": "",
            "external_ids.type.isni.preferred": "",
            "external_ids.type.wikidata.all": "",
            "external_ids.type.wikidata.preferred": "",
            "external_ids.type.fundref.all": "",
            "external_ids.type.fundref.preferred": "",
            "external_ids.type.grid.all": "",
            "external_ids.type.grid.preferred": "",
        }]
        ctx = _make_csv_ctx(tmp_path, rows, data_source=ds)
        v = DuplicateExternalIdsValidator()
        results = v.run(ctx)
        assert len(results) == 0

    def test_csv_output_fields(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", [
                {"type": "isni", "all": ["0000 0001 2222 3333"], "preferred": "0000 0001 2222 3333"},
            ]),
        ]
        ds = _make_data_source(dump_records)
        rows = [{
            "id": "https://ror.org/input001",
            "names.types.ror_display": "New Org",
            "external_ids.type.isni.all": "0000 0001 2222 3333",
            "external_ids.type.isni.preferred": "0000 0001 2222 3333",
            "external_ids.type.wikidata.all": "",
            "external_ids.type.wikidata.preferred": "",
            "external_ids.type.fundref.all": "",
            "external_ids.type.fundref.preferred": "",
            "external_ids.type.grid.all": "",
            "external_ids.type.grid.preferred": "",
        }]
        ctx = _make_csv_ctx(tmp_path, rows, data_source=ds)
        v = DuplicateExternalIdsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        result = results[0]
        assert result["id"] == "https://ror.org/input001"
        assert result["ror_display_name"] == "New Org"
        assert result["data_dump_id"] == "https://ror.org/dump001"
        assert result["data_dump_ror_display_name"] == "Dump Org"
        assert result["overlapping_external_id"] == "0000 0001 2222 3333"

    def test_csv_multiple_rows(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", [
                {"type": "wikidata", "all": ["Q12345"], "preferred": "Q12345"},
            ]),
        ]
        ds = _make_data_source(dump_records)
        rows = [
            {
                "id": "",
                "names.types.ror_display": "Match Org",
                "external_ids.type.isni.all": "",
                "external_ids.type.isni.preferred": "",
                "external_ids.type.wikidata.all": "Q12345",
                "external_ids.type.wikidata.preferred": "Q12345",
                "external_ids.type.fundref.all": "",
                "external_ids.type.fundref.preferred": "",
                "external_ids.type.grid.all": "",
                "external_ids.type.grid.preferred": "",
            },
            {
                "id": "",
                "names.types.ror_display": "No Match Org",
                "external_ids.type.isni.all": "",
                "external_ids.type.isni.preferred": "",
                "external_ids.type.wikidata.all": "Q99999",
                "external_ids.type.wikidata.preferred": "Q99999",
                "external_ids.type.fundref.all": "",
                "external_ids.type.fundref.preferred": "",
                "external_ids.type.grid.all": "",
                "external_ids.type.grid.preferred": "",
            },
        ]
        ctx = _make_csv_ctx(tmp_path, rows, data_source=ds)
        v = DuplicateExternalIdsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["ror_display_name"] == "Match Org"


class TestDuplicateExternalIdsEdgeCases:
    def test_returns_empty_when_no_input(self, tmp_path):
        ds = _make_data_source([])
        ctx = ValidatorContext(
            csv_file=None,
            json_dir=None,
            output_dir=tmp_path,
            data_source=ds,
            geonames_user=None,
        )
        v = DuplicateExternalIdsValidator()
        results = v.run(ctx)
        assert results == []

    def test_match_against_multiple_dump_records(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Org A", [
                {"type": "isni", "all": ["0000 0001 1111 1111"], "preferred": "0000 0001 1111 1111"},
            ]),
            _dump_record("https://ror.org/dump002", "Org B", [
                {"type": "isni", "all": ["0000 0002 2222 2222"], "preferred": "0000 0002 2222 2222"},
            ]),
            _dump_record("https://ror.org/dump003", "Org C", [
                {"type": "isni", "all": ["0000 0003 3333 3333"], "preferred": "0000 0003 3333 3333"},
            ]),
        ]
        ds = _make_data_source(dump_records)
        input_records = [{
            "id": "",
            "names": [{"value": "New Org", "types": ["ror_display"]}],
            "external_ids": [
                {"type": "isni", "all": ["0000 0002 2222 2222"], "preferred": "0000 0002 2222 2222"},
            ],
        }]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateExternalIdsValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["data_dump_id"] == "https://ror.org/dump002"
        assert results[0]["data_dump_ror_display_name"] == "Org B"

    def test_input_matches_multiple_dump_records(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Org A", [
                {"type": "isni", "all": ["0000 0001 2222 3333"], "preferred": "0000 0001 2222 3333"},
            ]),
            _dump_record("https://ror.org/dump002", "Org B", [
                {"type": "isni", "all": ["0000 0001 2222 3333"], "preferred": "0000 0001 2222 3333"},
            ]),
        ]
        ds = _make_data_source(dump_records)
        input_records = [{
            "id": "",
            "names": [{"value": "New Org", "types": ["ror_display"]}],
            "external_ids": [
                {"type": "isni", "all": ["0000 0001 2222 3333"], "preferred": "0000 0001 2222 3333"},
            ],
        }]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateExternalIdsValidator()
        results = v.run(ctx)
        assert len(results) == 2
        dump_ids = {r["data_dump_id"] for r in results}
        assert "https://ror.org/dump001" in dump_ids
        assert "https://ror.org/dump002" in dump_ids

    def test_missing_external_ids_key_in_input(self, tmp_path):
        dump_records = [
            _dump_record("https://ror.org/dump001", "Dump Org", [
                {"type": "isni", "all": ["0000 0001 2222 3333"], "preferred": "0000 0001 2222 3333"},
            ]),
        ]
        ds = _make_data_source(dump_records)
        input_records = [{
            "id": "",
            "names": [{"value": "No ExtIDs Org", "types": ["ror_display"]}],
        }]
        ctx = _make_json_ctx(tmp_path, input_records, data_source=ds)
        v = DuplicateExternalIdsValidator()
        results = v.run(ctx)
        assert results == []
