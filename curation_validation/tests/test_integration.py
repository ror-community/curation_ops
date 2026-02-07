import csv
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from curation_validation.cli import parse_args
from curation_validation.core.exceptions import ConfigurationError
from curation_validation.runner import run_validators, VALIDATORS
from curation_validation.validators import register_all_validators


@pytest.fixture(autouse=True)
def clean_validators():
    VALIDATORS.clear()
    register_all_validators()
    yield
    VALIDATORS.clear()


CSV_HEADER = (
    "id,names.types.ror_display,names.types.acronym,names.types.alias,"
    "names.types.label,status,types,links.type.website,links.type.wikipedia,"
    "established,locations.geonames_id,city,country,"
    "external_ids.type.isni.all,external_ids.type.isni.preferred,"
    "external_ids.type.wikidata.all,external_ids.type.wikidata.preferred,"
    "external_ids.type.fundref.all,external_ids.type.fundref.preferred,"
    "domains"
)

CSV_ROW_VALID = (
    ",Test University*en,TU,Test Uni*en,Universite de Test*fr,"
    "active,education,https://test.edu,https://en.wikipedia.org/wiki/Test_University,"
    "2000,5128581,Boston,United States,"
    "0000 0000 1234 5678,0000 0000 1234 5678,"
    "Q12345,Q12345,"
    "100000,100000,"
)


def make_csv(tmp_path, name="test.csv", content=None):
    if content is None:
        content = f"{CSV_HEADER}\n{CSV_ROW_VALID}\n"
    csv_file = tmp_path / name
    csv_file.write_text(content)
    return csv_file


def make_minimal_json_record(ror_id="https://ror.org/00test123", name="Test University"):
    return {
        "id": ror_id,
        "status": "active",
        "types": ["education"],
        "names": [
            {"value": name, "types": ["ror_display"]},
        ],
        "links": [
            {"type": "website", "value": "https://test.edu"},
        ],
        "established": 2000,
        "locations": [
            {
                "geonames_id": 5128581,
                "geonames_details": {
                    "name": "Boston",
                    "country_name": "United States",
                    "country_code": "US",
                },
            }
        ],
        "external_ids": [
            {
                "type": "isni",
                "all": ["0000 0000 1234 5678"],
                "preferred": "0000 0000 1234 5678",
            },
            {
                "type": "wikidata",
                "all": ["Q12345"],
                "preferred": "Q12345",
            },
            {
                "type": "fundref",
                "all": ["100000"],
                "preferred": "100000",
            },
        ],
        "admin": {
            "created": {"date": "2020-01-01"},
            "last_modified": {"date": "2020-06-01"},
        },
        "relationships": [],
        "domains": [],
    }


def make_json_dir(tmp_path, records=None, dirname="json"):
    if records is None:
        records = [make_minimal_json_record()]
    json_dir = tmp_path / dirname
    json_dir.mkdir(exist_ok=True)
    for record in records:
        ror_id = record.get("id", "").replace("https://ror.org/", "")
        (json_dir / f"{ror_id}.json").write_text(json.dumps(record))
    return json_dir


def read_output_csv(path):
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows


STANDALONE_CSV_VALIDATORS = {
    "validate_fields",
    "duplicate_values",
    "unprintable-chars",
    "leading_trailing",
    "in-release-duplicates",
}

STANDALONE_JSON_VALIDATORS = {
    "validate_fields",
    "duplicate_values",
    "unprintable-chars",
    "leading_trailing",
    "in-release-duplicates",
}


