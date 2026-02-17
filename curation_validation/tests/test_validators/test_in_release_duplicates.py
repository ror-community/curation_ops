import csv
import json
from pathlib import Path

import pytest

from curation_validation.validators.base import ValidatorContext
from curation_validation.validators.in_release_duplicates import (
    InReleaseDuplicatesValidator,
    parse_csv_record,
    parse_json_record,
    check_url_matches,
    check_name_matches,
    clean_name,
    find_duplicates,
    FUZZY_THRESHOLD,
)


def _make_json_ctx(tmp_path, records):
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
        geonames_user=None,
    )


def _make_csv_ctx(tmp_path, rows):
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
        geonames_user=None,
    )


def _json_record(display_name, website_url, aliases=None, labels=None):
    names = [{"value": display_name, "types": ["ror_display"]}]
    if aliases:
        for alias in aliases:
            names.append({"value": alias, "types": ["alias"]})
    if labels:
        for label in labels:
            names.append({"value": label, "types": ["label"]})
    links = []
    if website_url:
        links.append({"type": "website", "value": website_url})
    return {
        "id": "",
        "names": names,
        "links": links,
    }


def _csv_row(display_name, website_url, aliases="", labels=""):
    return {
        "names.types.ror_display": display_name,
        "links.type.website": website_url,
        "names.types.alias": aliases,
        "names.types.label": labels,
    }


class TestConstants:
    def test_fuzzy_threshold_is_85(self):
        assert FUZZY_THRESHOLD == 85


class TestInReleaseDuplicatesValidatorMetadata:
    def test_name(self):
        v = InReleaseDuplicatesValidator()
        assert v.name == "in-release-duplicates"

    def test_supported_formats(self):
        v = InReleaseDuplicatesValidator()
        assert v.supported_formats == {"csv", "json"}

    def test_does_not_require_data_source(self):
        v = InReleaseDuplicatesValidator()
        assert v.requires_data_source is False

    def test_output_filename(self):
        v = InReleaseDuplicatesValidator()
        assert v.output_filename == "in_release_duplicates.csv"

    def test_output_fields(self):
        v = InReleaseDuplicatesValidator()
        expected = [
            "record1_issue_url",
            "record2_issue_url",
            "record1_display_name",
            "record1_url",
            "record2_display_name",
            "record2_url",
            "match_type",
            "similarity_score",
        ]
        assert v.output_fields == expected

    def test_can_run_always(self, tmp_path):
        v = InReleaseDuplicatesValidator()
        ctx = ValidatorContext(
            csv_file=None,
            json_dir=None,
            output_dir=tmp_path,
            data_source=None,
            geonames_user=None,
        )
        can, _ = v.can_run(ctx)
        assert can is True


class TestCleanName:
    def test_strips_language_marker(self):
        assert clean_name("University of Tokyo*ja") == "University of Tokyo"

    def test_no_marker(self):
        assert clean_name("University of Tokyo") == "University of Tokyo"

    def test_strips_whitespace_around_marker(self):
        assert clean_name("Name *lang") == "Name"

    def test_empty_string(self):
        assert clean_name("") == ""


class TestParseCsvRecord:
    def test_basic_parsing(self):
        row = {
            "names.types.ror_display": "Main University",
            "links.type.website": "https://main.edu",
            "names.types.alias": "",
            "names.types.label": "",
        }
        result = parse_csv_record(row, 0)
        assert result["index"] == 0
        assert result["display_name"] == "Main University"
        assert "Main University" in result["names"]
        assert result["url"] == "https://main.edu"
        assert "https://main.edu" in result["urls"]

    def test_parses_semicolon_aliases(self):
        row = {
            "names.types.ror_display": "Main",
            "links.type.website": "",
            "names.types.alias": "Alias One; Alias Two",
            "names.types.label": "",
        }
        result = parse_csv_record(row, 0)
        assert "Alias One" in result["names"]
        assert "Alias Two" in result["names"]

    def test_parses_semicolon_labels(self):
        row = {
            "names.types.ror_display": "Main",
            "links.type.website": "",
            "names.types.alias": "",
            "names.types.label": "Label A; Label B*fr",
        }
        result = parse_csv_record(row, 0)
        assert "Label A" in result["names"]
        assert "Label B*fr" in result["names"]

    def test_empty_website_produces_empty_urls(self):
        row = {
            "names.types.ror_display": "Main",
            "links.type.website": "",
            "names.types.alias": "",
            "names.types.label": "",
        }
        result = parse_csv_record(row, 0)
        assert result["urls"] == []

    def test_missing_columns(self):
        row = {}
        result = parse_csv_record(row, 0)
        assert result["display_name"] == ""
        assert result["names"] == []
        assert result["urls"] == []


