import csv
import json
import random
from unittest.mock import MagicMock, patch

import pytest
from thefuzz import fuzz

from curation_validation.core.geonames import MAX_WORKERS
from curation_validation.core.loader import DataSource
from curation_validation.core.normalize import normalize_text
from curation_validation.validators.base import ValidatorContext
from curation_validation.validators.production_duplicates import (
    ProductionDuplicatesValidator,
    build_geonames_country_index,
    clean_name,
    find_production_duplicates,
    get_all_names_from_result,
    get_country_code_from_result,
    parse_csv_names,
    resolve_countries,
    FUZZY_THRESHOLD,
)

GEONAMES_CLIENT = "curation_validation.validators.production_duplicates.GeoNamesClient"

# geonames IDs used by the default data source, with their country codes.
NYC, BERLIN, PARIS, TOKYO = 5128581, 2950159, 2988507, 1850147


def _ror_record(ror_id, display_name, country_code, geonames_id=None, aliases=None,
                labels=None, acronyms=None, status="active"):
    names = [{"value": display_name, "types": ["ror_display", "label"]}]
    for alias in aliases or []:
        names.append({"value": alias, "types": ["alias"]})
    for label in labels or []:
        names.append({"value": label, "types": ["label"]})
    for acronym in acronyms or []:
        names.append({"value": acronym, "types": ["acronym"]})
    location = {"geonames_details": {"country_code": country_code}}
    if geonames_id is not None:
        location["geonames_id"] = geonames_id
    return {"id": ror_id, "status": status, "names": names, "locations": [location]}


def _data_source(*records):
    anchors = [
        _ror_record("https://ror.org/anchorus", "Anchor US", "US", NYC),
        _ror_record("https://ror.org/anchorde", "Anchor DE", "DE", BERLIN),
        _ror_record("https://ror.org/anchorfr", "Anchor FR", "FR", PARIS),
        _ror_record("https://ror.org/anchorjp", "Anchor JP", "JP", TOKYO),
    ]
    return DataSource(anchors + list(records))


def _input_json(display_name, geonames_id, aliases=None, labels=None, acronyms=None,
                country_code=None, ror_id=""):
    record = _ror_record(ror_id, display_name, country_code, geonames_id, aliases, labels, acronyms)
    if country_code is None:
        del record["locations"][0]["geonames_details"]
    record["id"] = ror_id
    return record


def _make_json_ctx(tmp_path, records, data_source, geonames_user="testuser"):
    json_dir = tmp_path / "json"
    json_dir.mkdir(parents=True, exist_ok=True)
    for i, record in enumerate(records):
        (json_dir / f"rec{i:04d}.json").write_text(json.dumps(record), encoding="utf-8")
    return ValidatorContext(
        csv_file=None,
        json_dir=json_dir,
        output_dir=tmp_path / "output",
        data_source=data_source,
        geonames_user=geonames_user,
    )


def _csv_row(display_name, geonames_id, aliases="", labels="", html_url=""):
    return {
        "html_url": html_url,
        "names.types.ror_display": display_name,
        "names.types.alias": aliases,
        "names.types.label": labels,
        "locations.geonames_id": str(geonames_id),
    }


def _make_csv_ctx(tmp_path, rows, data_source, geonames_user="testuser"):
    csv_file = tmp_path / "input.csv"
    if not rows:
        csv_file.write_text("", encoding="utf-8")
    else:
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    return ValidatorContext(
        csv_file=csv_file,
        json_dir=None,
        output_dir=tmp_path / "output",
        data_source=data_source,
        geonames_user=geonames_user,
    )