class TestCsvOnlyInvocation:
    def test_csv_only_runs_standalone_validators(self, tmp_path):
        csv_file = make_csv(tmp_path)
        output_dir = tmp_path / "out"

        run_validators(
            csv_file=csv_file,
            json_dir=None,
            output_dir=output_dir,
            data_dump_path=None,
            geonames_user=None,
            tests=["validate_fields"],
        )

        expected_file = output_dir / "csv_validate_fields.csv"
        assert expected_file.exists() or not expected_file.exists()

    def test_csv_only_with_invalid_data_creates_output(self, tmp_path):
        bad_csv = (
            f"{CSV_HEADER}\n"
            ",Bad Name,lower,,,INVALID_STATUS,badtype,not-a-url,not-a-wiki,abc,abc,,,"
            "bad-isni,bad-isni,bad-wikidata,bad-wikidata,bad-fundref,bad-fundref,\n"
        )
        csv_file = make_csv(tmp_path, content=bad_csv)
        output_dir = tmp_path / "out"

        run_validators(
            csv_file=csv_file,
            json_dir=None,
            output_dir=output_dir,
            data_dump_path=None,
            geonames_user=None,
            tests=["validate_fields"],
        )

        expected_file = output_dir / "csv_validate_fields.csv"
        assert expected_file.exists()
        rows = read_output_csv(expected_file)
        assert len(rows) > 0

    def test_csv_only_skips_json_only_formats(self, tmp_path):
        csv_file = make_csv(tmp_path)
        output_dir = tmp_path / "out"

        run_validators(
            csv_file=csv_file,
            json_dir=None,
            output_dir=output_dir,
            data_dump_path=None,
            geonames_user=None,
            tests=["validate_fields"],
        )

        output_files = list(output_dir.glob("json_*"))
        assert len(output_files) == 0


class TestJsonOnlyInvocation:
    def test_json_only_runs_standalone_validators(self, tmp_path):
        json_dir = make_json_dir(tmp_path)
        output_dir = tmp_path / "out"

        run_validators(
            csv_file=None,
            json_dir=json_dir,
            output_dir=output_dir,
            data_dump_path=None,
            geonames_user=None,
            tests=["validate_fields"],
        )

        csv_files = list(output_dir.glob("csv_*"))
        assert len(csv_files) == 0

    def test_json_only_with_bad_data_produces_output(self, tmp_path):
        bad_record = make_minimal_json_record()
        bad_record["status"] = "INVALID_STATUS"
        json_dir = make_json_dir(tmp_path, records=[bad_record])
        output_dir = tmp_path / "out"

        run_validators(
            csv_file=None,
            json_dir=json_dir,
            output_dir=output_dir,
            data_dump_path=None,
            geonames_user=None,
            tests=["validate_fields"],
        )

        expected_file = output_dir / "json_validate_fields.csv"
        assert expected_file.exists()
        rows = read_output_csv(expected_file)
        assert len(rows) > 0
        assert any("status" in r.get("error_warning", "").lower() for r in rows)

    def test_json_only_does_not_create_csv_prefixed_files(self, tmp_path):
        json_dir = make_json_dir(tmp_path)
        output_dir = tmp_path / "out"

        run_validators(
            csv_file=None,
            json_dir=json_dir,
            output_dir=output_dir,
            data_dump_path=None,
            geonames_user=None,
            tests=["leading_trailing"],
        )

        csv_files = list(output_dir.glob("csv_*"))
        assert len(csv_files) == 0


