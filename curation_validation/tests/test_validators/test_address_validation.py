import csv
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from curation_validation.validators.base import ValidatorContext
from curation_validation.validators.address_validation import (
    AddressValidationValidator,
    query_geonames_api,
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


def _json_record(ror_id="", display_name="Test Org", geonames_id=12345,
                  city="Springfield", country="United States"):
    return {
        "id": ror_id,
        "names": [{"value": display_name, "types": ["ror_display"]}],
        "locations": [
            {
                "geonames_id": geonames_id,
                "geonames_details": {
                    "name": city,
                    "country_name": country,
                },
            }
        ],
    }


def _csv_row(ror_id="", display_name="Test Org", geonames_id="12345",
             city="Springfield", country="United States"):
    return {
        "id": ror_id,
        "names.types.ror_display": display_name,
        "locations.geonames_id": geonames_id,
        "city": city,
        "country": country,
    }


class TestAddressValidationMetadata:
    def test_name(self):
        v = AddressValidationValidator()
        assert v.name == "address-validation"

    def test_supported_formats(self):
        v = AddressValidationValidator()
        assert v.supported_formats == {"csv", "json"}

    def test_requires_geonames(self):
        v = AddressValidationValidator()
        assert v.requires_geonames is True

    def test_output_filename(self):
        v = AddressValidationValidator()
        assert v.output_filename == "address_discrepancies.csv"

    def test_output_fields(self):
        v = AddressValidationValidator()
        expected = [
            "ror_display_name", "ror_id", "geonames_id",
            "csv_city", "csv_country",
            "geonames_city", "geonames_country", "issue",
        ]
        assert v.output_fields == expected

    def test_can_run_without_geonames_user(self, tmp_path):
        v = AddressValidationValidator()
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

    def test_can_run_with_geonames_user(self, tmp_path):
        v = AddressValidationValidator()
        ctx = ValidatorContext(
            csv_file=None,
            json_dir=None,
            output_dir=tmp_path,
            data_source=None,
            geonames_user="testuser",
        )
        can, _ = v.can_run(ctx)
        assert can is True


class TestQueryGeonamesApi:
    @patch("curation_validation.validators.address_validation.requests.get")
    def test_returns_city_and_country(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"name": "Springfield", "countryName": "United States"}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        city, country = query_geonames_api("12345", "testuser")
        assert city == "Springfield"
        assert country == "United States"

    @patch("curation_validation.validators.address_validation.requests.get")
    def test_returns_empty_on_request_error(self, mock_get):
        import requests as req
        mock_get.side_effect = req.exceptions.RequestException("timeout")

        city, country = query_geonames_api("12345", "testuser")
        assert city == ""
        assert country == ""

    @patch("curation_validation.validators.address_validation.requests.get")
    def test_returns_empty_strings_when_keys_missing(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        city, country = query_geonames_api("12345", "testuser")
        assert city == ""
        assert country == ""

    @patch("curation_validation.validators.address_validation.requests.get")
    def test_passes_correct_params(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"name": "X", "countryName": "Y"}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        query_geonames_api("99999", "myuser")
        mock_get.assert_called_once_with(
            "http://api.geonames.org/getJSON",
            params={"geonameId": "99999", "username": "myuser"},
            timeout=10,
        )


class TestAddressValidationJSON:
    @patch("curation_validation.validators.address_validation.query_geonames_api")
    def test_matching_address(self, mock_api, tmp_path):
        mock_api.return_value = ("Springfield", "United States")
        record = _json_record(city="Springfield", country="United States")
        ctx = _make_json_ctx(tmp_path, [record])
        v = AddressValidationValidator()
        results = v.run(ctx)
        assert results == []

    @patch("curation_validation.validators.address_validation.query_geonames_api")
    def test_city_mismatch(self, mock_api, tmp_path):
        mock_api.return_value = ("Shelbyville", "United States")
        record = _json_record(city="Springfield", country="United States")
        ctx = _make_json_ctx(tmp_path, [record])
        v = AddressValidationValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert "city mismatch" in results[0]["issue"]
        assert results[0]["csv_city"] == "Springfield"
        assert results[0]["geonames_city"] == "Shelbyville"

    @patch("curation_validation.validators.address_validation.query_geonames_api")
    def test_country_mismatch(self, mock_api, tmp_path):
        mock_api.return_value = ("Springfield", "Canada")
        record = _json_record(city="Springfield", country="United States")
        ctx = _make_json_ctx(tmp_path, [record])
        v = AddressValidationValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert "country mismatch" in results[0]["issue"]
        assert results[0]["csv_country"] == "United States"
        assert results[0]["geonames_country"] == "Canada"

    @patch("curation_validation.validators.address_validation.query_geonames_api")
    def test_both_city_and_country_mismatch(self, mock_api, tmp_path):
        mock_api.return_value = ("Shelbyville", "Canada")
        record = _json_record(city="Springfield", country="United States")
        ctx = _make_json_ctx(tmp_path, [record])
        v = AddressValidationValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert "city mismatch" in results[0]["issue"]
        assert "country mismatch" in results[0]["issue"]

    @patch("curation_validation.validators.address_validation.query_geonames_api")
    def test_api_error(self, mock_api, tmp_path):
        mock_api.return_value = ("", "")
        record = _json_record(city="Springfield", country="United States")
        ctx = _make_json_ctx(tmp_path, [record])
        v = AddressValidationValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert "api error" in results[0]["issue"].lower()

    @patch("curation_validation.validators.address_validation.query_geonames_api")
    def test_no_locations(self, mock_api, tmp_path):
        record = {
            "id": "",
            "names": [{"value": "No Location Org", "types": ["ror_display"]}],
            "locations": [],
        }
        ctx = _make_json_ctx(tmp_path, [record])
        v = AddressValidationValidator()
        results = v.run(ctx)
        assert results == []
        mock_api.assert_not_called()

    @patch("curation_validation.validators.address_validation.query_geonames_api")
    def test_missing_geonames_id(self, mock_api, tmp_path):
        record = {
            "id": "",
            "names": [{"value": "No GeoID Org", "types": ["ror_display"]}],
            "locations": [
                {
                    "geonames_details": {
                        "name": "Springfield",
                        "country_name": "United States",
                    },
                }
            ],
        }
        ctx = _make_json_ctx(tmp_path, [record])
        v = AddressValidationValidator()
        results = v.run(ctx)
        assert results == []
        mock_api.assert_not_called()

    @patch("curation_validation.validators.address_validation.query_geonames_api")
    def test_multiple_records(self, mock_api, tmp_path):
        def api_side_effect(geonames_id, username):
            if geonames_id == "12345":
                return ("Springfield", "United States")
            else:
                return ("Shelbyville", "United States")

        mock_api.side_effect = api_side_effect
        records = [
            _json_record(ror_id="https://ror.org/001", display_name="Match Org",
                         geonames_id=12345, city="Springfield", country="United States"),
            _json_record(ror_id="https://ror.org/002", display_name="Mismatch Org",
                         geonames_id=67890, city="Springfield", country="United States"),
        ]
        ctx = _make_json_ctx(tmp_path, records)
        v = AddressValidationValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["ror_display_name"] == "Mismatch Org"
        assert "city mismatch" in results[0]["issue"]

    @patch("curation_validation.validators.address_validation.query_geonames_api")
    def test_output_fields_present(self, mock_api, tmp_path):
        mock_api.return_value = ("Shelbyville", "Canada")
        record = _json_record(ror_id="https://ror.org/001", display_name="Test Org",
                              geonames_id=12345, city="Springfield", country="United States")
        ctx = _make_json_ctx(tmp_path, [record])
        v = AddressValidationValidator()
        results = v.run(ctx)
        assert len(results) == 1
        result = results[0]
        assert result["ror_display_name"] == "Test Org"
        assert result["ror_id"] == "https://ror.org/001"
        assert result["geonames_id"] == "12345"
        assert result["csv_city"] == "Springfield"
        assert result["csv_country"] == "United States"
        assert result["geonames_city"] == "Shelbyville"
        assert result["geonames_country"] == "Canada"

    @patch("curation_validation.validators.address_validation.query_geonames_api")
    def test_empty_json_dir(self, mock_api, tmp_path):
        json_dir = tmp_path / "json"
        json_dir.mkdir(parents=True, exist_ok=True)
        ctx = ValidatorContext(
            csv_file=None,
            json_dir=json_dir,
            output_dir=tmp_path / "output",
            data_source=None,
            geonames_user="testuser",
        )
        v = AddressValidationValidator()
        results = v.run(ctx)
        assert results == []
        mock_api.assert_not_called()


class TestAddressValidationCSV:
    @patch("curation_validation.validators.address_validation.query_geonames_api")
    def test_matching_address_csv(self, mock_api, tmp_path):
        mock_api.return_value = ("Springfield", "United States")
        row = _csv_row(city="Springfield", country="United States")
        ctx = _make_csv_ctx(tmp_path, [row])
        v = AddressValidationValidator()
        results = v.run(ctx)
        assert results == []

    @patch("curation_validation.validators.address_validation.query_geonames_api")
    def test_city_mismatch_csv(self, mock_api, tmp_path):
        mock_api.return_value = ("Shelbyville", "United States")
        row = _csv_row(city="Springfield", country="United States")
        ctx = _make_csv_ctx(tmp_path, [row])
        v = AddressValidationValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert "city mismatch" in results[0]["issue"]
        assert results[0]["csv_city"] == "Springfield"
        assert results[0]["geonames_city"] == "Shelbyville"

    @patch("curation_validation.validators.address_validation.query_geonames_api")
    def test_country_mismatch_csv(self, mock_api, tmp_path):
        mock_api.return_value = ("Springfield", "Canada")
        row = _csv_row(city="Springfield", country="United States")
        ctx = _make_csv_ctx(tmp_path, [row])
        v = AddressValidationValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert "country mismatch" in results[0]["issue"]
        assert results[0]["csv_country"] == "United States"
        assert results[0]["geonames_country"] == "Canada"

    @patch("curation_validation.validators.address_validation.query_geonames_api")
    def test_both_mismatch_csv(self, mock_api, tmp_path):
        mock_api.return_value = ("Shelbyville", "Canada")
        row = _csv_row(city="Springfield", country="United States")
        ctx = _make_csv_ctx(tmp_path, [row])
        v = AddressValidationValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert "city mismatch" in results[0]["issue"]
        assert "country mismatch" in results[0]["issue"]

    @patch("curation_validation.validators.address_validation.query_geonames_api")
    def test_api_error_csv(self, mock_api, tmp_path):
        mock_api.return_value = ("", "")
        row = _csv_row()
        ctx = _make_csv_ctx(tmp_path, [row])
        v = AddressValidationValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert "api error" in results[0]["issue"].lower()

    @patch("curation_validation.validators.address_validation.query_geonames_api")
    def test_empty_geonames_id_csv(self, mock_api, tmp_path):
        row = _csv_row(geonames_id="")
        ctx = _make_csv_ctx(tmp_path, [row])
        v = AddressValidationValidator()
        results = v.run(ctx)
        assert results == []
        mock_api.assert_not_called()

    @patch("curation_validation.validators.address_validation.query_geonames_api")
    def test_multiple_rows_csv(self, mock_api, tmp_path):
        def api_side_effect(geonames_id, username):
            if geonames_id == "12345":
                return ("Springfield", "United States")
            else:
                return ("Shelbyville", "United States")

        mock_api.side_effect = api_side_effect
        rows = [
            _csv_row(ror_id="https://ror.org/001", display_name="Match Org",
                      geonames_id="12345", city="Springfield", country="United States"),
            _csv_row(ror_id="https://ror.org/002", display_name="Mismatch Org",
                      geonames_id="67890", city="Springfield", country="United States"),
        ]
        ctx = _make_csv_ctx(tmp_path, rows)
        v = AddressValidationValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["ror_display_name"] == "Mismatch Org"
        assert "city mismatch" in results[0]["issue"]

    @patch("curation_validation.validators.address_validation.query_geonames_api")
    def test_csv_output_fields(self, mock_api, tmp_path):
        mock_api.return_value = ("Shelbyville", "Canada")
        row = _csv_row(ror_id="https://ror.org/001", display_name="Test Org",
                        geonames_id="12345", city="Springfield", country="United States")
        ctx = _make_csv_ctx(tmp_path, [row])
        v = AddressValidationValidator()
        results = v.run(ctx)
        assert len(results) == 1
        result = results[0]
        assert result["ror_display_name"] == "Test Org"
        assert result["ror_id"] == "https://ror.org/001"
        assert result["geonames_id"] == "12345"
        assert result["csv_city"] == "Springfield"
        assert result["csv_country"] == "United States"
        assert result["geonames_city"] == "Shelbyville"
        assert result["geonames_country"] == "Canada"

    @patch("curation_validation.validators.address_validation.query_geonames_api")
    def test_csv_whitespace_handling(self, mock_api, tmp_path):
        mock_api.return_value = ("Springfield", "United States")
        row = _csv_row(geonames_id="  12345  ", city="  Springfield  ", country="  United States  ")
        ctx = _make_csv_ctx(tmp_path, [row])
        v = AddressValidationValidator()
        results = v.run(ctx)
        assert results == []
        mock_api.assert_called_once_with("12345", "testuser")


class TestAddressValidationEdgeCases:
    def test_returns_empty_when_no_input(self, tmp_path):
        ctx = ValidatorContext(
            csv_file=None,
            json_dir=None,
            output_dir=tmp_path,
            data_source=None,
            geonames_user="testuser",
        )
        v = AddressValidationValidator()
        results = v.run(ctx)
        assert results == []

    @patch("curation_validation.validators.address_validation.query_geonames_api")
    def test_prefers_json_over_csv(self, mock_api, tmp_path):
        mock_api.return_value = ("Shelbyville", "United States")

        json_dir = tmp_path / "json"
        json_dir.mkdir(parents=True, exist_ok=True)
        json_record = _json_record(display_name="JSON Org", city="Springfield",
                                    country="United States")
        (json_dir / "rec.json").write_text(json.dumps(json_record), encoding="utf-8")

        csv_file = tmp_path / "input.csv"
        fieldnames = ["id", "names.types.ror_display", "locations.geonames_id", "city", "country"]
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(_csv_row(display_name="CSV Org"))

        ctx = ValidatorContext(
            csv_file=csv_file,
            json_dir=json_dir,
            output_dir=tmp_path / "output",
            data_source=None,
            geonames_user="testuser",
        )
        v = AddressValidationValidator()
        results = v.run(ctx)
        assert len(results) == 1
        assert results[0]["ror_display_name"] == "JSON Org"

    @patch("curation_validation.validators.address_validation.query_geonames_api")
    def test_geonames_id_converted_to_string(self, mock_api, tmp_path):
        mock_api.return_value = ("Springfield", "United States")
        record = _json_record(geonames_id=12345, city="Springfield", country="United States")
        ctx = _make_json_ctx(tmp_path, [record])
        v = AddressValidationValidator()
        v.run(ctx)
        mock_api.assert_called_once_with("12345", "testuser")