class TestParseJsonRecord:
    def test_basic_parsing(self):
        record = _json_record("Main University", "https://main.edu")
        result = parse_json_record(record, 0)
        assert result["index"] == 0
        assert result["display_name"] == "Main University"
        assert "Main University" in result["names"]
        assert result["url"] == "https://main.edu"
        assert "https://main.edu" in result["urls"]

    def test_extracts_aliases(self):
        record = _json_record("Main", "https://main.edu", aliases=["Alias1", "Alias2"])
        result = parse_json_record(record, 0)
        assert "Alias1" in result["names"]
        assert "Alias2" in result["names"]

    def test_extracts_labels(self):
        record = _json_record("Main", "https://main.edu", labels=["French Label"])
        result = parse_json_record(record, 0)
        assert "French Label" in result["names"]

    def test_no_website_link(self):
        record = {
            "names": [{"value": "Org", "types": ["ror_display"]}],
            "links": [{"type": "wikipedia", "value": "https://en.wikipedia.org/wiki/Org"}],
        }
        result = parse_json_record(record, 0)
        assert result["url"] == ""
        assert result["urls"] == []

    def test_no_ror_display_name(self):
        record = {
            "names": [{"value": "Just Alias", "types": ["alias"]}],
            "links": [],
        }
        result = parse_json_record(record, 0)
        assert result["display_name"] == ""

    def test_missing_keys(self):
        record = {}
        result = parse_json_record(record, 0)
        assert result["display_name"] == ""
        assert result["names"] == []
        assert result["urls"] == []

    def test_ignores_acronym_type(self):
        record = {
            "names": [
                {"value": "Main Org", "types": ["ror_display"]},
                {"value": "MO", "types": ["acronym"]},
            ],
            "links": [],
        }
        result = parse_json_record(record, 0)
        assert "Main Org" in result["names"]
        assert "MO" not in result["names"]


class TestCheckUrlMatches:
    def test_exact_match(self):
        matched, url1, url2 = check_url_matches(
            ["https://example.com"], ["https://example.com"]
        )
        assert matched is True
        assert url1 == "https://example.com"
        assert url2 == "https://example.com"

    def test_normalized_match_www(self):
        matched, url1, url2 = check_url_matches(
            ["https://www.example.com"], ["https://example.com"]
        )
        assert matched is True

    def test_normalized_match_scheme(self):
        matched, url1, url2 = check_url_matches(
            ["http://example.com"], ["https://example.com"]
        )
        assert matched is True

    def test_no_match(self):
        matched, url1, url2 = check_url_matches(
            ["https://alpha.com"], ["https://beta.com"]
        )
        assert matched is False
        assert url1 is None
        assert url2 is None

    def test_empty_urls(self):
        matched, _, _ = check_url_matches([], [])
        assert matched is False

    def test_skips_empty_strings(self):
        matched, _, _ = check_url_matches([""], ["https://example.com"])
        assert matched is False

    def test_skips_invalid_urls(self):
        matched, _, _ = check_url_matches(["not-a-url"], ["https://example.com"])
        assert matched is False