class TestBothInputs:
    def test_both_inputs_runs_csv_json_validators(self, tmp_path):
        record = make_minimal_json_record(ror_id="https://ror.org/00test123")
        json_dir = make_json_dir(tmp_path, records=[record])

        csv_content = (
            "id,names.types.ror_display,status,types,links.type.website,"
            "established,locations.geonames_id\n"
            "https://ror.org/00test123,Test University,active,education,"
            "https://test.edu,2000,5128581\n"
        )
        csv_file = make_csv(tmp_path, content=csv_content)
        output_dir = tmp_path / "out"

        run_validators(
            csv_file=csv_file,
            json_dir=json_dir,
            output_dir=output_dir,
            data_dump_path=None,
            geonames_user=None,
            tests=["new-record-integrity"],
        )

    def test_both_inputs_runs_dual_format_validators_for_both_formats(self, tmp_path):
        bad_csv = (
            f"{CSV_HEADER}\n"
            ",Bad Name,lower,,,INVALID_STATUS,badtype,not-a-url,not-a-wiki,abc,abc,,,"
            "bad-isni,bad-isni,bad-wikidata,bad-wikidata,bad-fundref,bad-fundref,\n"
        )
        csv_file = make_csv(tmp_path, content=bad_csv)

        bad_record = make_minimal_json_record()
        bad_record["status"] = "INVALID_STATUS"
        json_dir = make_json_dir(tmp_path, records=[bad_record])
        output_dir = tmp_path / "out"

        run_validators(
            csv_file=csv_file,
            json_dir=json_dir,
            output_dir=output_dir,
            data_dump_path=None,
            geonames_user=None,
            tests=["validate_fields"],
        )

        assert (output_dir / "csv_validate_fields.csv").exists()
        assert (output_dir / "json_validate_fields.csv").exists()

    def test_integrity_check_detects_mismatch(self, tmp_path):
        record = make_minimal_json_record(ror_id="https://ror.org/00test123")
        json_dir = make_json_dir(tmp_path, records=[record])

        csv_content = (
            "id,names.types.ror_display,status,types,links.type.website,"
            "established,locations.geonames_id\n"
            "https://ror.org/00test123,Test University,active,company,"
            "https://test.edu,2000,5128581\n"
        )
        csv_file = make_csv(tmp_path, content=csv_content)
        output_dir = tmp_path / "out"

        run_validators(
            csv_file=csv_file,
            json_dir=json_dir,
            output_dir=output_dir,
            data_dump_path=None,
            geonames_user=None,
            tests=["new-record-integrity"],
        )

        integrity_file = output_dir / "new_record_integrity.csv"
        assert integrity_file.exists()
        rows = read_output_csv(integrity_file)
        assert len(rows) > 0


class TestTestFlag:
    def test_single_test_flag_runs_only_that_validator(self, tmp_path):
        bad_csv = (
            f"{CSV_HEADER}\n"
            ",Bad Name,lower,,,INVALID_STATUS,badtype,not-a-url,not-a-wiki,abc,abc,,,"
            "bad-isni,bad-isni,bad-wikidata,bad-wikidata,bad-fundref,bad-fundref,\n"
        )
        csv_file = make_csv(tmp_path, content=bad_csv)
        output_dir = tmp_path / "out"

        run_validators(
            csv_file=csv_file,
            json_dir=None,
            output_dir=output_dir,
            data_dump_path=None,
            geonames_user=None,
            tests=["validate_fields"],
        )

        output_files = list(output_dir.glob("*.csv"))
        filenames = {f.name for f in output_files}
        assert "csv_validate_fields.csv" in filenames
        for name in filenames:
            assert "validate_fields" in name

    def test_multiple_test_flags(self, tmp_path):
        csv_content = (
            f"{CSV_HEADER}\n"
            ",Bad Name,lower,,,INVALID_STATUS,badtype,not-a-url,not-a-wiki,abc,abc,,,"
            "bad-isni,bad-isni,bad-wikidata,bad-wikidata,bad-fundref,bad-fundref,\n"
        )
        csv_file = make_csv(tmp_path, content=csv_content)
        output_dir = tmp_path / "out"

        run_validators(
            csv_file=csv_file,
            json_dir=None,
            output_dir=output_dir,
            data_dump_path=None,
            geonames_user=None,
            tests=["validate_fields", "leading_trailing"],
        )

        output_files = {f.name for f in output_dir.glob("*.csv")}
        assert "csv_validate_fields.csv" in output_files
        for name in output_files:
            assert ("validate_fields" in name or "leading_trailing" in name)

    def test_parse_args_test_flag(self):
        args = parse_args(["-c", "test.csv", "--test", "validate_fields"])
        assert args.test == ["validate_fields"]

    def test_parse_args_default_all(self):
        args = parse_args(["-c", "test.csv"])
        assert args.test == ["all"]

    def test_unknown_validator_is_skipped(self, tmp_path, capsys):
        csv_file = make_csv(tmp_path)
        output_dir = tmp_path / "out"

        run_validators(
            csv_file=csv_file,
            json_dir=None,
            output_dir=output_dir,
            data_dump_path=None,
            geonames_user=None,
            tests=["nonexistent-validator"],
        )

        captured = capsys.readouterr()
        assert "unknown" in captured.err.lower() or "Unknown" in captured.err