class TestProductionDuplicatesMetadata:
    def test_name(self):
        assert ProductionDuplicatesValidator().name == "production-duplicates"

    def test_supported_formats(self):
        assert ProductionDuplicatesValidator().supported_formats == {"csv", "json"}

    def test_requires_geonames(self):
        assert ProductionDuplicatesValidator().requires_geonames is True

    def test_requires_data_source(self):
        assert ProductionDuplicatesValidator().requires_data_source is True

    def test_output_filename(self):
        assert ProductionDuplicatesValidator().output_filename == "production_duplicates.csv"

    def test_output_fields(self):
        assert ProductionDuplicatesValidator().output_fields == [
            "issue_url",
            "input_name",
            "matched_ror_id",
            "matched_name",
            "match_ratio",
        ]

    def test_can_run_without_geonames(self, tmp_path):
        ctx = ValidatorContext(None, None, tmp_path, _data_source(), None)
        can, msg = ProductionDuplicatesValidator().can_run(ctx)
        assert can is False
        assert "geonames" in msg.lower()

    def test_can_run_without_data_source(self, tmp_path):
        ctx = ValidatorContext(None, None, tmp_path, None, "testuser")
        can, msg = ProductionDuplicatesValidator().can_run(ctx)
        assert can is False
        assert "data-dump" in msg

    def test_can_run_with_geonames_and_data_source(self, tmp_path):
        ctx = ValidatorContext(None, None, tmp_path, _data_source(), "testuser")
        can, _ = ProductionDuplicatesValidator().can_run(ctx)
        assert can is True


class TestGetCountryCodeFromResult:
    def test_returns_country_code(self):
        assert get_country_code_from_result(_ror_record("x", "Org", "US")) == "US"

    def test_returns_none_when_no_locations(self):
        assert get_country_code_from_result({"locations": []}) is None

    def test_returns_none_when_locations_key_missing(self):
        assert get_country_code_from_result({}) is None

    def test_returns_none_when_no_geonames_details(self):
        assert get_country_code_from_result({"locations": [{}]}) is None

    def test_returns_none_when_no_country_code(self):
        assert get_country_code_from_result({"locations": [{"geonames_details": {}}]}) is None


class TestGetAllNamesFromResult:
    def test_returns_display_alias_and_label(self):
        record = _ror_record("x", "Main Org", "US", aliases=["Alias One"], labels=["Label One"])
        assert get_all_names_from_result(record) == ["Main Org", "Alias One", "Label One"]

    def test_excludes_acronyms(self):
        record = _ror_record("x", "Main Org", "US", acronyms=["MO"])
        assert get_all_names_from_result(record) == ["Main Org"]

    def test_returns_empty_when_no_names(self):
        assert get_all_names_from_result({"names": []}) == []

    def test_returns_empty_when_names_key_missing(self):
        assert get_all_names_from_result({}) == []


class TestParseCsvNames:
    def test_parses_display_name(self):
        assert parse_csv_names({"names.types.ror_display": "University of Test"}) == ["University of Test"]

    def test_parses_aliases_and_labels(self):
        row = {
            "names.types.ror_display": "University of Test",
            "names.types.alias": "UTest; Test University",
            "names.types.label": "Universite de Test; Test Uni",
        }
        assert parse_csv_names(row) == [
            "University of Test", "UTest", "Test University", "Universite de Test", "Test Uni",
        ]

    def test_returns_empty_for_empty_row(self):
        assert parse_csv_names({}) == []

    def test_skips_empty_values(self):
        row = {"names.types.ror_display": "", "names.types.alias": "", "names.types.label": ""}
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


class TestBuildGeonamesCountryIndex:
    def test_indexes_all_locations_of_all_statuses(self):
        records = [
            _ror_record("a", "A", "US", NYC),
            _ror_record("b", "B", "DE", BERLIN, status="inactive"),
            {"id": "c", "locations": [
                {"geonames_id": PARIS, "geonames_details": {"country_code": "FR"}},
                {"geonames_id": TOKYO, "geonames_details": {"country_code": "JP"}},
            ]},
        ]
        assert build_geonames_country_index(records) == {
            str(NYC): "US", str(BERLIN): "DE", str(PARIS): "FR", str(TOKYO): "JP",
        }

    def test_skips_locations_without_id_or_country(self):
        records = [{"locations": [{"geonames_id": 1}, {"geonames_details": {"country_code": "US"}}]}]
        assert build_geonames_country_index(records) == {}


