import json
from pathlib import Path

import pytest

from curation_validation.core.exceptions import ConfigurationError
from curation_validation.validators.base import BaseValidator, ValidatorContext
from curation_validation.runner import (
    register_validator,
    run_validators,
    VALIDATORS,
    determine_available_formats,
)


class FakeCsvValidator(BaseValidator):
    name = "fake-csv"
    supported_formats = {"csv"}
    output_filename = "fake_csv.csv"
    output_fields = ["error"]

    def run(self, ctx: ValidatorContext) -> list[dict]:
        return [{"error": "csv issue"}]


class FakeJsonValidator(BaseValidator):
    name = "fake-json"
    supported_formats = {"json"}
    output_filename = "fake_json.csv"
    output_fields = ["error"]

    def run(self, ctx: ValidatorContext) -> list[dict]:
        return [{"error": "json issue"}]


class FakeDualValidator(BaseValidator):
    name = "fake-dual"
    supported_formats = {"csv", "json"}
    output_filename = "fake_dual.csv"
    output_fields = ["error"]

    def __init__(self):
        self.run_count = 0

    def run(self, ctx: ValidatorContext) -> list[dict]:
        self.run_count += 1
        return []


class FakeCsvJsonValidator(BaseValidator):
    name = "fake-integrity"
    supported_formats = {"csv_json"}
    output_filename = "fake_integrity.csv"
    output_fields = ["error"]

    def run(self, ctx: ValidatorContext) -> list[dict]:
        return []


class TestDetermineAvailableFormats:
    def test_csv_only(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a,b\n1,2\n")
        result = determine_available_formats(csv_file=csv_file, json_dir=None)
        assert result == {"csv"}

    def test_json_only(self, tmp_path):
        json_dir = tmp_path / "json"
        json_dir.mkdir()
        result = determine_available_formats(csv_file=None, json_dir=json_dir)
        assert result == {"json"}

    def test_both(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a,b\n1,2\n")
        json_dir = tmp_path / "json"
        json_dir.mkdir()
        result = determine_available_formats(csv_file=csv_file, json_dir=json_dir)
        assert result == {"csv", "json", "csv_json"}

    def test_neither(self):
        result = determine_available_formats(csv_file=None, json_dir=None)
        assert result == set()


class TestRegisterValidator:
    def test_registers(self):
        VALIDATORS.clear()
        v = FakeCsvValidator()
        register_validator(v)
        assert "fake-csv" in VALIDATORS
        VALIDATORS.clear()


class TestRunValidators:
    def test_runs_csv_validator_with_csv_input(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a,b\n1,2\n")
        VALIDATORS.clear()
        register_validator(FakeCsvValidator())
        exit_code = run_validators(
            csv_file=csv_file, json_dir=None,
            output_dir=tmp_path / "out", data_dump_path=None,
            geonames_user=None, tests=["all"],
        )
        assert (tmp_path / "out" / "csv_fake_csv.csv").exists()
        VALIDATORS.clear()

    def test_skips_csv_validator_with_json_input(self, tmp_path):
        json_dir = tmp_path / "json"
        json_dir.mkdir()
        VALIDATORS.clear()
        register_validator(FakeCsvValidator())
        exit_code = run_validators(
            csv_file=None, json_dir=json_dir,
            output_dir=tmp_path / "out", data_dump_path=None,
            geonames_user=None, tests=["all"],
        )
        assert not (tmp_path / "out" / "csv_fake_csv.csv").exists()
        VALIDATORS.clear()

    def test_csv_json_validator_errors_without_both(self, tmp_path):
        json_dir = tmp_path / "json"
        json_dir.mkdir()
        VALIDATORS.clear()
        register_validator(FakeCsvJsonValidator())
        with pytest.raises(ConfigurationError):
            run_validators(
                csv_file=None, json_dir=json_dir,
                output_dir=tmp_path / "out", data_dump_path=None,
                geonames_user=None, tests=["fake-integrity"],
            )
        VALIDATORS.clear()

    def test_dual_format_runs_once_per_format(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a,b\n1,2\n")
        json_dir = tmp_path / "json"
        json_dir.mkdir()
        dual = FakeDualValidator()
        VALIDATORS.clear()
        register_validator(dual)
        run_validators(
            csv_file=csv_file, json_dir=json_dir,
            output_dir=tmp_path / "out", data_dump_path=None,
            geonames_user=None, tests=["all"],
        )
        assert dual.run_count == 2
        VALIDATORS.clear()

    def test_unknown_validator_warns(self, tmp_path, capsys):
        VALIDATORS.clear()
        run_validators(
            csv_file=None, json_dir=None,
            output_dir=tmp_path / "out", data_dump_path=None,
            geonames_user=None, tests=["nonexistent"],
        )
        captured = capsys.readouterr()
        assert "Unknown" in captured.err or "unknown" in captured.err.lower()
        VALIDATORS.clear()