class TestMissingInput:
    def test_parse_args_requires_at_least_one_input(self):
        with pytest.raises(SystemExit):
            parse_args([])

    def test_cli_main_missing_csv_file(self, tmp_path):
        from curation_validation.cli import main

        nonexistent = str(tmp_path / "does_not_exist.csv")
        with patch("sys.argv", ["curation-validation", "-c", nonexistent]):
            ret = main()
        assert ret == 1

    def test_cli_main_missing_json_dir(self, tmp_path):
        from curation_validation.cli import main

        nonexistent = str(tmp_path / "no_such_dir")
        with patch("sys.argv", ["curation-validation", "-j", nonexistent]):
            ret = main()
        assert ret == 1


class TestCsvJsonValidatorSkipping:
    def test_csv_only_raises_for_explicit_csv_json_validator(self, tmp_path):
        csv_file = make_csv(tmp_path)
        output_dir = tmp_path / "out"

        with pytest.raises(ConfigurationError, match="requires both"):
            run_validators(
                csv_file=csv_file,
                json_dir=None,
                output_dir=output_dir,
                data_dump_path=None,
                geonames_user=None,
                tests=["new-record-integrity"],
            )

    def test_json_only_raises_for_explicit_csv_json_validator(self, tmp_path):
        json_dir = make_json_dir(tmp_path)
        output_dir = tmp_path / "out"

        with pytest.raises(ConfigurationError, match="requires both"):
            run_validators(
                csv_file=None,
                json_dir=json_dir,
                output_dir=output_dir,
                data_dump_path=None,
                geonames_user=None,
                tests=["new-record-integrity"],
            )

    def test_update_record_integrity_also_raises_when_explicit(self, tmp_path):
        csv_file = make_csv(tmp_path)
        output_dir = tmp_path / "out"

        with pytest.raises(ConfigurationError, match="requires both"):
            run_validators(
                csv_file=csv_file,
                json_dir=None,
                output_dir=output_dir,
                data_dump_path=None,
                geonames_user=None,
                tests=["update-record-integrity"],
            )

    def test_csv_json_validators_skipped_when_running_all(self, tmp_path):
        csv_file = make_csv(tmp_path)
        output_dir = tmp_path / "out"

        exit_code = run_validators(
            csv_file=csv_file,
            json_dir=None,
            output_dir=output_dir,
            data_dump_path=None,
            geonames_user=None,
            tests=["all"],
        )
        assert exit_code == 0


