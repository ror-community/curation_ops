import pytest
from pathlib import Path

from validate_ror_records_input_csvs.validators.base import ValidatorContext
from validate_ror_records_input_csvs.validators.duplicate_external_ids import DuplicateExternalIdsValidator
from validate_ror_records_input_csvs.core.loader import DataSource


@pytest.fixture
def validator():
    return DuplicateExternalIdsValidator()


def make_context(
    input_file: Path,
    tmp_path: Path,
    data_source: DataSource = None,
) -> ValidatorContext:
    return ValidatorContext(
        input_file=input_file,
        output_dir=tmp_path,
        data_source=data_source,
        geonames_user=None,
    )


class TestValidatorProperties:
    def test_name(self, validator):
        assert validator.name == "duplicate-external-ids"

    def test_output_filename(self, validator):
        assert validator.output_filename == "duplicate_external_ids.csv"

    def test_output_fields(self, validator):
        assert "id" in validator.output_fields
        assert "ror_display_name" in validator.output_fields
        assert "data_dump_id" in validator.output_fields
        assert "data_dump_ror_display_name" in validator.output_fields
        assert "overlapping_external_id" in validator.output_fields

    def test_requires_data_source(self, validator):
        assert validator.requires_data_source is True

    def test_requires_geonames(self, validator):
        assert validator.requires_geonames is False


class TestISNIOverlap:
    def test_finds_isni_overlap(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,external_ids.type.isni.all\n"
            ",Test Org*en,0000 0001 2345 6789\n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "external_ids": [{"type": "isni", "all": ["0000 0001 2345 6789"]}],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 1
        assert "0000 0001 2345 6789" in results[0]["overlapping_external_id"]
        assert results[0]["data_dump_id"] == "https://ror.org/existing"

    def test_no_isni_overlap(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,external_ids.type.isni.all\n"
            ",Test Org*en,0000 0001 2345 6789\n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "external_ids": [{"type": "isni", "all": ["0000 9999 8888 7777"]}],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 0


class TestWikidataOverlap:
    def test_finds_wikidata_overlap(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,external_ids.type.wikidata.all\n"
            ",Test Org*en,Q12345\n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "external_ids": [{"type": "wikidata", "all": ["Q12345"]}],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 1
        assert results[0]["overlapping_external_id"] == "Q12345"


class TestFundRefOverlap:
    def test_finds_fundref_overlap(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,external_ids.type.fundref.all\n"
            ",Test Org*en,100000001\n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "external_ids": [{"type": "fundref", "all": ["100000001"]}],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 1
        assert results[0]["overlapping_external_id"] == "100000001"


class TestPreferredIdOverlap:
    def test_finds_preferred_id_overlap(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,external_ids.type.isni.preferred\n"
            ",Test Org*en,0000 0001 2345 6789\n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "external_ids": [{"type": "isni", "preferred": "0000 0001 2345 6789", "all": []}],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 1


class TestWhitespaceNormalization:
    def test_normalizes_whitespace_for_isni(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,external_ids.type.isni.all\n"
            ",Test Org*en,0000  0001 2345 6789\n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "external_ids": [{"type": "isni", "all": ["0000 0001 2345 6789"]}],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 1

    def test_normalizes_leading_trailing_whitespace(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,external_ids.type.wikidata.all\n"
            ",Test Org*en, Q12345 \n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "external_ids": [{"type": "wikidata", "all": ["Q12345"]}],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 1


class TestMultipleExternalIds:
    def test_finds_multiple_overlaps_in_single_record(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,external_ids.type.isni.all,external_ids.type.wikidata.all\n"
            ",Test Org*en,0000 0001 2345 6789,Q12345\n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "external_ids": [
                {"type": "isni", "all": ["0000 0001 2345 6789"]},
                {"type": "wikidata", "all": ["Q12345"]},
            ],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 2
        overlap_ids = {r["overlapping_external_id"] for r in results}
        assert "0000 0001 2345 6789" in overlap_ids
        assert "Q12345" in overlap_ids

    def test_semicolon_separated_ids(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,external_ids.type.isni.all\n"
            ",Test Org*en,0000 0001 1111 1111;0000 0001 2345 6789\n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "external_ids": [{"type": "isni", "all": ["0000 0001 2345 6789"]}],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 1
        assert results[0]["overlapping_external_id"] == "0000 0001 2345 6789"


class TestMultipleRecords:
    def test_multiple_csv_records(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,external_ids.type.wikidata.all\n"
            ",Org One*en,Q11111\n"
            ",Org Two*en,Q22222\n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "external_ids": [{"type": "wikidata", "all": ["Q22222"]}],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 1
        assert results[0]["ror_display_name"] == "Org Two*en"


class TestOutputFormat:
    def test_output_includes_all_fields(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,external_ids.type.isni.all\n"
            "https://ror.org/csv123,CSV Org*en,0000 0001 2345 6789\n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "external_ids": [{"type": "isni", "all": ["0000 0001 2345 6789"]}],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 1
        result = results[0]
        assert result["id"] == "https://ror.org/csv123"
        assert result["ror_display_name"] == "CSV Org*en"
        assert result["data_dump_id"] == "https://ror.org/existing"
        assert result["data_dump_ror_display_name"] == "Existing Org"
        assert result["overlapping_external_id"] == "0000 0001 2345 6789"


class TestEmptyAndMissingData:
    def test_empty_external_ids_in_csv(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,external_ids.type.isni.all\n"
            ",Test Org*en,\n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "external_ids": [{"type": "isni", "all": ["0000 0001 2345 6789"]}],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 0

    def test_no_external_ids_in_data_source(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,external_ids.type.isni.all\n"
            ",Test Org*en,0000 0001 2345 6789\n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "external_ids": [],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 0

    def test_missing_names_in_csv_record(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,external_ids.type.wikidata.all\n"
            ",Q12345\n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "external_ids": [{"type": "wikidata", "all": ["Q12345"]}],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 1
        assert results[0]["ror_display_name"] == ""


class TestGridId:
    def test_finds_grid_overlap(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,external_ids.type.grid.all\n"
            ",Test Org*en,grid.12345.a\n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "external_ids": [{"type": "grid", "all": ["grid.12345.a"]}],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 1
        assert results[0]["overlapping_external_id"] == "grid.12345.a"


class TestCanRun:
    def test_can_run_with_data_source(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text("id,names.types.ror_display\n,Test*en\n")
        data_source = DataSource([])

        ctx = make_context(csv_path, tmp_path, data_source)
        can_run, reason = validator.can_run(ctx)

        assert can_run is True
        assert reason == ""