class TestCheckNameMatches:
    def test_exact_match(self):
        matches = check_name_matches(["University of Oxford"], ["University of Oxford"])
        assert len(matches) == 1
        assert matches[0][2] == 100

    def test_fuzzy_match_above_threshold(self):
        matches = check_name_matches(
            ["University of California"],
            ["Universty of California"],
        )
        assert len(matches) >= 1
        assert matches[0][2] >= FUZZY_THRESHOLD

    def test_fuzzy_match_below_threshold(self):
        matches = check_name_matches(
            ["University of Oxford"],
            ["Tokyo Institute of Technology"],
        )
        assert len(matches) == 0

    def test_name_with_language_marker(self):
        matches = check_name_matches(
            ["University of Tokyo*ja"],
            ["University of Tokyo"],
        )
        assert len(matches) >= 1
        assert matches[0][2] == 100

    def test_empty_names(self):
        matches = check_name_matches([], ["University"])
        assert matches == []

    def test_empty_cleaned_name(self):
        matches = check_name_matches(["*ja"], ["University"])
        assert matches == []

    def test_multiple_matches(self):
        matches = check_name_matches(
            ["University of Oxford", "Oxford Uni"],
            ["University of Oxford"],
        )
        exact = [m for m in matches if m[2] == 100]
        assert len(exact) == 1


class TestFindDuplicates:
    def test_url_match_csv_records(self):
        parsed = [
            {
                "index": 0,
                "display_name": "Org A",
                "names": ["Org A"],
                "url": "https://example.com",
                "urls": ["https://example.com"],
            },
            {
                "index": 1,
                "display_name": "Org B",
                "names": ["Org B"],
                "url": "https://example.com",
                "urls": ["https://example.com"],
            },
        ]
        findings = find_duplicates(parsed)
        url_findings = [f for f in findings if f["match_type"] == "url"]
        assert len(url_findings) == 1
        assert url_findings[0]["record1_display_name"] == "Org A"
        assert url_findings[0]["record2_display_name"] == "Org B"
        assert url_findings[0]["similarity_score"] == 100

    def test_exact_name_match(self):
        parsed = [
            {
                "index": 0,
                "display_name": "University of Oxford",
                "names": ["University of Oxford"],
                "url": "https://oxford.ac.uk",
                "urls": ["https://oxford.ac.uk"],
            },
            {
                "index": 1,
                "display_name": "University of Oxford",
                "names": ["University of Oxford"],
                "url": "https://different.com",
                "urls": ["https://different.com"],
            },
        ]
        findings = find_duplicates(parsed)
        name_findings = [f for f in findings if f["match_type"] == "name_exact"]
        assert len(name_findings) == 1
        assert name_findings[0]["similarity_score"] == 100

    def test_fuzzy_name_match(self):
        parsed = [
            {
                "index": 0,
                "display_name": "University of California",
                "names": ["University of California"],
                "url": "",
                "urls": [],
            },
            {
                "index": 1,
                "display_name": "Universty of California",
                "names": ["Universty of California"],
                "url": "",
                "urls": [],
            },
        ]
        findings = find_duplicates(parsed)
        fuzzy = [f for f in findings if f["match_type"] == "name_fuzzy"]
        assert len(fuzzy) >= 1
        assert FUZZY_THRESHOLD <= fuzzy[0]["similarity_score"] < 100

    def test_no_duplicates(self):
        parsed = [
            {
                "index": 0,
                "display_name": "University of Oxford",
                "names": ["University of Oxford"],
                "url": "https://oxford.ac.uk",
                "urls": ["https://oxford.ac.uk"],
            },
            {
                "index": 1,
                "display_name": "Tokyo Institute of Technology",
                "names": ["Tokyo Institute of Technology"],
                "url": "https://titech.ac.jp",
                "urls": ["https://titech.ac.jp"],
            },
        ]
        findings = find_duplicates(parsed)
        assert findings == []

    def test_deduplication_of_name_pairs(self):
        parsed = [
            {
                "index": 0,
                "display_name": "Org A",
                "names": ["Org A", "Org A Alias"],
                "url": "",
                "urls": [],
            },
            {
                "index": 1,
                "display_name": "Org B",
                "names": ["Org A", "Org A Alias"],
                "url": "",
                "urls": [],
            },
        ]
        findings = find_duplicates(parsed)
        name_findings = [f for f in findings if "name" in f["match_type"]]
        name_pairs = [(f["match_type"], f["similarity_score"]) for f in name_findings]
        exact_count = sum(1 for mt, _ in name_pairs if mt == "name_exact")
        assert exact_count == 2

    def test_single_record_no_findings(self):
        parsed = [
            {
                "index": 0,
                "display_name": "Only Org",
                "names": ["Only Org"],
                "url": "https://only.com",
                "urls": ["https://only.com"],
            },
        ]
        findings = find_duplicates(parsed)
        assert findings == []

    def test_empty_records(self):
        findings = find_duplicates([])
        assert findings == []

    def test_output_fields_present(self):
        parsed = [
            {
                "index": 0,
                "display_name": "Org A",
                "names": ["Org A"],
                "url": "https://example.com",
                "urls": ["https://example.com"],
            },
            {
                "index": 1,
                "display_name": "Org B",
                "names": ["Org B"],
                "url": "https://example.com",
                "urls": ["https://example.com"],
            },
        ]
        findings = find_duplicates(parsed)
        assert len(findings) >= 1
        for finding in findings:
            assert "record1_display_name" in finding
            assert "record1_url" in finding
            assert "record2_display_name" in finding
            assert "record2_url" in finding
            assert "match_type" in finding
            assert "similarity_score" in finding