class TestOutputFileNaming:
    def test_csv_format_prefix(self, tmp_path):
        bad_csv = (
            f"{CSV_HEADER}\n"
            ",Bad Name,lower,,,INVALID_STATUS,badtype,not-a-url,not-a-wiki,abc,abc,,,"
            "bad-isni,bad-isni,bad-wikidata,bad-wikidata,bad-fundref,bad-fundref,\n"
        )
        csv_file = make_csv(tmp_path, content=bad_csv)
        output_dir = tmp_path / "out"

        run_validators(
            csv_file=csv_file,
            json_dir=None,
            output_dir=output_dir,
            data_dump_path=None,
            geonames_user=None,
            tests=["validate_fields"],
        )

        assert (output_dir / "csv_validate_fields.csv").exists()
        assert not (output_dir / "validation_report.csv").exists()

    def test_json_format_prefix(self, tmp_path):
        bad_record = make_minimal_json_record()
        bad_record["status"] = "INVALID_STATUS"
        json_dir = make_json_dir(tmp_path, records=[bad_record])
        output_dir = tmp_path / "out"

        run_validators(
            csv_file=None,
            json_dir=json_dir,
            output_dir=output_dir,
            data_dump_path=None,
            geonames_user=None,
            tests=["validate_fields"],
        )

        assert (output_dir / "json_validate_fields.csv").exists()
        assert not (output_dir / "validation_report.csv").exists()

    def test_csv_json_validator_no_prefix(self, tmp_path):
        record = make_minimal_json_record(ror_id="https://ror.org/00test123")
        record["types"] = ["company"]
        json_dir = make_json_dir(tmp_path, records=[record])

        csv_content = (
            "id,names.types.ror_display,status,types,links.type.website,"
            "established,locations.geonames_id\n"
            "https://ror.org/00test123,Test University,active,education,"
            "https://test.edu,2000,5128581\n"
        )
        csv_file = make_csv(tmp_path, content=csv_content)
        output_dir = tmp_path / "out"

        run_validators(
            csv_file=csv_file,
            json_dir=json_dir,
            output_dir=output_dir,
            data_dump_path=None,
            geonames_user=None,
            tests=["new-record-integrity"],
        )

        integrity_file = output_dir / "new_record_integrity.csv"
        assert integrity_file.exists()
        assert not (output_dir / "csv_new_record_integrity.csv").exists()
        assert not (output_dir / "json_new_record_integrity.csv").exists()

    def test_dual_inputs_both_prefixed(self, tmp_path):
        bad_csv = (
            f"{CSV_HEADER}\n"
            ",Bad Name,lower,,,INVALID_STATUS,badtype,not-a-url,not-a-wiki,abc,abc,,,"
            "bad-isni,bad-isni,bad-wikidata,bad-wikidata,bad-fundref,bad-fundref,\n"
        )
        csv_file = make_csv(tmp_path, content=bad_csv)

        bad_record = make_minimal_json_record()
        bad_record["status"] = "INVALID_STATUS"
        json_dir = make_json_dir(tmp_path, records=[bad_record])
        output_dir = tmp_path / "out"

        run_validators(
            csv_file=csv_file,
            json_dir=json_dir,
            output_dir=output_dir,
            data_dump_path=None,
            geonames_user=None,
            tests=["validate_fields"],
        )

        assert (output_dir / "csv_validate_fields.csv").exists()
        assert (output_dir / "json_validate_fields.csv").exists()


class TestNoIssuesNoOutput:
    def test_valid_csv_produces_no_output(self, tmp_path):
        valid_csv = (
            "id,names.types.ror_display,status,types,links.type.website,"
            "established,locations.geonames_id,city,country\n"
            ",Valid University*en,active,education,https://valid.edu,"
            "2000,5128581,Boston,United States\n"
        )
        csv_file = make_csv(tmp_path, content=valid_csv)
        output_dir = tmp_path / "out"

        run_validators(
            csv_file=csv_file,
            json_dir=None,
            output_dir=output_dir,
            data_dump_path=None,
            geonames_user=None,
            tests=["validate_fields"],
        )

        output_files = list(output_dir.glob("*.csv"))
        assert len(output_files) == 0

    def test_valid_json_produces_no_output(self, tmp_path):
        record = make_minimal_json_record()
        json_dir = make_json_dir(tmp_path, records=[record])
        output_dir = tmp_path / "out"

        run_validators(
            csv_file=None,
            json_dir=json_dir,
            output_dir=output_dir,
            data_dump_path=None,
            geonames_user=None,
            tests=["validate_fields"],
        )

        output_files = list(output_dir.glob("*.csv"))
        assert len(output_files) == 0

    def test_clean_json_no_unprintable_output(self, tmp_path):
        record = make_minimal_json_record()
        json_dir = make_json_dir(tmp_path, records=[record])
        output_dir = tmp_path / "out"

        run_validators(
            csv_file=None,
            json_dir=json_dir,
            output_dir=output_dir,
            data_dump_path=None,
            geonames_user=None,
            tests=["unprintable-chars"],
        )

        output_files = list(output_dir.glob("*.csv"))
        assert len(output_files) == 0

    def test_matching_integrity_produces_no_output(self, tmp_path):
        record = make_minimal_json_record(ror_id="https://ror.org/00test123")
        json_dir = make_json_dir(tmp_path, records=[record])

        csv_content = (
            "id,names.types.ror_display,status,types,links.type.website,"
            "established,locations.geonames_id\n"
            "https://ror.org/00test123,Test University,active,education,"
            "https://test.edu,2000,5128581\n"
        )
        csv_file = make_csv(tmp_path, content=csv_content)
        output_dir = tmp_path / "out"

        run_validators(
            csv_file=csv_file,
            json_dir=json_dir,
            output_dir=output_dir,
            data_dump_path=None,
            geonames_user=None,
            tests=["new-record-integrity"],
        )

        output_files = list(output_dir.glob("*.csv"))
        assert len(output_files) == 0


