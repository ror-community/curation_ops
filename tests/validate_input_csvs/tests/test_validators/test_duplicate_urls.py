import pytest
from pathlib import Path

from validate_ror_records_input_csvs.validators.base import ValidatorContext
from validate_ror_records_input_csvs.validators.duplicate_urls import DuplicateUrlsValidator
from validate_ror_records_input_csvs.core.loader import DataSource


@pytest.fixture
def validator():
    return DuplicateUrlsValidator()


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
        assert validator.name == "duplicate-urls"

    def test_output_filename(self, validator):
        assert validator.output_filename == "duplicate_urls.csv"

    def test_output_fields(self, validator):
        assert "ror_display_name" in validator.output_fields
        assert "ror_id" in validator.output_fields
        assert "data_dump_id" in validator.output_fields
        assert "data_dump_ror_display_name" in validator.output_fields
        assert "csv_url" in validator.output_fields
        assert "data_dump_url" in validator.output_fields

    def test_requires_data_source(self, validator):
        assert validator.requires_data_source is True

    def test_requires_geonames(self, validator):
        assert validator.requires_geonames is False


class TestExactUrlMatch:
    def test_finds_exact_url_match(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,links.type.website\n"
            ",Test Org*en,https://example.org\n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "links": [{"type": "website", "value": "https://example.org"}],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 1
        assert results[0]["data_dump_id"] == "https://ror.org/existing"
        assert results[0]["csv_url"] == "https://example.org"
        assert results[0]["data_dump_url"] == "https://example.org"


class TestWwwNormalization:
    def test_matches_with_www_removed(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,links.type.website\n"
            ",Test Org*en,https://www.example.org\n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "links": [{"type": "website", "value": "https://example.org"}],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 1

    def test_matches_www_in_data_source(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,links.type.website\n"
            ",Test Org*en,https://example.org\n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "links": [{"type": "website", "value": "https://www.example.org"}],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 1


class TestSchemeVariation:
    def test_matches_http_vs_https(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,links.type.website\n"
            ",Test Org*en,http://example.org\n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "links": [{"type": "website", "value": "https://example.org"}],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 1

    def test_matches_https_vs_http(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,links.type.website\n"
            ",Test Org*en,https://example.org\n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "links": [{"type": "website", "value": "http://example.org"}],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 1


class TestPathStripping:
    def test_matches_with_path_stripped(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,links.type.website\n"
            ",Test Org*en,https://example.org/about/us\n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "links": [{"type": "website", "value": "https://example.org"}],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 1

    def test_matches_path_in_data_source(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,links.type.website\n"
            ",Test Org*en,https://example.org\n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "links": [{"type": "website", "value": "https://example.org/contact"}],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 1

    def test_matches_with_query_params_stripped(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,links.type.website\n"
            ",Test Org*en,https://example.org?lang=en\n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "links": [{"type": "website", "value": "https://example.org"}],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 1

    def test_matches_with_fragment_stripped(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,links.type.website\n"
            ",Test Org*en,https://example.org#section\n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "links": [{"type": "website", "value": "https://example.org"}],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 1


class TestDifferentDomains:
    def test_no_match_for_different_domains(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,links.type.website\n"
            ",Test Org*en,https://example.org\n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "links": [{"type": "website", "value": "https://different.org"}],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 0

    def test_no_match_for_subdomain(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,links.type.website\n"
            ",Test Org*en,https://sub.example.org\n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "links": [{"type": "website", "value": "https://example.org"}],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 0


class TestWhitespaceHandling:
    def test_handles_leading_trailing_whitespace(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,links.type.website\n"
            ",Test Org*en, https://example.org \n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "links": [{"type": "website", "value": "https://example.org"}],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 1


class TestCaseInsensitivity:
    def test_matches_case_insensitive(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,links.type.website\n"
            ",Test Org*en,https://EXAMPLE.ORG\n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "links": [{"type": "website", "value": "https://example.org"}],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 1


class TestOutputFormat:
    def test_output_includes_all_fields(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,links.type.website\n"
            "https://ror.org/csv123,CSV Org*en,https://example.org\n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "links": [{"type": "website", "value": "https://example.org/path"}],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 1
        result = results[0]
        assert result["ror_id"] == "https://ror.org/csv123"
        assert result["ror_display_name"] == "CSV Org*en"
        assert result["data_dump_id"] == "https://ror.org/existing"
        assert result["data_dump_ror_display_name"] == "Existing Org"
        assert result["csv_url"] == "https://example.org"
        assert result["data_dump_url"] == "https://example.org/path"

    def test_output_with_new_record(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,links.type.website\n"
            ",New Org*en,https://example.org\n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "links": [{"type": "website", "value": "https://example.org"}],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 1
        assert results[0]["ror_id"] == ""


class TestEmptyAndMissingData:
    def test_empty_url_in_csv(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,links.type.website\n"
            ",Test Org*en,\n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "links": [{"type": "website", "value": "https://example.org"}],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 0

    def test_no_website_in_data_source(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,links.type.website\n"
            ",Test Org*en,https://example.org\n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "links": [],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 0

    def test_missing_links_field_in_data_source(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,links.type.website\n"
            ",Test Org*en,https://example.org\n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 0


class TestMultipleRecords:
    def test_multiple_csv_records(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,links.type.website\n"
            ",Org One*en,https://one.org\n"
            ",Org Two*en,https://two.org\n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "links": [{"type": "website", "value": "https://two.org"}],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 1
        assert results[0]["ror_display_name"] == "Org Two*en"

    def test_multiple_data_source_matches(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,links.type.website\n"
            ",Test Org*en,https://example.org\n"
        )

        data_source = DataSource([
            {
                "id": "https://ror.org/first",
                "names": [{"value": "First Org", "types": ["ror_display"]}],
                "links": [{"type": "website", "value": "https://first.org"}],
            },
            {
                "id": "https://ror.org/second",
                "names": [{"value": "Second Org", "types": ["ror_display"]}],
                "links": [{"type": "website", "value": "https://example.org"}],
            },
        ])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 1
        assert results[0]["data_dump_id"] == "https://ror.org/second"


class TestCanRun:
    def test_can_run_with_data_source(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text("id,names.types.ror_display\n,Test*en\n")
        data_source = DataSource([])

        ctx = make_context(csv_path, tmp_path, data_source)
        can_run, reason = validator.can_run(ctx)

        assert can_run is True
        assert reason == ""


class TestCombinedNormalization:
    def test_www_and_scheme_and_path_combined(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,links.type.website\n"
            ",Test Org*en,http://www.EXAMPLE.org/some/path?query=1#fragment\n"
        )

        data_source = DataSource([{
            "id": "https://ror.org/existing",
            "names": [{"value": "Existing Org", "types": ["ror_display"]}],
            "links": [{"type": "website", "value": "https://example.org"}],
        }])

        ctx = make_context(csv_path, tmp_path, data_source)
        results = validator.run(ctx)

        assert len(results) == 1