class TestInReleaseDuplicatesJSON:
    def test_url_match_json(self, tmp_path):
        records = [
            _json_record("Org A", "https://example.com"),
            _json_record("Org B", "https://example.com"),
        ]
        ctx = _make_json_ctx(tmp_path, records)
        v = InReleaseDuplicatesValidator()
        results = v.run(ctx)
        url_results = [r for r in results if r["match_type"] == "url"]
        assert len(url_results) == 1

    def test_exact_name_match_json(self, tmp_path):
        records = [
            _json_record("University of Oxford", "https://oxford.ac.uk"),
            _json_record("University of Oxford", "https://different.com"),
        ]
        ctx = _make_json_ctx(tmp_path, records)
        v = InReleaseDuplicatesValidator()
        results = v.run(ctx)
        exact = [r for r in results if r["match_type"] == "name_exact"]
        assert len(exact) == 1

    def test_fuzzy_name_match_json(self, tmp_path):
        records = [
            _json_record("University of California", "https://uc.edu"),
            _json_record("Universty of California", "https://ucal.edu"),
        ]
        ctx = _make_json_ctx(tmp_path, records)
        v = InReleaseDuplicatesValidator()
        results = v.run(ctx)
        fuzzy = [r for r in results if r["match_type"] == "name_fuzzy"]
        assert len(fuzzy) >= 1
        assert FUZZY_THRESHOLD <= fuzzy[0]["similarity_score"] < 100

    def test_no_match_json(self, tmp_path):
        records = [
            _json_record("University of Oxford", "https://oxford.ac.uk"),
            _json_record("Tokyo Institute of Technology", "https://titech.ac.jp"),
        ]
        ctx = _make_json_ctx(tmp_path, records)
        v = InReleaseDuplicatesValidator()
        results = v.run(ctx)
        assert results == []

    def test_alias_match_json(self, tmp_path):
        records = [
            _json_record("Org A", "https://a.com", aliases=["Shared Alias Name"]),
            _json_record("Org B", "https://b.com", aliases=["Shared Alias Name"]),
        ]
        ctx = _make_json_ctx(tmp_path, records)
        v = InReleaseDuplicatesValidator()
        results = v.run(ctx)
        name_results = [r for r in results if "name" in r["match_type"]]
        assert len(name_results) >= 1

    def test_label_match_json(self, tmp_path):
        records = [
            _json_record("Org A", "https://a.com", labels=["Common Label"]),
            _json_record("Org B", "https://b.com", labels=["Common Label"]),
        ]
        ctx = _make_json_ctx(tmp_path, records)
        v = InReleaseDuplicatesValidator()
        results = v.run(ctx)
        name_results = [r for r in results if "name" in r["match_type"]]
        assert len(name_results) >= 1

    def test_empty_json_dir(self, tmp_path):
        json_dir = tmp_path / "json"
        json_dir.mkdir(parents=True, exist_ok=True)
        ctx = ValidatorContext(
            csv_file=None,
            json_dir=json_dir,
            output_dir=tmp_path / "output",
            data_source=None,
            geonames_user=None,
        )
        v = InReleaseDuplicatesValidator()
        results = v.run(ctx)
        assert results == []

    def test_normalized_url_match_json(self, tmp_path):
        records = [
            _json_record("Org A", "https://www.example.com"),
            _json_record("Org B", "http://example.com"),
        ]
        ctx = _make_json_ctx(tmp_path, records)
        v = InReleaseDuplicatesValidator()
        results = v.run(ctx)
        url_results = [r for r in results if r["match_type"] == "url"]
        assert len(url_results) == 1