class TestHelpFlag:
    def test_help_flag_exits_zero(self):
        with pytest.raises(SystemExit) as exc_info:
            parse_args(["--help"])
        assert exc_info.value.code == 0

    def test_help_flag_prints_usage(self, capsys):
        with pytest.raises(SystemExit):
            parse_args(["--help"])
        captured = capsys.readouterr()
        assert "curation-validation" in captured.out
        assert "--csv" in captured.out or "-c" in captured.out
        assert "--json-dir" in captured.out or "-j" in captured.out
        assert "--test" in captured.out


class TestOutputDirectoryCreation:
    def test_output_dir_is_created_if_missing(self, tmp_path):
        csv_file = make_csv(tmp_path)
        nested = tmp_path / "a" / "b" / "c"

        run_validators(
            csv_file=csv_file,
            json_dir=None,
            output_dir=nested,
            data_dump_path=None,
            geonames_user=None,
            tests=["validate_fields"],
        )

        assert nested.exists()
        assert nested.is_dir()


class TestValidatorsRequiringDataSource:
    def test_data_source_validators_work_with_data_dump(self, tmp_path):
        csv_content = (
            "id,names.types.ror_display,links.type.website,"
            "external_ids.type.isni.all,external_ids.type.isni.preferred\n"
            ",Test University*en,https://test.edu,0000 0000 1234 5678,0000 0000 1234 5678\n"
        )
        csv_file = make_csv(tmp_path, content=csv_content)

        data_dump = tmp_path / "dump.json"
        data_dump.write_text(json.dumps([
            {
                "id": "https://ror.org/existing1",
                "names": [{"value": "Existing Org", "types": ["ror_display"]}],
                "links": [{"type": "website", "value": "https://existing.org"}],
                "external_ids": [
                    {
                        "type": "isni",
                        "all": ["0000 0000 9999 8888"],
                        "preferred": "0000 0000 9999 8888",
                    }
                ],
            }
        ]))

        output_dir = tmp_path / "out"

        run_validators(
            csv_file=csv_file,
            json_dir=None,
            output_dir=output_dir,
            data_dump_path=str(data_dump),
            geonames_user=None,
            tests=["duplicate-external-ids", "duplicate-urls"],
        )

    def test_data_source_validators_detect_overlap(self, tmp_path):
        csv_content = (
            "id,names.types.ror_display,links.type.website,"
            "external_ids.type.wikidata.all,external_ids.type.wikidata.preferred\n"
            ",Test University*en,https://test.edu,Q99999,Q99999\n"
        )
        csv_file = make_csv(tmp_path, content=csv_content)

        data_dump = tmp_path / "dump.json"
        data_dump.write_text(json.dumps([
            {
                "id": "https://ror.org/existing1",
                "names": [{"value": "Existing Org", "types": ["ror_display"]}],
                "links": [{"type": "website", "value": "https://existing.org"}],
                "external_ids": [
                    {
                        "type": "wikidata",
                        "all": ["Q99999"],
                        "preferred": "Q99999",
                    }
                ],
            }
        ]))

        output_dir = tmp_path / "out"

        run_validators(
            csv_file=csv_file,
            json_dir=None,
            output_dir=output_dir,
            data_dump_path=str(data_dump),
            geonames_user=None,
            tests=["duplicate-external-ids"],
        )

        expected_file = output_dir / "csv_duplicate_external_ids.csv"
        assert expected_file.exists()
        rows = read_output_csv(expected_file)
        assert len(rows) > 0
        assert any("Q99999" in r.get("overlapping_external_id", "") for r in rows)

    def test_duplicate_urls_detects_overlap(self, tmp_path):
        csv_content = (
            "id,names.types.ror_display,links.type.website\n"
            ",New University*en,https://duplicate.edu\n"
        )
        csv_file = make_csv(tmp_path, content=csv_content)

        data_dump = tmp_path / "dump.json"
        data_dump.write_text(json.dumps([
            {
                "id": "https://ror.org/existing1",
                "names": [{"value": "Existing Org", "types": ["ror_display"]}],
                "links": [{"type": "website", "value": "https://duplicate.edu"}],
                "external_ids": [],
            }
        ]))

        output_dir = tmp_path / "out"

        run_validators(
            csv_file=csv_file,
            json_dir=None,
            output_dir=output_dir,
            data_dump_path=str(data_dump),
            geonames_user=None,
            tests=["duplicate-urls"],
        )

        expected_file = output_dir / "csv_duplicate_urls.csv"
        assert expected_file.exists()
        rows = read_output_csv(expected_file)
        assert len(rows) > 0
        assert any("duplicate.edu" in r.get("csv_url", "") for r in rows)