class TestResolveCountries:
    def _info(self, geonames_id, country_code=None, issue_url="issue"):
        return {"issue_url": issue_url, "names": ["X"], "geonames_id": str(geonames_id),
                "country_code": country_code}

    @patch(GEONAMES_CLIENT)
    def test_ids_in_data_dump_need_no_api_call(self, mock_cls):
        records = _data_source().get_all_records()
        countries = resolve_countries([self._info(NYC), self._info(BERLIN)], records, "user")
        assert countries[str(NYC)] == "US"
        assert countries[str(BERLIN)] == "DE"
        mock_cls.assert_not_called()

    @patch(GEONAMES_CLIENT)
    def test_embedded_country_code_needs_no_api_call(self, mock_cls):
        countries = resolve_countries([self._info(424242, "NZ")], [], "user")
        assert countries["424242"] == "NZ"
        mock_cls.assert_not_called()

    @patch(GEONAMES_CLIENT)
    def test_data_dump_takes_precedence_over_embedded_country(self, mock_cls):
        records = _data_source().get_all_records()
        countries = resolve_countries([self._info(NYC, "CA")], records, "user")
        assert countries[str(NYC)] == "US"

    @patch(GEONAMES_CLIENT)
    def test_unknown_ids_fall_back_to_geonames_once_each(self, mock_cls):
        client = MagicMock()
        client.get_country_code.side_effect = lambda gid, record_identifier="": {"111": "BR", "222": None}[gid]
        mock_cls.return_value = client
        infos = [self._info(111, issue_url="i1"), self._info(111, issue_url="i2"), self._info(222, issue_url="i3")]

        countries = resolve_countries(infos, [], "user")

        mock_cls.assert_called_once_with("user")
        assert countries["111"] == "BR"
        assert countries["222"] is None
        calls = sorted(call.args[0] for call in client.get_country_code.call_args_list)
        assert calls == ["111", "222"]
        client.get_country_code.assert_any_call("111", record_identifier="i1")


