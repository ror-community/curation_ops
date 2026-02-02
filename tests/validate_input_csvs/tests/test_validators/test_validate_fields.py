import pytest
from pathlib import Path

from validate_ror_records_input_csvs.validators.base import ValidatorContext
from validate_ror_records_input_csvs.validators.validate_fields import ValidateFieldsValidator


@pytest.fixture
def validator():
    return ValidateFieldsValidator()


@pytest.fixture
def fixtures_dir():
    return Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def valid_csv(fixtures_dir):
    return fixtures_dir / "new_records_valid.csv"


@pytest.fixture
def invalid_csv(fixtures_dir):
    return fixtures_dir / "new_records_invalid.csv"


def make_context(input_file: Path, tmp_path: Path) -> ValidatorContext:
    return ValidatorContext(
        input_file=input_file,
        output_dir=tmp_path,
        data_source=None,
        geonames_user=None,
    )


class TestValidatorProperties:
    def test_name(self, validator):
        assert validator.name == "validate-fields"

    def test_output_filename(self, validator):
        assert validator.output_filename == "validation_report.csv"

    def test_output_fields(self, validator):
        assert "html_url" in validator.output_fields
        assert "ror_id" in validator.output_fields
        assert "error_warning" in validator.output_fields

    def test_requires_data_source(self, validator):
        assert validator.requires_data_source is False

    def test_requires_geonames(self, validator):
        assert validator.requires_geonames is False


class TestValidNewRecords:
    def test_valid_new_records_no_errors(self, validator, valid_csv, tmp_path):
        ctx = make_context(valid_csv, tmp_path)
        results = validator.run(ctx)
        assert len(results) == 0


class TestInvalidStatus:
    def test_invalid_status_produces_error(self, validator, tmp_path):
        csv_content = """id,status,city,country
,pending,Boston,United States"""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        ctx = make_context(csv_file, tmp_path)
        results = validator.run(ctx)

        assert len(results) >= 1
        status_errors = [r for r in results if "status" in r["error_warning"].lower()]
        assert len(status_errors) >= 1


class TestInvalidAcronym:
    def test_lowercase_acronym_produces_error(self, validator, tmp_path):
        csv_content = """id,names.types.acronym,city,country
,lowercase*en,Boston,United States"""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        ctx = make_context(csv_file, tmp_path)
        results = validator.run(ctx)

        assert len(results) >= 1
        acronym_errors = [r for r in results if "lowercase" in r["error_warning"].lower()
                         or "uppercase" in r["error_warning"].lower()
                         or "acronym" in r["error_warning"].lower().replace("names.types.acronym", "")]
        assert len(acronym_errors) >= 1


class TestInvalidURL:
    def test_url_without_scheme_produces_error(self, validator, tmp_path):
        csv_content = """id,links.type.website,city,country
,example.org,Boston,United States"""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        ctx = make_context(csv_file, tmp_path)
        results = validator.run(ctx)

        assert len(results) >= 1
        url_errors = [r for r in results if "url" in r["error_warning"].lower()
                     or "http" in r["error_warning"].lower()
                     or "links" in r["error_warning"].lower()]
        assert len(url_errors) >= 1


class TestInvalidYear:
    def test_year_outside_range_produces_error(self, validator, tmp_path):
        csv_content = """id,established,city,country
,99,Boston,United States"""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        ctx = make_context(csv_file, tmp_path)
        results = validator.run(ctx)

        assert len(results) >= 1
        year_errors = [r for r in results if "established" in r["error_warning"].lower()
                      or "year" in r["error_warning"].lower()
                      or "4-digit" in r["error_warning"].lower()]
        assert len(year_errors) >= 1

    def test_non_numeric_year_produces_error(self, validator, tmp_path):
        csv_content = """id,established,city,country
,abc,Boston,United States"""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        ctx = make_context(csv_file, tmp_path)
        results = validator.run(ctx)

        assert len(results) >= 1
        year_errors = [r for r in results if "established" in r["error_warning"].lower()
                      or "year" in r["error_warning"].lower()]
        assert len(year_errors) >= 1


class TestInvalidWikidata:
    def test_lowercase_q_produces_error(self, validator, tmp_path):
        csv_content = """id,external_ids.type.wikidata.all,city,country
,q12345,Boston,United States"""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        ctx = make_context(csv_file, tmp_path)
        results = validator.run(ctx)

        assert len(results) >= 1
        wikidata_errors = [r for r in results if "wikidata" in r["error_warning"].lower()]
        assert len(wikidata_errors) >= 1


