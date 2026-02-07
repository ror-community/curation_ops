import csv
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from curation_validation.validators.base import ValidatorContext
from curation_validation.validators.production_duplicates import (
    ProductionDuplicatesValidator,
    get_country_code_from_result,
    get_all_names_from_result,
    parse_csv_names,
    clean_name,
    FUZZY_THRESHOLD,
    MAX_WORKERS,
)


def _make_json_ctx(tmp_path, records, geonames_user="testuser"):
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
        data_source=None,
        geonames_user=geonames_user,
    )


def _make_csv_ctx(tmp_path, rows, geonames_user="testuser"):
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
        data_source=None,
        geonames_user=geonames_user,
    )


def _ror_api_result(ror_id, display_name, country_code, aliases=None, labels=None):
    names = [{"value": display_name, "types": ["ror_display"]}]
    if aliases:
        for alias in aliases:
            names.append({"value": alias, "types": ["alias"]})
    if labels:
        for label in labels:
            names.append({"value": label, "types": ["label"]})
    return {
        "id": ror_id,
        "names": names,
        "locations": [
            {
                "geonames_details": {
                    "country_code": country_code,
                }
            }
        ],
    }


class TestProductionDuplicatesMetadata:
    def test_name(self):
        v = ProductionDuplicatesValidator()
        assert v.name == "production-duplicates"

    def test_supported_formats(self):
        v = ProductionDuplicatesValidator()
        assert v.supported_formats == {"csv", "json"}

    def test_requires_geonames(self):
        v = ProductionDuplicatesValidator()
        assert v.requires_geonames is True

    def test_output_filename(self):
        v = ProductionDuplicatesValidator()
        assert v.output_filename == "production_duplicates.csv"

    def test_output_fields(self):
        v = ProductionDuplicatesValidator()
        expected = [
            "issue_url",
            "input_name",
            "matched_ror_id",
            "matched_name",
            "match_ratio",
        ]
        assert v.output_fields == expected

    def test_can_run_without_geonames(self, tmp_path):
        v = ProductionDuplicatesValidator()
        ctx = ValidatorContext(
            csv_file=None,
            json_dir=None,
            output_dir=tmp_path,
            data_source=None,
            geonames_user=None,
        )
        can, msg = v.can_run(ctx)
        assert can is False
        assert "geonames" in msg.lower()

    def test_can_run_with_geonames(self, tmp_path):
        v = ProductionDuplicatesValidator()
        ctx = ValidatorContext(
            csv_file=None,
            json_dir=None,
            output_dir=tmp_path,
            data_source=None,
            geonames_user="testuser",
        )
        can, _ = v.can_run(ctx)
        assert can is True


class TestGetCountryCodeFromResult:
    def test_returns_country_code(self):
        result = _ror_api_result("https://ror.org/001", "Org", "US")
        assert get_country_code_from_result(result) == "US"

    def test_returns_none_when_no_locations(self):
        result = {"locations": []}
        assert get_country_code_from_result(result) is None

    def test_returns_none_when_locations_key_missing(self):
        result = {}
        assert get_country_code_from_result(result) is None

    def test_returns_none_when_no_geonames_details(self):
        result = {"locations": [{}]}
        assert get_country_code_from_result(result) is None

    def test_returns_none_when_no_country_code(self):
        result = {"locations": [{"geonames_details": {}}]}
        assert get_country_code_from_result(result) is None


class TestGetAllNamesFromResult:
    def test_returns_display_name(self):
        result = _ror_api_result("https://ror.org/001", "Main Org", "US")
        names = get_all_names_from_result(result)
        assert "Main Org" in names

    def test_returns_aliases(self):
        result = _ror_api_result(
            "https://ror.org/001", "Main Org", "US", aliases=["Alias One"]
        )
        names = get_all_names_from_result(result)
        assert "Main Org" in names
        assert "Alias One" in names

    def test_returns_labels(self):
        result = _ror_api_result(
            "https://ror.org/001", "Main Org", "US", labels=["Label One"]
        )
        names = get_all_names_from_result(result)
        assert "Label One" in names

    def test_excludes_acronyms(self):
        result = {
            "names": [
                {"value": "Main Org", "types": ["ror_display"]},
                {"value": "MO", "types": ["acronym"]},
            ]
        }
        names = get_all_names_from_result(result)
        assert "Main Org" in names
        assert "MO" not in names

    def test_returns_empty_when_no_names(self):
        result = {"names": []}
        assert get_all_names_from_result(result) == []

    def test_returns_empty_when_names_key_missing(self):
        result = {}
        assert get_all_names_from_result(result) == []