class TestProductionDuplicatesJSON:
    @patch(GEONAMES_CLIENT)
    def test_finds_duplicate_matching_country(self, mock_cls, tmp_path):
        ds = _data_source(_ror_record("https://ror.org/existing001", "University of Testing", "US"))
        ctx = _make_json_ctx(tmp_path, [_input_json("University of Testing", NYC)], ds)

        results = ProductionDuplicatesValidator().run(ctx)

        assert results == [{
            "issue_url": "University of Testing",
            "input_name": "University of Testing",
            "matched_ror_id": "https://ror.org/existing001",
            "matched_name": "University of Testing",
            "match_ratio": 100,
        }]
        mock_cls.assert_not_called()

    def test_filters_by_country_mismatch(self, tmp_path):
        ds = _data_source(_ror_record("https://ror.org/existing001", "University of Testing", "GB"))
        ctx = _make_json_ctx(tmp_path, [_input_json("University of Testing", NYC)], ds)
        assert ProductionDuplicatesValidator().run(ctx) == []

    def test_country_comes_from_first_location_of_ror_record(self, tmp_path):
        existing = _ror_record("https://ror.org/existing001", "University of Testing", "GB")
        existing["locations"].append({"geonames_details": {"country_code": "US"}})
        ctx = _make_json_ctx(tmp_path, [_input_json("University of Testing", NYC)], _data_source(existing))
        assert ProductionDuplicatesValidator().run(ctx) == []

    def test_below_threshold_not_reported(self, tmp_path):
        ds = _data_source(_ror_record("https://ror.org/x", "Completely Different Organization Name XYZ", "US"))
        ctx = _make_json_ctx(tmp_path, [_input_json("University of Testing", NYC)], ds)
        assert ProductionDuplicatesValidator().run(ctx) == []

    def test_fuzzy_match_reports_thefuzz_score(self, tmp_path):
        ds = _data_source(_ror_record("https://ror.org/x", "University of Testin", "US"))
        ctx = _make_json_ctx(tmp_path, [_input_json("University of Testing", NYC)], ds)
        results = ProductionDuplicatesValidator().run(ctx)
        expected = fuzz.ratio(normalize_text("University of Testing"), normalize_text("University of Testin"))
        assert [r["match_ratio"] for r in results] == [expected]

    def test_matches_against_aliases_and_labels(self, tmp_path):
        ds = _data_source(
            _ror_record("https://ror.org/a", "Different Display Name", "DE", aliases=["Technische Universitat Berlin"]),
            _ror_record("https://ror.org/b", "Other Display Name", "DE", labels=["Technische Universität Berlin"]),
        )
        ctx = _make_json_ctx(tmp_path, [_input_json("Technische Universitat Berlin", BERLIN)], ds)
        results = ProductionDuplicatesValidator().run(ctx)
        assert {(r["matched_ror_id"], r["matched_name"]) for r in results} == {
            ("https://ror.org/a", "Technische Universitat Berlin"),
            ("https://ror.org/b", "Technische Universität Berlin"),
        }

    def test_does_not_match_acronyms_of_ror_records(self, tmp_path):
        ds = _data_source(_ror_record("https://ror.org/a", "Something Else", "US", acronyms=["Testing Univ Org"]))
        ctx = _make_json_ctx(tmp_path, [_input_json("Testing Univ Org", NYC)], ds)
        assert ProductionDuplicatesValidator().run(ctx) == []

    @pytest.mark.parametrize("status", ["inactive", "withdrawn"])
    def test_ignores_non_active_records(self, status, tmp_path):
        ds = _data_source(_ror_record("https://ror.org/x", "University of Testing", "US", status=status))
        ctx = _make_json_ctx(tmp_path, [_input_json("University of Testing", NYC)], ds)
        assert ProductionDuplicatesValidator().run(ctx) == []

    def test_reports_first_matching_name_of_each_record_once(self, tmp_path):
        ds = _data_source(_ror_record(
            "https://ror.org/x", "University of Testin", "US", aliases=["University of Testing"],
        ))
        ctx = _make_json_ctx(tmp_path, [_input_json("University of Testing", NYC)], ds)
        results = ProductionDuplicatesValidator().run(ctx)
        assert [(r["matched_name"], r["match_ratio"]) for r in results] == [
            ("University of Testin", fuzz.ratio("university of testing", "university of testin")),
        ]

    def test_deduplicates_on_input_name_and_ror_id(self, tmp_path):
        ds = _data_source(_ror_record(
            "https://ror.org/x", "University of Testing", "US", aliases=["University of Testing"],
        ))
        record = _input_json("University of Testing", NYC, aliases=["University of Testing"])
        ctx = _make_json_ctx(tmp_path, [record], ds)
        results = ProductionDuplicatesValidator().run(ctx)
        assert len(results) == 1

    def test_same_name_in_two_input_records_reported_once_for_first(self, tmp_path):
        ds = _data_source(_ror_record("https://ror.org/x", "Shared Name Institute", "US"))
        records = [_input_json("Shared Name Institute", NYC), _input_json("Shared Name Institute", NYC)]
        ctx = _make_json_ctx(tmp_path, records, ds)
        assert len(ProductionDuplicatesValidator().run(ctx)) == 1

    def test_uses_embedded_country_for_ids_not_in_dump(self, tmp_path):
        ds = _data_source(_ror_record("https://ror.org/x", "Auckland Testing Trust", "NZ"))
        record = _input_json("Auckland Testing Trust", 2193733, country_code="NZ")
        ctx = _make_json_ctx(tmp_path, [record], ds)
        with patch(GEONAMES_CLIENT) as mock_cls:
            results = ProductionDuplicatesValidator().run(ctx)
        mock_cls.assert_not_called()
        assert [r["matched_ror_id"] for r in results] == ["https://ror.org/x"]

    @patch(GEONAMES_CLIENT)
    def test_geonames_fallback_for_ids_not_found_locally(self, mock_cls, tmp_path):
        client = MagicMock()
        client.get_country_code.return_value = "NZ"
        mock_cls.return_value = client
        ds = _data_source(_ror_record("https://ror.org/x", "Auckland Testing Trust", "NZ"))
        ctx = _make_json_ctx(tmp_path, [_input_json("Auckland Testing Trust", 2193733)], ds)

        results = ProductionDuplicatesValidator().run(ctx)

        client.get_country_code.assert_called_once_with("2193733", record_identifier="Auckland Testing Trust")
        assert [r["matched_ror_id"] for r in results] == ["https://ror.org/x"]

    @patch(GEONAMES_CLIENT)
    def test_geonames_lookup_fails_skips_record(self, mock_cls, tmp_path):
        client = MagicMock()
        client.get_country_code.return_value = None
        mock_cls.return_value = client
        ds = _data_source(_ror_record("https://ror.org/x", "University of Testing", "US"))
        ctx = _make_json_ctx(tmp_path, [_input_json("University of Testing", 9999999)], ds)
        assert ProductionDuplicatesValidator().run(ctx) == []

    def test_empty_json_dir(self, tmp_path):
        ctx = _make_json_ctx(tmp_path, [], _data_source())
        assert ProductionDuplicatesValidator().run(ctx) == []

    def test_multiple_input_records(self, tmp_path):
        ds = _data_source(_ror_record("https://ror.org/x", "University of Testing", "US"))
        records = [
            _input_json("University of Testing", NYC),
            _input_json("Completely Novel Organization", NYC),
        ]
        ctx = _make_json_ctx(tmp_path, records, ds)
        matched_names = [r["input_name"] for r in ProductionDuplicatesValidator().run(ctx)]
        assert matched_names == ["University of Testing"]

    def test_searches_display_alias_label_but_not_acronym(self, tmp_path):
        ds = _data_source(
            _ror_record("https://ror.org/a", "Technische Universitat Berlin", "DE"),
            _ror_record("https://ror.org/b", "TU Berlin", "DE"),
            _ror_record("https://ror.org/c", "Technical University of Berlin", "DE"),
            _ror_record("https://ror.org/d", "TUB", "DE"),
        )
        record = _input_json(
            "Technische Universitat Berlin", BERLIN, aliases=["TU Berlin"],
            labels=["Technical University of Berlin"], acronyms=["TUB"],
        )
        ctx = _make_json_ctx(tmp_path, [record], ds)
        results = ProductionDuplicatesValidator().run(ctx)
        assert [r["matched_ror_id"] for r in results] == [
            "https://ror.org/a", "https://ror.org/b", "https://ror.org/c",
        ]

    def test_issue_url_falls_back_to_id_without_display_name(self, tmp_path):
        ds = _data_source(_ror_record("https://ror.org/x", "Test University", "US"))
        record = _input_json("ignored", NYC, ror_id="https://ror.org/input1")
        record["names"] = [{"value": "Test University", "types": ["label"]}]
        ctx = _make_json_ctx(tmp_path, [record], ds)
        results = ProductionDuplicatesValidator().run(ctx)
        assert results[0]["issue_url"] == "https://ror.org/input1"

    def test_update_record_matches_itself_in_production(self, tmp_path):
        existing = _ror_record("https://ror.org/x", "Test University", "US", NYC)
        ctx = _make_json_ctx(tmp_path, [existing], _data_source(existing))
        results = ProductionDuplicatesValidator().run(ctx)
        assert [r["matched_ror_id"] for r in results] == ["https://ror.org/x"]


