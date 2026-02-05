from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import pytest

from validate_ror_records_input_csvs.validators.base import BaseValidator, ValidatorContext
from validate_ror_records_input_csvs.core.loader import DataSource


class TestValidatorContext:
    def test_create_context(self, tmp_path):
        ctx = ValidatorContext(
            input_file=tmp_path / "input.csv",
            output_dir=tmp_path,
            data_source=None,
            geonames_user=None,
        )
        assert ctx.input_file == tmp_path / "input.csv"
        assert ctx.data_source is None


class TestBaseValidator:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            BaseValidator()

    def test_concrete_validator_must_implement_run(self):
        class IncompleteValidator(BaseValidator):
            name = "incomplete"
            output_filename = "output.csv"
            output_fields = ["field"]

        with pytest.raises(TypeError):
            IncompleteValidator()

    def test_concrete_validator_works(self, tmp_path):
        class ConcreteValidator(BaseValidator):
            name = "concrete"
            output_filename = "output.csv"
            output_fields = ["id", "error"]

            def run(self, ctx: ValidatorContext) -> list[dict]:
                return [{"id": "1", "error": "test"}]

        validator = ConcreteValidator()
        ctx = ValidatorContext(
            input_file=tmp_path / "input.csv",
            output_dir=tmp_path,
            data_source=None,
            geonames_user=None,
        )
        results = validator.run(ctx)
        assert len(results) == 1

    def test_can_run_no_requirements(self, tmp_path):
        class SimpleValidator(BaseValidator):
            name = "simple"
            output_filename = "output.csv"
            output_fields = ["field"]
            requires_data_source = False
            requires_geonames = False

            def run(self, ctx):
                return []

        validator = SimpleValidator()
        ctx = ValidatorContext(
            input_file=tmp_path / "input.csv",
            output_dir=tmp_path,
            data_source=None,
            geonames_user=None,
        )
        can_run, reason = validator.can_run(ctx)
        assert can_run is True
        assert reason == ""

    def test_can_run_missing_geonames(self, tmp_path):
        class NeedsGeoValidator(BaseValidator):
            name = "needs-geo"
            output_filename = "output.csv"
            output_fields = ["field"]
            requires_geonames = True

            def run(self, ctx):
                return []

        validator = NeedsGeoValidator()
        ctx = ValidatorContext(
            input_file=tmp_path / "input.csv",
            output_dir=tmp_path,
            data_source=None,
            geonames_user=None,
        )
        can_run, reason = validator.can_run(ctx)
        assert can_run is False
        assert "geonames" in reason.lower()
