from curation_validation.core.json_utils import (
    flatten_json,
    simplify_json,
    simplify_and_invert_json,
)


SAMPLE_RECORD = {
    "id": "https://ror.org/012345",
    "status": "active",
    "types": ["education"],
    "established": 1990,
    "names": [
        {"value": "Test University", "types": ["label", "ror_display"], "lang": "en"},
        {"value": "TU", "types": ["acronym"], "lang": "en"},
    ],
    "links": [
        {"type": "website", "value": "https://test.edu"},
        {"type": "wikipedia", "value": "https://en.wikipedia.org/wiki/Test"},
    ],
    "locations": [{"geonames_id": 5367440, "geonames_details": {"country_code": "US", "name": "City"}}],
    "external_ids": [
        {"type": "wikidata", "all": ["Q12345"], "preferred": "Q12345"},
    ],
    "relationships": [],
    "domains": ["test.edu"],
    "admin": {"created": {"date": "2026-01-01"}},
}


class TestFlattenJson:
    def test_flattens_simple(self):
        result = flatten_json({"a": 1, "b": "two"})
        assert result == {"a": 1, "b": "two"}

    def test_flattens_nested_dict(self):
        result = flatten_json({"a": {"b": "value"}})
        assert result["a_b"] == "value"

    def test_flattens_list(self):
        result = flatten_json({"items": ["x", "y"]})
        assert result["items_0"] == "x"
        assert result["items_1"] == "y"

    def test_flattens_record(self):
        result = flatten_json(SAMPLE_RECORD)
        assert result["status"] == "active"
        assert result["names_0_value"] == "Test University"
        assert result["locations_0_geonames_id"] == 5367440


class TestSimplifyJson:
    def test_extracts_status(self):
        result = simplify_json(SAMPLE_RECORD)
        assert "active" in result["status"]

    def test_extracts_types(self):
        result = simplify_json(SAMPLE_RECORD)
        assert "education" in result["types"]

    def test_extracts_names_by_type(self):
        result = simplify_json(SAMPLE_RECORD)
        assert "Test University" in result["names.types.ror_display"]
        assert "TU" in result["names.types.acronym"]

    def test_extracts_links(self):
        result = simplify_json(SAMPLE_RECORD)
        assert "https://test.edu" in result["links.type.website"]

    def test_extracts_external_ids(self):
        result = simplify_json(SAMPLE_RECORD)
        assert "Q12345" in result["external_ids.type.wikidata.all"]
        assert "Q12345" in result["external_ids.type.wikidata.preferred"]

    def test_extracts_geonames_id(self):
        result = simplify_json(SAMPLE_RECORD)
        assert 5367440 in result["locations.geonames_id"]

    def test_extracts_established(self):
        result = simplify_json(SAMPLE_RECORD)
        assert 1990 in result["established"]

    def test_all_contains_all_values(self):
        result = simplify_json(SAMPLE_RECORD)
        assert "active" in result["all"]
        assert "Test University" in result["all"]
        assert "Q12345" in result["all"]

    def test_all_excludes_falsy(self):
        record = {**SAMPLE_RECORD, "external_ids": []}
        result = simplify_json(record)
        assert [] not in result["all"]


class TestSimplifyAndInvertJson:
    def test_returns_simplified_and_inverted(self):
        simplified, inverted = simplify_and_invert_json(SAMPLE_RECORD)
        assert "active" in simplified["status"]
        assert "status" in inverted["active"]

    def test_inverted_maps_value_to_fields(self):
        _, inverted = simplify_and_invert_json(SAMPLE_RECORD)
        assert "external_ids.type.wikidata.preferred" in inverted["Q12345"]
        assert "external_ids.type.wikidata.all" in inverted["Q12345"]