class TestProductionDuplicatesCSV:
    def test_finds_duplicate_matching_country_csv(self, tmp_path):
        ds = _data_source(_ror_record("https://ror.org/existing001", "University of Testing", "US"))
        rows = [_csv_row("University of Testing", NYC, html_url="https://github.com/x/1")]
        results = ProductionDuplicatesValidator().run(_make_csv_ctx(tmp_path, rows, ds))
        assert results == [{
            "issue_url": "https://github.com/x/1",
            "input_name": "University of Testing",
            "matched_ror_id": "https://ror.org/existing001",
            "matched_name": "University of Testing",
            "match_ratio": 100,
        }]

    def test_filters_by_country_mismatch_csv(self, tmp_path):
        ds = _data_source(_ror_record("https://ror.org/x", "University of Testing", "JP"))
        rows = [_csv_row("University of Testing", NYC)]
        assert ProductionDuplicatesValidator().run(_make_csv_ctx(tmp_path, rows, ds)) == []

    def test_below_threshold_not_reported_csv(self, tmp_path):
        ds = _data_source(_ror_record("https://ror.org/x", "Completely Different Organization Name XYZ", "US"))
        rows = [_csv_row("University of Testing", NYC)]
        assert ProductionDuplicatesValidator().run(_make_csv_ctx(tmp_path, rows, ds)) == []

    def test_csv_matches_semicolon_separated_aliases_and_labels(self, tmp_path):
        ds = _data_source(
            _ror_record("https://ror.org/a", "Northern Coastal Observatory", "US"),
            _ror_record("https://ror.org/b", "Mountain Bioscience Laboratory", "US"),
            _ror_record("https://ror.org/c", "Desert Ecology Station", "US"),
        )
        rows = [_csv_row("Main University", NYC,
                         aliases="Northern Coastal Observatory; Mountain Bioscience Laboratory",
                         labels="Desert Ecology Station")]
        results = ProductionDuplicatesValidator().run(_make_csv_ctx(tmp_path, rows, ds))
        assert [(r["input_name"], r["matched_ror_id"]) for r in results] == [
            ("Northern Coastal Observatory", "https://ror.org/a"),
            ("Mountain Bioscience Laboratory", "https://ror.org/b"),
            ("Desert Ecology Station", "https://ror.org/c"),
        ]

    def test_csv_strips_language_marker_but_reports_raw_input_name(self, tmp_path):
        ds = _data_source(_ror_record("https://ror.org/x", "University of Paris", "FR"))
        rows = [_csv_row("Universite de Paris", PARIS, labels="University of Paris*en")]
        results = ProductionDuplicatesValidator().run(_make_csv_ctx(tmp_path, rows, ds))
        assert [(r["input_name"], r["match_ratio"]) for r in results] == [("University of Paris*en", 100)]

    @patch(GEONAMES_CLIENT)
    def test_csv_geonames_lookup_fails_skips_record(self, mock_cls, tmp_path):
        mock_cls.return_value.get_country_code.return_value = None
        ds = _data_source(_ror_record("https://ror.org/x", "University of Testing", "US"))
        rows = [_csv_row("University of Testing", 9999999)]
        assert ProductionDuplicatesValidator().run(_make_csv_ctx(tmp_path, rows, ds)) == []

    @patch(GEONAMES_CLIENT)
    def test_csv_geonames_fallback(self, mock_cls, tmp_path):
        mock_cls.return_value.get_country_code.return_value = "US"
        ds = _data_source(_ror_record("https://ror.org/x", "University of Testing", "US"))
        rows = [_csv_row("University of Testing", 9999999, html_url="https://github.com/x/1")]
        results = ProductionDuplicatesValidator().run(_make_csv_ctx(tmp_path, rows, ds))
        mock_cls.return_value.get_country_code.assert_called_once_with(
            "9999999", record_identifier="https://github.com/x/1"
        )
        assert [r["matched_ror_id"] for r in results] == ["https://ror.org/x"]

    def test_csv_multiple_rows_in_input_order(self, tmp_path):
        ds = _data_source(
            _ror_record("https://ror.org/a", "University of Testing", "US"),
            _ror_record("https://ror.org/b", "Berlin Testing Institute", "DE"),
        )
        rows = [
            _csv_row("Berlin Testing Institute", BERLIN),
            _csv_row("Completely Novel Organization", NYC),
            _csv_row("University of Testing", NYC),
        ]
        results = ProductionDuplicatesValidator().run(_make_csv_ctx(tmp_path, rows, ds))
        assert [r["matched_ror_id"] for r in results] == ["https://ror.org/b", "https://ror.org/a"]