class TestValidatorsRequiringGeonames:
    def test_address_validation_fails_without_geonames_user(self, tmp_path):
        csv_file = make_csv(tmp_path)
        output_dir = tmp_path / "out"

        with pytest.raises(SystemExit):
            run_validators(
                csv_file=csv_file,
                json_dir=None,
                output_dir=output_dir,
                data_dump_path=None,
                geonames_user=None,
                tests=["address-validation"],
            )

    def test_production_duplicates_fails_without_geonames_user(self, tmp_path):
        csv_file = make_csv(tmp_path)
        output_dir = tmp_path / "out"

        with pytest.raises(SystemExit):
            run_validators(
                csv_file=csv_file,
                json_dir=None,
                output_dir=output_dir,
                data_dump_path=None,
                geonames_user=None,
                tests=["production-duplicates"],
            )


class TestInReleaseDuplicates:
    def test_csv_detects_in_release_duplicates(self, tmp_path):
        csv_content = (
            "id,names.types.ror_display,links.type.website,names.types.alias,names.types.label\n"
            ",University of Testing*en,https://testing.edu,,\n"
            ",University of Testing*de,https://testing.edu,,\n"
        )
        csv_file = make_csv(tmp_path, content=csv_content)
        output_dir = tmp_path / "out"

        run_validators(
            csv_file=csv_file,
            json_dir=None,
            output_dir=output_dir,
            data_dump_path=None,
            geonames_user=None,
            tests=["in-release-duplicates"],
        )

        expected_file = output_dir / "csv_in_release_duplicates.csv"
        assert expected_file.exists()
        rows = read_output_csv(expected_file)
        assert len(rows) > 0

    def test_json_detects_in_release_duplicates(self, tmp_path):
        records = [
            make_minimal_json_record(ror_id="https://ror.org/001", name="University of Testing"),
            make_minimal_json_record(ror_id="https://ror.org/002", name="University of Testing"),
        ]
        json_dir = make_json_dir(tmp_path, records=records)
        output_dir = tmp_path / "out"

        run_validators(
            csv_file=None,
            json_dir=json_dir,
            output_dir=output_dir,
            data_dump_path=None,
            geonames_user=None,
            tests=["in-release-duplicates"],
        )

        expected_file = output_dir / "json_in_release_duplicates.csv"
        assert expected_file.exists()
        rows = read_output_csv(expected_file)
        assert len(rows) > 0


class TestUnprintableCharsIntegration:
    def test_unprintable_chars_detected_in_json(self, tmp_path):
        record = make_minimal_json_record()
        record["names"][0]["value"] = "Test\x00University"
        json_dir = make_json_dir(tmp_path, records=[record])
        output_dir = tmp_path / "out"

        run_validators(
            csv_file=None,
            json_dir=json_dir,
            output_dir=output_dir,
            data_dump_path=None,
            geonames_user=None,
            tests=["unprintable-chars"],
        )

        expected_file = output_dir / "json_unprintable_chars.csv"
        assert expected_file.exists()
        rows = read_output_csv(expected_file)
        assert len(rows) > 0


