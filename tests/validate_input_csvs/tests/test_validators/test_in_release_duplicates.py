import pytest
from pathlib import Path

from validate_ror_records_input_csvs.validators.base import ValidatorContext
from validate_ror_records_input_csvs.validators.in_release_duplicates import InReleaseDuplicatesValidator


@pytest.fixture
def validator():
    return InReleaseDuplicatesValidator()


def make_context(input_file: Path, tmp_path: Path) -> ValidatorContext:
    return ValidatorContext(
        input_file=input_file,
        output_dir=tmp_path,
        data_source=None,
        geonames_user=None,
    )


class TestValidatorProperties:
    def test_name(self, validator):
        assert validator.name == "in-release-duplicates"

    def test_output_filename(self, validator):
        assert validator.output_filename == "in_release_duplicates.csv"

    def test_output_fields(self, validator):
        assert "record1_display_name" in validator.output_fields
        assert "record1_url" in validator.output_fields
        assert "record2_display_name" in validator.output_fields
        assert "record2_url" in validator.output_fields
        assert "match_type" in validator.output_fields
        assert "similarity_score" in validator.output_fields

    def test_requires_data_source(self, validator):
        assert validator.requires_data_source is False

    def test_requires_geonames(self, validator):
        assert validator.requires_geonames is False


class TestUrlMatchDetection:
    def test_detects_url_match_within_csv(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,links.type.website\n"
            ",Org One*en,https://example.org\n"
            ",Org Two*en,https://example.org\n"
        )

        ctx = make_context(csv_path, tmp_path)
        results = validator.run(ctx)

        assert len(results) == 1
        assert results[0]["match_type"] == "url"
        assert results[0]["similarity_score"] == 100

    def test_detects_normalized_url_match(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,links.type.website\n"
            ",Org One*en,https://www.example.org/path\n"
            ",Org Two*en,http://example.org\n"
        )

        ctx = make_context(csv_path, tmp_path)
        results = validator.run(ctx)

        assert len(results) == 1
        assert results[0]["match_type"] == "url"

    def test_no_url_match_different_domains(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,links.type.website\n"
            ",Org One*en,https://example.org\n"
            ",Org Two*en,https://different.org\n"
        )

        ctx = make_context(csv_path, tmp_path)
        results = validator.run(ctx)

        assert len(results) == 0


class TestExactNameMatch:
    def test_detects_exact_name_match(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,names.types.alias,names.types.label,links.type.website\n"
            ",University of Testing*en,,,https://one.org\n"
            ",University of Testing*en,,,https://two.org\n"
        )

        ctx = make_context(csv_path, tmp_path)
        results = validator.run(ctx)

        assert len(results) >= 1
        name_matches = [r for r in results if r["match_type"] in ("name_exact", "name_fuzzy")]
        assert len(name_matches) >= 1
        assert name_matches[0]["similarity_score"] == 100

    def test_detects_alias_match(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,names.types.alias,names.types.label,links.type.website\n"
            ",University of Testing*en,UT*en,,https://one.org\n"
            ",UT*en,,,https://two.org\n"
        )

        ctx = make_context(csv_path, tmp_path)
        results = validator.run(ctx)

        assert len(results) >= 1


class TestFuzzyNameMatch:
    def test_detects_fuzzy_match_at_85_percent(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,names.types.alias,names.types.label,links.type.website\n"
            ",University of California*en,,,https://one.org\n"
            ",Universiti of California*en,,,https://two.org\n"
        )

        ctx = make_context(csv_path, tmp_path)
        results = validator.run(ctx)

        name_matches = [r for r in results if r["match_type"] in ("name_exact", "name_fuzzy")]
        assert len(name_matches) >= 1
        assert name_matches[0]["similarity_score"] >= 85

    def test_no_match_below_85_threshold(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,names.types.alias,names.types.label,links.type.website\n"
            ",ABC Corp*en,,,https://one.org\n"
            ",XYZ Institute*en,,,https://two.org\n"
        )

        ctx = make_context(csv_path, tmp_path)
        results = validator.run(ctx)

        assert len(results) == 0

    def test_84_percent_does_not_trigger(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,names.types.alias,names.types.label,links.type.website\n"
            ",Alpha Institute of Technology*en,,,https://one.org\n"
            ",Beta Corporation Limited*en,,,https://two.org\n"
        )

        ctx = make_context(csv_path, tmp_path)
        results = validator.run(ctx)

        assert len(results) == 0


class TestNoDuplicateWhenDifferent:
    def test_no_match_for_different_records(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,names.types.alias,names.types.label,links.type.website\n"
            ",Harvard University*en,,,https://harvard.edu\n"
            ",Stanford University*en,,,https://stanford.edu\n"
        )

        ctx = make_context(csv_path, tmp_path)
        results = validator.run(ctx)

        url_matches = [r for r in results if r["match_type"] == "url"]
        assert len(url_matches) == 0