class TestEmptyRequiredFields:
    def test_empty_city_produces_warning(self, validator, tmp_path):
        csv_content = """id,city,country
,,United States"""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        ctx = make_context(csv_file, tmp_path)
        results = validator.run(ctx)

        assert len(results) >= 1
        city_errors = [r for r in results if "city" in r["error_warning"].lower()]
        assert len(city_errors) >= 1

    def test_empty_country_produces_warning(self, validator, tmp_path):
        csv_content = """id,city,country
,Boston,"""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        ctx = make_context(csv_file, tmp_path)
        results = validator.run(ctx)

        assert len(results) >= 1
        country_errors = [r for r in results if "country" in r["error_warning"].lower()]
        assert len(country_errors) >= 1


class TestMultiValueFields:
    def test_multi_value_field_partial_invalid(self, validator, tmp_path):
        csv_content = """id,names.types.acronym,city,country
,TU;lowercase;ABC,Boston,United States"""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        ctx = make_context(csv_file, tmp_path)
        results = validator.run(ctx)

        assert len(results) >= 1
        acronym_errors = [r for r in results if "lowercase" in r["error_warning"].lower()
                         or "uppercase" in r["error_warning"].lower()]
        assert len(acronym_errors) >= 1


class TestInvalidNames:
    def test_name_without_language_tag_produces_warning(self, validator, tmp_path):
        csv_content = """id,names.types.ror_display,city,country
,Test University,Boston,United States"""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        ctx = make_context(csv_file, tmp_path)
        results = validator.run(ctx)

        assert len(results) >= 1
        name_errors = [r for r in results if "language" in r["error_warning"].lower()
                      or "format" in r["error_warning"].lower()]
        assert len(name_errors) >= 1


class TestInvalidTypes:
    def test_invalid_type_produces_error(self, validator, tmp_path):
        csv_content = """id,types,city,country
,university,Boston,United States"""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        ctx = make_context(csv_file, tmp_path)
        results = validator.run(ctx)

        assert len(results) >= 1
        type_errors = [r for r in results if "types" in r["error_warning"].lower()]
        assert len(type_errors) >= 1


class TestInvalidGeonames:
    def test_non_numeric_geonames_produces_error(self, validator, tmp_path):
        csv_content = """id,locations.geonames_id,city,country
,abc,Boston,United States"""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        ctx = make_context(csv_file, tmp_path)
        results = validator.run(ctx)

        assert len(results) >= 1
        geo_errors = [r for r in results if "geonames" in r["error_warning"].lower()]
        assert len(geo_errors) >= 1

    def test_zero_geonames_produces_error(self, validator, tmp_path):
        csv_content = """id,locations.geonames_id,city,country
,0,Boston,United States"""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        ctx = make_context(csv_file, tmp_path)
        results = validator.run(ctx)

        assert len(results) >= 1
        geo_errors = [r for r in results if "geonames" in r["error_warning"].lower()]
        assert len(geo_errors) >= 1


class TestInvalidISNI:
    def test_invalid_isni_format_produces_error(self, validator, tmp_path):
        csv_content = """id,external_ids.type.isni.all,city,country
,0000-1234-5678,Boston,United States"""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        ctx = make_context(csv_file, tmp_path)
        results = validator.run(ctx)

        assert len(results) >= 1
        isni_errors = [r for r in results if "isni" in r["error_warning"].lower()]
        assert len(isni_errors) >= 1


class TestInvalidFundRef:
    def test_zero_fundref_produces_error(self, validator, tmp_path):
        csv_content = """id,external_ids.type.fundref.all,city,country
,0,Boston,United States"""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        ctx = make_context(csv_file, tmp_path)
        results = validator.run(ctx)

        assert len(results) >= 1
        fundref_errors = [r for r in results if "fundref" in r["error_warning"].lower()]
        assert len(fundref_errors) >= 1


class TestInvalidWikipedia:
    def test_invalid_wikipedia_url_produces_error(self, validator, tmp_path):
        csv_content = """id,links.type.wikipedia,city,country
,https://example.com/wiki,Boston,United States"""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        ctx = make_context(csv_file, tmp_path)
        results = validator.run(ctx)

        assert len(results) >= 1
        wiki_errors = [r for r in results if "wikipedia" in r["error_warning"].lower()]
        assert len(wiki_errors) >= 1


class TestInvalidCsvFile:
    def test_invalid_csv_produces_multiple_errors(self, validator, invalid_csv, tmp_path):
        ctx = make_context(invalid_csv, tmp_path)
        results = validator.run(ctx)

        assert len(results) >= 5
