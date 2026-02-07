from curation_validation.core.extract import extract_fields


SAMPLE_JSON_RECORD = {
    "id": "https://ror.org/012345",
    "status": "active",
    "types": ["education", "funder"],
    "established": 1990,
    "names": [
        {"value": "Test University", "types": ["label", "ror_display"], "lang": "en"},
        {"value": "TU", "types": ["acronym"], "lang": "en"},
        {"value": "Uni Test", "types": ["alias"], "lang": "en"},
        {"value": "Testuni", "types": ["label"], "lang": "de"},
    ],
    "links": [
        {"type": "website", "value": "https://test.edu"},
        {"type": "wikipedia", "value": "https://en.wikipedia.org/wiki/Test"},
    ],
    "locations": [{"geonames_id": 5367440, "geonames_details": {"country_code": "US", "name": "City"}}],
    "external_ids": [
        {"type": "wikidata", "all": ["Q12345"], "preferred": "Q12345"},
        {"type": "isni", "all": ["0000 0001 2345 6789"], "preferred": "0000 0001 2345 6789"},
    ],
    "relationships": [],
    "domains": ["test.edu"],
}

SAMPLE_CSV_ROW = {
    "id": "https://ror.org/012345",
    "html_url": "https://github.com/issues/1",
    "status": "active",
    "types": "education;funder",
    "names.types.ror_display": "Test University*en",
    "names.types.acronym": "TU*en",
    "names.types.alias": "Uni Test*en",
    "names.types.label": "Testuni*de",
    "links.type.website": "https://test.edu",
    "links.type.wikipedia": "https://en.wikipedia.org/wiki/Test",
    "established": "1990",
    "external_ids.type.wikidata.all": "Q12345",
    "external_ids.type.wikidata.preferred": "Q12345",
    "external_ids.type.isni.all": "0000 0001 2345 6789",
    "external_ids.type.isni.preferred": "0000 0001 2345 6789",
    "external_ids.type.fundref.all": "",
    "external_ids.type.fundref.preferred": "",
    "locations.geonames_id": "5367440",
    "city": "City",
    "country": "United States",
    "domains": "test.edu",
}


class TestExtractFieldsJson:
    def test_extracts_status(self):
        result = extract_fields(SAMPLE_JSON_RECORD, "json")
        assert result["status"] == ["active"]

    def test_extracts_types(self):
        result = extract_fields(SAMPLE_JSON_RECORD, "json")
        assert set(result["types"]) == {"education", "funder"}

    def test_extracts_ror_display(self):
        result = extract_fields(SAMPLE_JSON_RECORD, "json")
        assert "Test University" in result["names.types.ror_display"]

    def test_extracts_acronym(self):
        result = extract_fields(SAMPLE_JSON_RECORD, "json")
        assert "TU" in result["names.types.acronym"]

    def test_extracts_alias(self):
        result = extract_fields(SAMPLE_JSON_RECORD, "json")
        assert "Uni Test" in result["names.types.alias"]

    def test_extracts_label(self):
        result = extract_fields(SAMPLE_JSON_RECORD, "json")
        assert "Testuni" in result["names.types.label"]

    def test_extracts_website(self):
        result = extract_fields(SAMPLE_JSON_RECORD, "json")
        assert "https://test.edu" in result["links.type.website"]

    def test_extracts_wikipedia(self):
        result = extract_fields(SAMPLE_JSON_RECORD, "json")
        assert "https://en.wikipedia.org/wiki/Test" in result["links.type.wikipedia"]

    def test_extracts_established(self):
        result = extract_fields(SAMPLE_JSON_RECORD, "json")
        assert "1990" in result["established"]

    def test_extracts_geonames_id(self):
        result = extract_fields(SAMPLE_JSON_RECORD, "json")
        assert "5367440" in result["locations.geonames_id"]

    def test_extracts_external_ids(self):
        result = extract_fields(SAMPLE_JSON_RECORD, "json")
        assert "Q12345" in result["external_ids.type.wikidata.all"]
        assert "Q12345" in result["external_ids.type.wikidata.preferred"]

    def test_extracts_domains(self):
        result = extract_fields(SAMPLE_JSON_RECORD, "json")
        assert "test.edu" in result["domains"]

    def test_all_values_are_lists(self):
        result = extract_fields(SAMPLE_JSON_RECORD, "json")
        for key, value in result.items():
            assert isinstance(value, list), f"{key} should be a list"

    def test_all_values_are_strings(self):
        result = extract_fields(SAMPLE_JSON_RECORD, "json")
        for key, values in result.items():
            for v in values:
                assert isinstance(v, str), f"{key} contains non-string: {v!r}"

    def test_extracts_record_id(self):
        result = extract_fields(SAMPLE_JSON_RECORD, "json")
        assert result["id"] == ["https://ror.org/012345"]

    def test_empty_external_ids(self):
        record = {**SAMPLE_JSON_RECORD, "external_ids": []}
        result = extract_fields(record, "json")
        assert result["external_ids.type.wikidata.all"] == []
        assert result["external_ids.type.fundref.all"] == []


class TestExtractFieldsCsv:
    def test_extracts_status(self):
        result = extract_fields(SAMPLE_CSV_ROW, "csv")
        assert result["status"] == ["active"]

    def test_extracts_types_splits_semicolon(self):
        result = extract_fields(SAMPLE_CSV_ROW, "csv")
        assert set(result["types"]) == {"education", "funder"}

    def test_extracts_names(self):
        result = extract_fields(SAMPLE_CSV_ROW, "csv")
        assert "Test University*en" in result["names.types.ror_display"]

    def test_extracts_website(self):
        result = extract_fields(SAMPLE_CSV_ROW, "csv")
        assert "https://test.edu" in result["links.type.website"]

    def test_extracts_established(self):
        result = extract_fields(SAMPLE_CSV_ROW, "csv")
        assert "1990" in result["established"]

    def test_extracts_geonames_id(self):
        result = extract_fields(SAMPLE_CSV_ROW, "csv")
        assert "5367440" in result["locations.geonames_id"]

    def test_extracts_external_ids(self):
        result = extract_fields(SAMPLE_CSV_ROW, "csv")
        assert "Q12345" in result["external_ids.type.wikidata.all"]

    def test_empty_field_returns_empty_list(self):
        result = extract_fields(SAMPLE_CSV_ROW, "csv")
        assert result["external_ids.type.fundref.all"] == []

    def test_all_values_are_lists(self):
        result = extract_fields(SAMPLE_CSV_ROW, "csv")
        for key, value in result.items():
            assert isinstance(value, list), f"{key} should be a list"

    def test_multi_value_semicolons(self):
        row = {**SAMPLE_CSV_ROW, "names.types.alias": "Alias1*en;Alias2*en"}
        result = extract_fields(row, "csv")
        assert len(result["names.types.alias"]) == 2


class TestExtractFieldsConsistency:
    def test_same_fields_both_formats(self):
        json_result = extract_fields(SAMPLE_JSON_RECORD, "json")
        csv_result = extract_fields(SAMPLE_CSV_ROW, "csv")
        assert set(json_result.keys()) == set(csv_result.keys())
