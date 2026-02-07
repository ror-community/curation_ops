from pathlib import Path
from dataclasses import FrozenInstanceError

import pytest

from curation_validation.validators.base import BaseValidator, ValidatorContext


class ConcreteValidator(BaseValidator):
    name = "test-validator"
    supported_formats = {"csv", "json"}
    output_filename = "test_output.csv"
    output_fields = ["field1", "field2"]

    def run(self, ctx: ValidatorContext) -> list[dict]:
        return []


class TestValidatorContext:
    def test_creates_with_csv_only(self, tmp_path):
        ctx = ValidatorContext(
            csv_file=tmp_path / "test.csv",
            json_dir=None,
            output_dir=tmp_path,
            data_source=None,
            geonames_user=None,
        )
        assert ctx.csv_file is not None
        assert ctx.json_dir is None

    def test_creates_with_json_only(self, tmp_path):
        ctx = ValidatorContext(
            csv_file=None,
            json_dir=tmp_path / "json",
            output_dir=tmp_path,
            data_source=None,
            geonames_user=None,
        )
        assert ctx.json_dir is not None
        assert ctx.csv_file is None

    def test_creates_with_both(self, tmp_path):
        ctx = ValidatorContext(
            csv_file=tmp_path / "test.csv",
            json_dir=tmp_path / "json",
            output_dir=tmp_path,
            data_source=None,
            geonames_user=None,
        )
        assert ctx.csv_file is not None
        assert ctx.json_dir is not None


class TestBaseValidator:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            BaseValidator()

    def test_concrete_has_name(self):
        v = ConcreteValidator()
        assert v.name == "test-validator"

    def test_concrete_has_supported_formats(self):
        v = ConcreteValidator()
        assert v.supported_formats == {"csv", "json"}

    def test_can_run_default(self, tmp_path):
        v = ConcreteValidator()
        ctx = ValidatorContext(
            csv_file=None, json_dir=None, output_dir=tmp_path,
            data_source=None, geonames_user=None,
        )
        can, reason = v.can_run(ctx)
        assert can is True

    def test_can_run_requires_geonames(self, tmp_path):
        v = ConcreteValidator()
        v.requires_geonames = True
        ctx = ValidatorContext(
            csv_file=None, json_dir=None, output_dir=tmp_path,
            data_source=None, geonames_user=None,
        )
        can, reason = v.can_run(ctx)
        assert can is False
        assert "geonames" in reason.lower()

    def test_can_run_requires_data_source(self, tmp_path):
        v = ConcreteValidator()
        v.requires_data_source = True
        ctx = ValidatorContext(
            csv_file=None, json_dir=None, output_dir=tmp_path,
            data_source=None, geonames_user=None,
        )
        can, reason = v.can_run(ctx)
        assert can is False
        assert "data" in reason.lower()