class TestInReleaseDuplicatesCSV:
    def test_url_match_csv(self, tmp_path):
        rows = [
            _csv_row("Org A", "https://example.com"),
            _csv_row("Org B", "https://example.com"),
        ]
        ctx = _make_csv_ctx(tmp_path, rows)
        v = InReleaseDuplicatesValidator()
        results = v.run(ctx)
        url_results = [r for r in results if r["match_type"] == "url"]
        assert len(url_results) == 1

    def test_exact_name_match_csv(self, tmp_path):
        rows = [
            _csv_row("University of Oxford", "https://oxford.ac.uk"),
            _csv_row("University of Oxford", "https://different.com"),
        ]
        ctx = _make_csv_ctx(tmp_path, rows)
        v = InReleaseDuplicatesValidator()
        results = v.run(ctx)
        exact = [r for r in results if r["match_type"] == "name_exact"]
        assert len(exact) == 1

    def test_fuzzy_name_match_csv(self, tmp_path):
        rows = [
            _csv_row("University of California", "https://uc.edu"),
            _csv_row("Universty of California", "https://ucal.edu"),
        ]
        ctx = _make_csv_ctx(tmp_path, rows)
        v = InReleaseDuplicatesValidator()
        results = v.run(ctx)
        fuzzy = [r for r in results if r["match_type"] == "name_fuzzy"]
        assert len(fuzzy) >= 1

    def test_no_match_csv(self, tmp_path):
        rows = [
            _csv_row("University of Oxford", "https://oxford.ac.uk"),
            _csv_row("Tokyo Institute of Technology", "https://titech.ac.jp"),
        ]
        ctx = _make_csv_ctx(tmp_path, rows)
        v = InReleaseDuplicatesValidator()
        results = v.run(ctx)
        assert results == []

    def test_below_threshold_csv(self, tmp_path):
        rows = [
            _csv_row("University of Oxford", "https://oxford.ac.uk"),
            _csv_row("Centre National de la Recherche", "https://cnrs.fr"),
        ]
        ctx = _make_csv_ctx(tmp_path, rows)
        v = InReleaseDuplicatesValidator()
        results = v.run(ctx)
        assert results == []

    def test_alias_match_csv(self, tmp_path):
        rows = [
            _csv_row("Org A", "https://a.com", aliases="Shared Alias"),
            _csv_row("Org B", "https://b.com", aliases="Shared Alias"),
        ]
        ctx = _make_csv_ctx(tmp_path, rows)
        v = InReleaseDuplicatesValidator()
        results = v.run(ctx)
        name_results = [r for r in results if "name" in r["match_type"]]
        assert len(name_results) >= 1

    def test_label_with_lang_marker_csv(self, tmp_path):
        rows = [
            _csv_row("Org A", "https://a.com", labels="Common Label*fr"),
            _csv_row("Org B", "https://b.com", labels="Common Label*de"),
        ]
        ctx = _make_csv_ctx(tmp_path, rows)
        v = InReleaseDuplicatesValidator()
        results = v.run(ctx)
        name_results = [r for r in results if "name" in r["match_type"]]
        assert len(name_results) >= 1

    def test_multiple_semicolon_aliases_csv(self, tmp_path):
        rows = [
            _csv_row("Org A", "https://a.com", aliases="Alpha; Beta; Gamma"),
            _csv_row("Org B", "https://b.com", aliases="Delta; Beta; Epsilon"),
        ]
        ctx = _make_csv_ctx(tmp_path, rows)
        v = InReleaseDuplicatesValidator()
        results = v.run(ctx)
        name_results = [r for r in results if "name" in r["match_type"]]
        assert len(name_results) >= 1

    def test_normalized_url_match_csv(self, tmp_path):
        rows = [
            _csv_row("Org A", "https://www.example.com"),
            _csv_row("Org B", "http://example.com"),
        ]
        ctx = _make_csv_ctx(tmp_path, rows)
        v = InReleaseDuplicatesValidator()
        results = v.run(ctx)
        url_results = [r for r in results if r["match_type"] == "url"]
        assert len(url_results) == 1

    def test_csv_output_fields(self, tmp_path):
        rows = [
            _csv_row("Org A", "https://example.com"),
            _csv_row("Org B", "https://example.com"),
        ]
        ctx = _make_csv_ctx(tmp_path, rows)
        v = InReleaseDuplicatesValidator()
        results = v.run(ctx)
        assert len(results) >= 1
        for result in results:
            assert "record1_display_name" in result
            assert "record1_url" in result
            assert "record2_display_name" in result
            assert "record2_url" in result
            assert "match_type" in result
            assert "similarity_score" in result