class TestProductionDuplicatesEdgeCases:
    def test_returns_empty_when_no_input(self, tmp_path):
        ctx = ValidatorContext(None, None, tmp_path, None, "testuser")
        assert ProductionDuplicatesValidator().run(ctx) == []

    def test_prefers_json_over_csv(self, tmp_path):
        ds = _data_source(
            _ror_record("https://ror.org/j", "JSON Org Name", "US"),
            _ror_record("https://ror.org/c", "CSV Org Name", "US"),
        )
        ctx = _make_json_ctx(tmp_path, [_input_json("JSON Org Name", NYC)], ds)
        csv_ctx = _make_csv_ctx(tmp_path, [_csv_row("CSV Org Name", NYC)], ds)
        ctx.csv_file = csv_ctx.csv_file
        results = ProductionDuplicatesValidator().run(ctx)
        assert [r["input_name"] for r in results] == ["JSON Org Name"]

    def test_record_with_no_locations(self, tmp_path):
        record = _input_json("No Location Org", NYC)
        record["locations"] = []
        ctx = _make_json_ctx(tmp_path, [record], _data_source())
        assert ProductionDuplicatesValidator().run(ctx) == []

    def test_record_with_only_acronym(self, tmp_path):
        record = _input_json("ignored", NYC)
        record["names"] = [{"value": "ACR", "types": ["acronym"]}]
        ctx = _make_json_ctx(tmp_path, [record], _data_source(_ror_record("x", "ACR", "US")))
        assert ProductionDuplicatesValidator().run(ctx) == []

    def test_csv_no_geonames_id(self, tmp_path):
        ds = _data_source(_ror_record("https://ror.org/x", "University of Testing", "US"))
        rows = [_csv_row("University of Testing", "")]
        assert ProductionDuplicatesValidator().run(_make_csv_ctx(tmp_path, rows, ds)) == []

    def test_name_that_normalizes_to_empty_is_skipped(self, tmp_path):
        ds = _data_source(_ror_record("https://ror.org/x", "!!!", "US"))
        ctx = _make_json_ctx(tmp_path, [_input_json("???", NYC)], ds)
        assert ProductionDuplicatesValidator().run(ctx) == []