class TestParseCsvNames:
    def test_parses_display_name(self):
        row = {"names.types.ror_display": "University of Test"}
        names = parse_csv_names(row)
        assert "University of Test" in names

    def test_parses_aliases(self):
        row = {
            "names.types.ror_display": "University of Test",
            "names.types.alias": "UTest; Test University",
        }
        names = parse_csv_names(row)
        assert "University of Test" in names
        assert "UTest" in names
        assert "Test University" in names

    def test_parses_labels(self):
        row = {
            "names.types.ror_display": "University of Test",
            "names.types.label": "Universite de Test; Test Uni",
        }
        names = parse_csv_names(row)
        assert "Universite de Test" in names
        assert "Test Uni" in names

    def test_returns_empty_for_empty_row(self):
        row = {}
        assert parse_csv_names(row) == []

    def test_skips_empty_values(self):
        row = {
            "names.types.ror_display": "",
            "names.types.alias": "",
            "names.types.label": "",
        }
        assert parse_csv_names(row) == []


class TestCleanName:
    def test_strips_asterisk_suffix(self):
        assert clean_name("Some Name*en") == "Some Name"

    def test_returns_name_without_asterisk(self):
        assert clean_name("Some Name") == "Some Name"

    def test_strips_whitespace_after_asterisk(self):
        assert clean_name("Name * extra") == "Name"

    def test_empty_string(self):
        assert clean_name("") == ""


class TestConstants:
    def test_fuzzy_threshold(self):
        assert FUZZY_THRESHOLD == 85

    def test_max_workers(self):
        assert MAX_WORKERS == 5