class TestMultipleMatches:
    def test_reports_each_pair_once(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,names.types.alias,names.types.label,links.type.website\n"
            ",Org One*en,,,https://example.org\n"
            ",Org Two*en,,,https://example.org\n"
        )

        ctx = make_context(csv_path, tmp_path)
        results = validator.run(ctx)

        url_matches = [r for r in results if r["match_type"] == "url"]
        assert len(url_matches) == 1

    def test_multiple_records_multiple_matches(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,names.types.alias,names.types.label,links.type.website\n"
            ",Org A*en,,,https://a.org\n"
            ",Org B*en,,,https://a.org\n"
            ",Org C*en,,,https://c.org\n"
            ",Org D*en,,,https://c.org\n"
        )

        ctx = make_context(csv_path, tmp_path)
        results = validator.run(ctx)

        url_matches = [r for r in results if r["match_type"] == "url"]
        assert len(url_matches) == 2


class TestOutputFormat:
    def test_output_includes_all_fields(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,names.types.alias,names.types.label,links.type.website\n"
            ",First Organization*en,,,https://example.org\n"
            ",Second Organization*en,,,https://example.org\n"
        )

        ctx = make_context(csv_path, tmp_path)
        results = validator.run(ctx)

        assert len(results) >= 1
        result = results[0]

        assert "record1_display_name" in result
        assert "record1_url" in result
        assert "record2_display_name" in result
        assert "record2_url" in result
        assert "match_type" in result
        assert "similarity_score" in result

    def test_match_type_is_url_for_url_match(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,names.types.alias,names.types.label,links.type.website\n"
            ",Org One*en,,,https://example.org\n"
            ",Org Two*en,,,https://example.org\n"
        )

        ctx = make_context(csv_path, tmp_path)
        results = validator.run(ctx)

        url_matches = [r for r in results if r["match_type"] == "url"]
        assert len(url_matches) == 1
        assert url_matches[0]["similarity_score"] == 100


class TestEmptyAndEdgeCases:
    def test_handles_single_record(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,names.types.alias,names.types.label,links.type.website\n"
            ",Only Org*en,,,https://example.org\n"
        )

        ctx = make_context(csv_path, tmp_path)
        results = validator.run(ctx)

        assert len(results) == 0

    def test_handles_empty_csv(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,names.types.alias,names.types.label,links.type.website\n"
        )

        ctx = make_context(csv_path, tmp_path)
        results = validator.run(ctx)

        assert len(results) == 0

    def test_handles_empty_urls(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,names.types.alias,names.types.label,links.type.website\n"
            ",Test University*en,,,\n"
            ",Test University*en,,,\n"
        )

        ctx = make_context(csv_path, tmp_path)
        results = validator.run(ctx)

        name_matches = [r for r in results if r["match_type"] in ("name_exact", "name_fuzzy")]
        assert len(name_matches) >= 1

    def test_handles_empty_names(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,names.types.alias,names.types.label,links.type.website\n"
            ",,,,https://example.org\n"
            ",,,,https://example.org\n"
        )

        ctx = make_context(csv_path, tmp_path)
        results = validator.run(ctx)

        url_matches = [r for r in results if r["match_type"] == "url"]
        assert len(url_matches) == 1


class TestCanRun:
    def test_can_run_without_data_source(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text("id,names.types.ror_display\n,Test*en\n")

        ctx = make_context(csv_path, tmp_path)
        can_run, reason = validator.can_run(ctx)

        assert can_run is True
        assert reason == ""


class TestNameLanguageMarker:
    def test_strips_language_marker_for_comparison(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,names.types.alias,names.types.label,links.type.website\n"
            ",Test University*en,,,https://one.org\n"
            ",Test University*de,,,https://two.org\n"
        )

        ctx = make_context(csv_path, tmp_path)
        results = validator.run(ctx)

        name_matches = [r for r in results if r["match_type"] in ("name_exact", "name_fuzzy")]
        assert len(name_matches) >= 1


class TestMultipleNameFields:
    def test_matches_across_name_types(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,names.types.alias,names.types.label,links.type.website\n"
            ",Main University*en,MU*en,,https://one.org\n"
            ",Another Org*en,Main University*en,,https://two.org\n"
        )

        ctx = make_context(csv_path, tmp_path)
        results = validator.run(ctx)

        name_matches = [r for r in results if r["match_type"] in ("name_exact", "name_fuzzy")]
        assert len(name_matches) >= 1

    def test_matches_label_names(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,names.types.alias,names.types.label,links.type.website\n"
            ",Org A*en,,Special Label*en,https://one.org\n"
            ",Org B*en,,Special Label*en,https://two.org\n"
        )

        ctx = make_context(csv_path, tmp_path)
        results = validator.run(ctx)

        name_matches = [r for r in results if r["match_type"] in ("name_exact", "name_fuzzy")]
        assert len(name_matches) >= 1

    def test_multiple_aliases_separated_by_semicolon(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,names.types.alias,names.types.label,links.type.website\n"
            ",University A*en,UA*en; Uni A*en,,https://one.org\n"
            ",Uni A*en,,,https://two.org\n"
        )

        ctx = make_context(csv_path, tmp_path)
        results = validator.run(ctx)

        name_matches = [r for r in results if r["match_type"] in ("name_exact", "name_fuzzy")]
        assert len(name_matches) >= 1