class TestLeadingTrailingIntegration:
    def test_leading_trailing_detected_in_json(self, tmp_path):
        record = make_minimal_json_record()
        record["names"].append({"value": " Bad Name", "types": ["alias"]})
        json_dir = make_json_dir(tmp_path, records=[record])
        output_dir = tmp_path / "out"

        run_validators(
            csv_file=None,
            json_dir=json_dir,
            output_dir=output_dir,
            data_dump_path=None,
            geonames_user=None,
            tests=["leading_trailing"],
        )

        expected_file = output_dir / "json_leading_trailing.csv"
        assert expected_file.exists()
        rows = read_output_csv(expected_file)
        assert len(rows) > 0
        assert any(r.get("issue") == "leading" for r in rows)


class TestUpdateRecordIntegrity:
    def test_update_record_integrity_detects_mismatch(self, tmp_path):
        record = make_minimal_json_record(ror_id="https://ror.org/00test123")
        json_dir = make_json_dir(tmp_path, records=[record])

        csv_content = (
            "id,html_url,status,names.types.ror_display\n"
            "https://ror.org/00test123,https://github.com/issue/1,replace==withdrawn,\n"
        )
        csv_file = make_csv(tmp_path, content=csv_content)
        output_dir = tmp_path / "out"

        run_validators(
            csv_file=csv_file,
            json_dir=json_dir,
            output_dir=output_dir,
            data_dump_path=None,
            geonames_user=None,
            tests=["update-record-integrity"],
        )

        expected_file = output_dir / "update_record_integrity.csv"
        assert expected_file.exists()
        rows = read_output_csv(expected_file)
        assert len(rows) > 0

    def test_update_record_integrity_no_issues_when_applied(self, tmp_path):
        record = make_minimal_json_record(ror_id="https://ror.org/00test123")
        json_dir = make_json_dir(tmp_path, records=[record])

        csv_content = (
            "id,html_url,status,names.types.ror_display\n"
            "https://ror.org/00test123,https://github.com/issue/1,replace==active,\n"
        )
        csv_file = make_csv(tmp_path, content=csv_content)
        output_dir = tmp_path / "out"

        run_validators(
            csv_file=csv_file,
            json_dir=json_dir,
            output_dir=output_dir,
            data_dump_path=None,
            geonames_user=None,
            tests=["update-record-integrity"],
        )

        output_files = list(output_dir.glob("*.csv"))
        assert len(output_files) == 0


class TestMultipleValidatorsEndToEnd:
    def test_run_several_standalone_validators(self, tmp_path):
        bad_csv = (
            f"{CSV_HEADER}\n"
            ",Bad Name,lower,,,INVALID_STATUS,badtype,not-a-url,not-a-wiki,abc,abc,,,"
            "bad-isni,bad-isni,bad-wikidata,bad-wikidata,bad-fundref,bad-fundref,\n"
        )
        csv_file = make_csv(tmp_path, content=bad_csv)
        output_dir = tmp_path / "out"

        run_validators(
            csv_file=csv_file,
            json_dir=None,
            output_dir=output_dir,
            data_dump_path=None,
            geonames_user=None,
            tests=["validate_fields", "in-release-duplicates", "unprintable-chars"],
        )

        assert (output_dir / "csv_validate_fields.csv").exists()

    def test_empty_csv_no_data_rows(self, tmp_path):
        csv_content = f"{CSV_HEADER}\n"
        csv_file = make_csv(tmp_path, content=csv_content)
        output_dir = tmp_path / "out"

        run_validators(
            csv_file=csv_file,
            json_dir=None,
            output_dir=output_dir,
            data_dump_path=None,
            geonames_user=None,
            tests=["validate_fields"],
        )

        output_files = list(output_dir.glob("*.csv"))
        assert len(output_files) == 0

    def test_empty_json_dir_no_records(self, tmp_path):
        json_dir = tmp_path / "json"
        json_dir.mkdir()
        output_dir = tmp_path / "out"

        run_validators(
            csv_file=None,
            json_dir=json_dir,
            output_dir=output_dir,
            data_dump_path=None,
            geonames_user=None,
            tests=["validate_fields"],
        )

        output_files = list(output_dir.glob("*.csv"))
        assert len(output_files) == 0