class TestProductionDuplicatesJSON:
    @patch("curation_validation.validators.production_duplicates.RORAPIClient")
    @patch("curation_validation.validators.production_duplicates.GeoNamesClient")
    def test_finds_duplicate_matching_country(self, mock_geonames_cls, mock_ror_cls, tmp_path):
        mock_geonames = MagicMock()
        mock_geonames.get_country_code.return_value = "US"
        mock_geonames_cls.return_value = mock_geonames

        mock_ror = MagicMock()
        mock_ror.search_all.return_value = [
            _ror_api_result("https://ror.org/existing001", "University of Testing", "US")
        ]
        mock_ror_cls.return_value = mock_ror

        input_records = [
            {
                "id": "",
                "names": [{"value": "University of Testing", "types": ["ror_display"]}],
                "locations": [{"geonames_id": 5128581}],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records)
        v = ProductionDuplicatesValidator()
        results = v.run(ctx)

        assert len(results) >= 1
        assert results[0]["matched_ror_id"] == "https://ror.org/existing001"
        assert results[0]["input_name"] == "University of Testing"
        assert int(results[0]["match_ratio"]) >= FUZZY_THRESHOLD

    @patch("curation_validation.validators.production_duplicates.RORAPIClient")
    @patch("curation_validation.validators.production_duplicates.GeoNamesClient")
    def test_filters_by_country_mismatch(self, mock_geonames_cls, mock_ror_cls, tmp_path):
        mock_geonames = MagicMock()
        mock_geonames.get_country_code.return_value = "US"
        mock_geonames_cls.return_value = mock_geonames

        mock_ror = MagicMock()
        mock_ror.search_all.return_value = [
            _ror_api_result("https://ror.org/existing001", "University of Testing", "GB")
        ]
        mock_ror_cls.return_value = mock_ror

        input_records = [
            {
                "id": "",
                "names": [{"value": "University of Testing", "types": ["ror_display"]}],
                "locations": [{"geonames_id": 5128581}],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records)
        v = ProductionDuplicatesValidator()
        results = v.run(ctx)

        assert len(results) == 0

    @patch("curation_validation.validators.production_duplicates.RORAPIClient")
    @patch("curation_validation.validators.production_duplicates.GeoNamesClient")
    def test_below_threshold_not_reported(self, mock_geonames_cls, mock_ror_cls, tmp_path):
        mock_geonames = MagicMock()
        mock_geonames.get_country_code.return_value = "US"
        mock_geonames_cls.return_value = mock_geonames

        mock_ror = MagicMock()
        mock_ror.search_all.return_value = [
            _ror_api_result("https://ror.org/existing001", "Completely Different Organization Name XYZ", "US")
        ]
        mock_ror_cls.return_value = mock_ror

        input_records = [
            {
                "id": "",
                "names": [{"value": "University of Testing", "types": ["ror_display"]}],
                "locations": [{"geonames_id": 5128581}],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records)
        v = ProductionDuplicatesValidator()
        results = v.run(ctx)

        assert len(results) == 0

    @patch("curation_validation.validators.production_duplicates.RORAPIClient")
    @patch("curation_validation.validators.production_duplicates.GeoNamesClient")
    def test_matches_against_aliases(self, mock_geonames_cls, mock_ror_cls, tmp_path):
        mock_geonames = MagicMock()
        mock_geonames.get_country_code.return_value = "DE"
        mock_geonames_cls.return_value = mock_geonames

        mock_ror = MagicMock()
        mock_ror.search_all.return_value = [
            _ror_api_result(
                "https://ror.org/existing001",
                "Different Display Name",
                "DE",
                aliases=["Technische Universitat Berlin"],
            )
        ]
        mock_ror_cls.return_value = mock_ror

        input_records = [
            {
                "id": "",
                "names": [{"value": "Technische Universitat Berlin", "types": ["ror_display"]}],
                "locations": [{"geonames_id": 2950159}],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records)
        v = ProductionDuplicatesValidator()
        results = v.run(ctx)

        assert len(results) >= 1
        assert results[0]["matched_name"] == "Technische Universitat Berlin"

    @patch("curation_validation.validators.production_duplicates.RORAPIClient")
    @patch("curation_validation.validators.production_duplicates.GeoNamesClient")
    def test_no_api_results_no_findings(self, mock_geonames_cls, mock_ror_cls, tmp_path):
        mock_geonames = MagicMock()
        mock_geonames.get_country_code.return_value = "US"
        mock_geonames_cls.return_value = mock_geonames

        mock_ror = MagicMock()
        mock_ror.search_all.return_value = []
        mock_ror_cls.return_value = mock_ror

        input_records = [
            {
                "id": "",
                "names": [{"value": "Very Unique Name", "types": ["ror_display"]}],
                "locations": [{"geonames_id": 5128581}],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records)
        v = ProductionDuplicatesValidator()
        results = v.run(ctx)

        assert len(results) == 0

    @patch("curation_validation.validators.production_duplicates.RORAPIClient")
    @patch("curation_validation.validators.production_duplicates.GeoNamesClient")
    def test_deduplicates_findings(self, mock_geonames_cls, mock_ror_cls, tmp_path):
        mock_geonames = MagicMock()
        mock_geonames.get_country_code.return_value = "US"
        mock_geonames_cls.return_value = mock_geonames

        mock_ror = MagicMock()
        mock_ror.search_all.return_value = [
            _ror_api_result(
                "https://ror.org/existing001",
                "University of Testing",
                "US",
                aliases=["University of Testing"],
            )
        ]
        mock_ror_cls.return_value = mock_ror

        input_records = [
            {
                "id": "",
                "names": [
                    {"value": "University of Testing", "types": ["ror_display"]},
                    {"value": "University of Testing", "types": ["alias"]},
                ],
                "locations": [{"geonames_id": 5128581}],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records)
        v = ProductionDuplicatesValidator()
        results = v.run(ctx)

        seen = set()
        for r in results:
            key = (r["input_name"], r["matched_ror_id"])
            assert key not in seen, f"Duplicate finding: {key}"
            seen.add(key)

    @patch("curation_validation.validators.production_duplicates.RORAPIClient")
    @patch("curation_validation.validators.production_duplicates.GeoNamesClient")
    def test_output_format_fields(self, mock_geonames_cls, mock_ror_cls, tmp_path):
        mock_geonames = MagicMock()
        mock_geonames.get_country_code.return_value = "US"
        mock_geonames_cls.return_value = mock_geonames

        mock_ror = MagicMock()
        mock_ror.search_all.return_value = [
            _ror_api_result("https://ror.org/existing001", "University of Testing", "US")
        ]
        mock_ror_cls.return_value = mock_ror

        input_records = [
            {
                "id": "",
                "names": [{"value": "University of Testing", "types": ["ror_display"]}],
                "locations": [{"geonames_id": 5128581}],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records)
        v = ProductionDuplicatesValidator()
        results = v.run(ctx)

        assert len(results) >= 1
        result = results[0]
        assert "issue_url" in result
        assert "input_name" in result
        assert "matched_ror_id" in result
        assert "matched_name" in result
        assert "match_ratio" in result

    @patch("curation_validation.validators.production_duplicates.RORAPIClient")
    @patch("curation_validation.validators.production_duplicates.GeoNamesClient")
    def test_extracts_geonames_id_from_json(self, mock_geonames_cls, mock_ror_cls, tmp_path):
        mock_geonames = MagicMock()
        mock_geonames.get_country_code.return_value = "FR"
        mock_geonames_cls.return_value = mock_geonames

        mock_ror = MagicMock()
        mock_ror.search_all.return_value = [
            _ror_api_result("https://ror.org/existing001", "Universite de Paris", "FR")
        ]
        mock_ror_cls.return_value = mock_ror

        input_records = [
            {
                "id": "",
                "names": [{"value": "Universite de Paris", "types": ["ror_display"]}],
                "locations": [{"geonames_id": 2988507}],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records)
        v = ProductionDuplicatesValidator()
        results = v.run(ctx)

        mock_geonames.get_country_code.assert_called()
        call_args = mock_geonames.get_country_code.call_args_list[0]
        assert "2988507" in str(call_args)

    @patch("curation_validation.validators.production_duplicates.RORAPIClient")
    @patch("curation_validation.validators.production_duplicates.GeoNamesClient")
    def test_geonames_lookup_fails_skips_record(self, mock_geonames_cls, mock_ror_cls, tmp_path):
        mock_geonames = MagicMock()
        mock_geonames.get_country_code.return_value = None
        mock_geonames_cls.return_value = mock_geonames

        mock_ror = MagicMock()
        mock_ror_cls.return_value = mock_ror

        input_records = [
            {
                "id": "",
                "names": [{"value": "University of Testing", "types": ["ror_display"]}],
                "locations": [{"geonames_id": 9999999}],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records)
        v = ProductionDuplicatesValidator()
        results = v.run(ctx)

        assert len(results) == 0

    @patch("curation_validation.validators.production_duplicates.RORAPIClient")
    @patch("curation_validation.validators.production_duplicates.GeoNamesClient")
    def test_empty_json_dir(self, mock_geonames_cls, mock_ror_cls, tmp_path):
        mock_geonames = MagicMock()
        mock_geonames_cls.return_value = mock_geonames
        mock_ror = MagicMock()
        mock_ror_cls.return_value = mock_ror

        json_dir = tmp_path / "json"
        json_dir.mkdir(parents=True, exist_ok=True)
        ctx = ValidatorContext(
            csv_file=None,
            json_dir=json_dir,
            output_dir=tmp_path / "output",
            data_source=None,
            geonames_user="testuser",
        )
        v = ProductionDuplicatesValidator()
        results = v.run(ctx)
        assert results == []

    @patch("curation_validation.validators.production_duplicates.RORAPIClient")
    @patch("curation_validation.validators.production_duplicates.GeoNamesClient")
    def test_multiple_input_records(self, mock_geonames_cls, mock_ror_cls, tmp_path):
        mock_geonames = MagicMock()
        mock_geonames.get_country_code.return_value = "US"
        mock_geonames_cls.return_value = mock_geonames

        mock_ror = MagicMock()

        def search_side_effect(name):
            if "Testing" in name:
                return [
                    _ror_api_result("https://ror.org/existing001", "University of Testing", "US")
                ]
            return []

        mock_ror.search_all.side_effect = search_side_effect
        mock_ror_cls.return_value = mock_ror

        input_records = [
            {
                "id": "",
                "names": [{"value": "University of Testing", "types": ["ror_display"]}],
                "locations": [{"geonames_id": 5128581}],
            },
            {
                "id": "",
                "names": [{"value": "Completely Novel Organization", "types": ["ror_display"]}],
                "locations": [{"geonames_id": 5128581}],
            },
        ]
        ctx = _make_json_ctx(tmp_path, input_records)
        v = ProductionDuplicatesValidator()
        results = v.run(ctx)

        matched_names = [r["input_name"] for r in results]
        assert "University of Testing" in matched_names
        assert "Completely Novel Organization" not in matched_names

    @patch("curation_validation.validators.production_duplicates.RORAPIClient")
    @patch("curation_validation.validators.production_duplicates.GeoNamesClient")
    def test_json_extracts_multiple_names(self, mock_geonames_cls, mock_ror_cls, tmp_path):
        mock_geonames = MagicMock()
        mock_geonames.get_country_code.return_value = "DE"
        mock_geonames_cls.return_value = mock_geonames

        search_calls = []

        def track_search(name):
            search_calls.append(name)
            return []

        mock_ror = MagicMock()
        mock_ror.search_all.side_effect = track_search
        mock_ror_cls.return_value = mock_ror

        input_records = [
            {
                "id": "",
                "names": [
                    {"value": "Technische Universitat Berlin", "types": ["ror_display"]},
                    {"value": "TU Berlin", "types": ["alias"]},
                    {"value": "Technical University of Berlin", "types": ["label"]},
                    {"value": "TUB", "types": ["acronym"]},
                ],
                "locations": [{"geonames_id": 2950159}],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records)
        v = ProductionDuplicatesValidator()
        v.run(ctx)

        searched = set(search_calls)
        assert "Technische Universitat Berlin" in searched
        assert "TU Berlin" in searched
        assert "Technical University of Berlin" in searched
        assert "TUB" not in searched

    @patch("curation_validation.validators.production_duplicates.RORAPIClient")
    @patch("curation_validation.validators.production_duplicates.GeoNamesClient")
    def test_issue_url_from_json_id(self, mock_geonames_cls, mock_ror_cls, tmp_path):
        mock_geonames = MagicMock()
        mock_geonames.get_country_code.return_value = "US"
        mock_geonames_cls.return_value = mock_geonames

        mock_ror = MagicMock()
        mock_ror.search_all.return_value = [
            _ror_api_result("https://ror.org/existing001", "Test University", "US")
        ]
        mock_ror_cls.return_value = mock_ror

        input_records = [
            {
                "id": "",
                "names": [{"value": "Test University", "types": ["ror_display"]}],
                "locations": [{"geonames_id": 5128581}],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records)
        v = ProductionDuplicatesValidator()
        results = v.run(ctx)

        assert len(results) >= 1
        assert "issue_url" in results[0]


class TestProductionDuplicatesCSV:
    @patch("curation_validation.validators.production_duplicates.RORAPIClient")
    @patch("curation_validation.validators.production_duplicates.GeoNamesClient")
    def test_finds_duplicate_matching_country_csv(self, mock_geonames_cls, mock_ror_cls, tmp_path):
        mock_geonames = MagicMock()
        mock_geonames.get_country_code.return_value = "US"
        mock_geonames_cls.return_value = mock_geonames

        mock_ror = MagicMock()
        mock_ror.search_all.return_value = [
            _ror_api_result("https://ror.org/existing001", "University of Testing", "US")
        ]
        mock_ror_cls.return_value = mock_ror

        rows = [
            {
                "names.types.ror_display": "University of Testing",
                "names.types.alias": "",
                "names.types.label": "",
                "locations.geonames_id": "5128581",
            }
        ]
        ctx = _make_csv_ctx(tmp_path, rows)
        v = ProductionDuplicatesValidator()
        results = v.run(ctx)

        assert len(results) >= 1
        assert results[0]["matched_ror_id"] == "https://ror.org/existing001"
        assert results[0]["input_name"] == "University of Testing"

    @patch("curation_validation.validators.production_duplicates.RORAPIClient")
    @patch("curation_validation.validators.production_duplicates.GeoNamesClient")
    def test_filters_by_country_mismatch_csv(self, mock_geonames_cls, mock_ror_cls, tmp_path):
        mock_geonames = MagicMock()
        mock_geonames.get_country_code.return_value = "US"
        mock_geonames_cls.return_value = mock_geonames

        mock_ror = MagicMock()
        mock_ror.search_all.return_value = [
            _ror_api_result("https://ror.org/existing001", "University of Testing", "JP")
        ]
        mock_ror_cls.return_value = mock_ror

        rows = [
            {
                "names.types.ror_display": "University of Testing",
                "names.types.alias": "",
                "names.types.label": "",
                "locations.geonames_id": "5128581",
            }
        ]
        ctx = _make_csv_ctx(tmp_path, rows)
        v = ProductionDuplicatesValidator()
        results = v.run(ctx)

        assert len(results) == 0

    @patch("curation_validation.validators.production_duplicates.RORAPIClient")
    @patch("curation_validation.validators.production_duplicates.GeoNamesClient")
    def test_below_threshold_not_reported_csv(self, mock_geonames_cls, mock_ror_cls, tmp_path):
        mock_geonames = MagicMock()
        mock_geonames.get_country_code.return_value = "US"
        mock_geonames_cls.return_value = mock_geonames

        mock_ror = MagicMock()
        mock_ror.search_all.return_value = [
            _ror_api_result("https://ror.org/existing001", "Completely Different Organization Name XYZ", "US")
        ]
        mock_ror_cls.return_value = mock_ror

        rows = [
            {
                "names.types.ror_display": "University of Testing",
                "names.types.alias": "",
                "names.types.label": "",
                "locations.geonames_id": "5128581",
            }
        ]
        ctx = _make_csv_ctx(tmp_path, rows)
        v = ProductionDuplicatesValidator()
        results = v.run(ctx)

        assert len(results) == 0

    @patch("curation_validation.validators.production_duplicates.RORAPIClient")
    @patch("curation_validation.validators.production_duplicates.GeoNamesClient")
    def test_csv_parses_semicolon_separated_aliases(self, mock_geonames_cls, mock_ror_cls, tmp_path):
        mock_geonames = MagicMock()
        mock_geonames.get_country_code.return_value = "US"
        mock_geonames_cls.return_value = mock_geonames

        search_calls = []

        def track_search(name):
            search_calls.append(name)
            return []

        mock_ror = MagicMock()
        mock_ror.search_all.side_effect = track_search
        mock_ror_cls.return_value = mock_ror

        rows = [
            {
                "names.types.ror_display": "Main University",
                "names.types.alias": "Alias One; Alias Two",
                "names.types.label": "Label One",
                "locations.geonames_id": "5128581",
            }
        ]
        ctx = _make_csv_ctx(tmp_path, rows)
        v = ProductionDuplicatesValidator()
        v.run(ctx)

        searched = set(search_calls)
        assert "Main University" in searched
        assert "Alias One" in searched
        assert "Alias Two" in searched
        assert "Label One" in searched

    @patch("curation_validation.validators.production_duplicates.RORAPIClient")
    @patch("curation_validation.validators.production_duplicates.GeoNamesClient")
    def test_csv_handles_asterisk_in_names(self, mock_geonames_cls, mock_ror_cls, tmp_path):
        mock_geonames = MagicMock()
        mock_geonames.get_country_code.return_value = "FR"
        mock_geonames_cls.return_value = mock_geonames

        search_calls = []

        def track_search(name):
            search_calls.append(name)
            return []

        mock_ror = MagicMock()
        mock_ror.search_all.side_effect = track_search
        mock_ror_cls.return_value = mock_ror

        rows = [
            {
                "names.types.ror_display": "Universite de Paris",
                "names.types.alias": "",
                "names.types.label": "Universite de Paris*fr; University of Paris*en",
                "locations.geonames_id": "2988507",
            }
        ]
        ctx = _make_csv_ctx(tmp_path, rows)
        v = ProductionDuplicatesValidator()
        v.run(ctx)

        searched = set(search_calls)
        assert "Universite de Paris" in searched
        assert "University of Paris" in searched
        for call in search_calls:
            assert "*" not in call

    @patch("curation_validation.validators.production_duplicates.RORAPIClient")
    @patch("curation_validation.validators.production_duplicates.GeoNamesClient")
    def test_csv_geonames_lookup_fails_skips_record(self, mock_geonames_cls, mock_ror_cls, tmp_path):
        mock_geonames = MagicMock()
        mock_geonames.get_country_code.return_value = None
        mock_geonames_cls.return_value = mock_geonames

        mock_ror = MagicMock()
        mock_ror_cls.return_value = mock_ror

        rows = [
            {
                "names.types.ror_display": "University of Testing",
                "names.types.alias": "",
                "names.types.label": "",
                "locations.geonames_id": "9999999",
            }
        ]
        ctx = _make_csv_ctx(tmp_path, rows)
        v = ProductionDuplicatesValidator()
        results = v.run(ctx)

        assert len(results) == 0

    @patch("curation_validation.validators.production_duplicates.RORAPIClient")
    @patch("curation_validation.validators.production_duplicates.GeoNamesClient")
    def test_csv_multiple_rows(self, mock_geonames_cls, mock_ror_cls, tmp_path):
        mock_geonames = MagicMock()
        mock_geonames.get_country_code.return_value = "US"
        mock_geonames_cls.return_value = mock_geonames

        mock_ror = MagicMock()

        def search_side_effect(name):
            if "Testing" in name:
                return [
                    _ror_api_result("https://ror.org/existing001", "University of Testing", "US")
                ]
            return []

        mock_ror.search_all.side_effect = search_side_effect
        mock_ror_cls.return_value = mock_ror

        rows = [
            {
                "names.types.ror_display": "University of Testing",
                "names.types.alias": "",
                "names.types.label": "",
                "locations.geonames_id": "5128581",
            },
            {
                "names.types.ror_display": "Completely Novel Organization",
                "names.types.alias": "",
                "names.types.label": "",
                "locations.geonames_id": "5128581",
            },
        ]
        ctx = _make_csv_ctx(tmp_path, rows)
        v = ProductionDuplicatesValidator()
        results = v.run(ctx)

        matched_names = [r["input_name"] for r in results]
        assert "University of Testing" in matched_names
        assert "Completely Novel Organization" not in matched_names

    @patch("curation_validation.validators.production_duplicates.RORAPIClient")
    @patch("curation_validation.validators.production_duplicates.GeoNamesClient")
    def test_csv_output_fields(self, mock_geonames_cls, mock_ror_cls, tmp_path):
        mock_geonames = MagicMock()
        mock_geonames.get_country_code.return_value = "US"
        mock_geonames_cls.return_value = mock_geonames

        mock_ror = MagicMock()
        mock_ror.search_all.return_value = [
            _ror_api_result("https://ror.org/existing001", "University of Testing", "US")
        ]
        mock_ror_cls.return_value = mock_ror

        rows = [
            {
                "names.types.ror_display": "University of Testing",
                "names.types.alias": "",
                "names.types.label": "",
                "locations.geonames_id": "5128581",
            }
        ]
        ctx = _make_csv_ctx(tmp_path, rows)
        v = ProductionDuplicatesValidator()
        results = v.run(ctx)

        assert len(results) >= 1
        result = results[0]
        assert "issue_url" in result
        assert "input_name" in result
        assert "matched_ror_id" in result
        assert "matched_name" in result
        assert "match_ratio" in result


class TestProductionDuplicatesEdgeCases:
    def test_returns_empty_when_no_input(self, tmp_path):
        ctx = ValidatorContext(
            csv_file=None,
            json_dir=None,
            output_dir=tmp_path,
            data_source=None,
            geonames_user="testuser",
        )
        v = ProductionDuplicatesValidator()
        results = v.run(ctx)
        assert results == []

    @patch("curation_validation.validators.production_duplicates.RORAPIClient")
    @patch("curation_validation.validators.production_duplicates.GeoNamesClient")
    def test_prefers_json_over_csv(self, mock_geonames_cls, mock_ror_cls, tmp_path):
        mock_geonames = MagicMock()
        mock_geonames.get_country_code.return_value = "US"
        mock_geonames_cls.return_value = mock_geonames

        mock_ror = MagicMock()
        mock_ror.search_all.return_value = [
            _ror_api_result("https://ror.org/existing001", "JSON Org", "US")
        ]
        mock_ror_cls.return_value = mock_ror

        json_dir = tmp_path / "json"
        json_dir.mkdir(parents=True, exist_ok=True)
        json_record = {
            "id": "",
            "names": [{"value": "JSON Org", "types": ["ror_display"]}],
            "locations": [{"geonames_id": 5128581}],
        }
        (json_dir / "rec.json").write_text(json.dumps(json_record), encoding="utf-8")

        csv_file = tmp_path / "input.csv"
        fieldnames = [
            "names.types.ror_display",
            "names.types.alias",
            "names.types.label",
            "locations.geonames_id",
        ]
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow({
                "names.types.ror_display": "CSV Org",
                "names.types.alias": "",
                "names.types.label": "",
                "locations.geonames_id": "5128581",
            })

        ctx = ValidatorContext(
            csv_file=csv_file,
            json_dir=json_dir,
            output_dir=tmp_path / "output",
            data_source=None,
            geonames_user="testuser",
        )
        v = ProductionDuplicatesValidator()
        results = v.run(ctx)

        assert len(results) >= 1
        assert results[0]["input_name"] == "JSON Org"

    @patch("curation_validation.validators.production_duplicates.RORAPIClient")
    @patch("curation_validation.validators.production_duplicates.GeoNamesClient")
    def test_record_with_no_locations(self, mock_geonames_cls, mock_ror_cls, tmp_path):
        mock_geonames = MagicMock()
        mock_geonames_cls.return_value = mock_geonames
        mock_ror = MagicMock()
        mock_ror_cls.return_value = mock_ror

        input_records = [
            {
                "id": "",
                "names": [{"value": "No Location Org", "types": ["ror_display"]}],
                "locations": [],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records)
        v = ProductionDuplicatesValidator()
        results = v.run(ctx)

        assert results == []

    @patch("curation_validation.validators.production_duplicates.RORAPIClient")
    @patch("curation_validation.validators.production_duplicates.GeoNamesClient")
    def test_record_with_no_names(self, mock_geonames_cls, mock_ror_cls, tmp_path):
        mock_geonames = MagicMock()
        mock_geonames.get_country_code.return_value = "US"
        mock_geonames_cls.return_value = mock_geonames
        mock_ror = MagicMock()
        mock_ror_cls.return_value = mock_ror

        input_records = [
            {
                "id": "",
                "names": [{"value": "ACR", "types": ["acronym"]}],
                "locations": [{"geonames_id": 5128581}],
            }
        ]
        ctx = _make_json_ctx(tmp_path, input_records)
        v = ProductionDuplicatesValidator()
        results = v.run(ctx)

        assert results == []

    @patch("curation_validation.validators.production_duplicates.RORAPIClient")
    @patch("curation_validation.validators.production_duplicates.GeoNamesClient")
    def test_csv_no_geonames_id(self, mock_geonames_cls, mock_ror_cls, tmp_path):
        mock_geonames = MagicMock()
        mock_geonames_cls.return_value = mock_geonames
        mock_ror = MagicMock()
        mock_ror_cls.return_value = mock_ror

        rows = [
            {
                "names.types.ror_display": "University of Testing",
                "names.types.alias": "",
                "names.types.label": "",
                "locations.geonames_id": "",
            }
        ]
        ctx = _make_csv_ctx(tmp_path, rows)
        v = ProductionDuplicatesValidator()
        results = v.run(ctx)

        assert results == []