class TestInReleaseDuplicatesEdgeCases:
    def test_returns_empty_when_no_input(self, tmp_path):
        ctx = ValidatorContext(
            csv_file=None,
            json_dir=None,
            output_dir=tmp_path,
            data_source=None,
            geonames_user=None,
        )
        v = InReleaseDuplicatesValidator()
        results = v.run(ctx)
        assert results == []

    def test_prefers_json_over_csv(self, tmp_path):
        json_dir = tmp_path / "json"
        json_dir.mkdir(parents=True, exist_ok=True)
        rec1 = _json_record("JSON Org A", "https://example.com")
        rec2 = _json_record("JSON Org B", "https://example.com")
        (json_dir / "rec1.json").write_text(json.dumps(rec1), encoding="utf-8")
        (json_dir / "rec2.json").write_text(json.dumps(rec2), encoding="utf-8")

        csv_file = tmp_path / "input.csv"
        fieldnames = [
            "names.types.ror_display",
            "links.type.website",
            "names.types.alias",
            "names.types.label",
        ]
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(_csv_row("CSV Org A", "https://example.com"))
            writer.writerow(_csv_row("CSV Org B", "https://example.com"))

        ctx = ValidatorContext(
            csv_file=csv_file,
            json_dir=json_dir,
            output_dir=tmp_path / "output",
            data_source=None,
            geonames_user=None,
        )
        v = InReleaseDuplicatesValidator()
        results = v.run(ctx)
        url_results = [r for r in results if r["match_type"] == "url"]
        assert len(url_results) >= 1
        assert "JSON" in url_results[0]["record1_display_name"]

    def test_three_records_pairwise(self, tmp_path):
        records = [
            _json_record("Org A", "https://example.com"),
            _json_record("Org B", "https://example.com"),
            _json_record("Org C", "https://example.com"),
        ]
        ctx = _make_json_ctx(tmp_path, records)
        v = InReleaseDuplicatesValidator()
        results = v.run(ctx)
        url_results = [r for r in results if r["match_type"] == "url"]
        assert len(url_results) == 3