def _brute_force(record_infos, records, countries):
    """Compare every input name with every name of every active same-country record."""
    found = {}
    for info in record_infos:
        country = countries.get(info["geonames_id"])
        if not country:
            continue
        for input_name in info["names"]:
            normalized = normalize_text(clean_name(input_name))
            if not normalized:
                continue
            for record in records:
                if record.get("status") != "active" or get_country_code_from_result(record) != country:
                    continue
                for name in get_all_names_from_result(record):
                    score = fuzz.ratio(normalized, normalize_text(name))
                    if score >= FUZZY_THRESHOLD:
                        found.setdefault((input_name, record["id"]), (name, score))
                        break
    return found


@pytest.mark.parametrize("seed", range(5))
def test_matches_brute_force_search(seed):
    rng = random.Random(seed)
    words = ["University", "Institute", "of", "Testing", "Research", "National", "Centre",
             "Center", "Hospital", "Berlin", "Paris", "Société", "大学", "College"]
    countries_pool = ["US", "DE", "FR"]

    def name():
        return " ".join(rng.choice(words) for _ in range(rng.randint(2, 4)))

    records = []
    for k in range(300):
        records.append(_ror_record(
            f"https://ror.org/r{k}", name(), rng.choice(countries_pool),
            aliases=[name() for _ in range(rng.randint(0, 2))],
            status=rng.choice(["active", "active", "active", "inactive"]),
        ))
    geonames_ids = {"1": "US", "2": "DE", "3": "FR", "4": None}
    infos = [
        {"issue_url": f"i{k}", "names": [name() + rng.choice(["", "*en"]) for _ in range(rng.randint(1, 3))],
         "geonames_id": rng.choice(list(geonames_ids))}
        for k in range(60)
    ]

    results = find_production_duplicates(infos, records, geonames_ids)

    assert {(r["input_name"], r["matched_ror_id"]): (r["matched_name"], r["match_ratio"]) for r in results} \
        == _brute_force(infos, records, geonames_ids)
    assert len(results) == len({(r["input_name"], r["matched_ror_id"]) for r in results})
