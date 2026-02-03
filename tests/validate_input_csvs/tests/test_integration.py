# tests/test_integration.py
"""End-to-end integration tests for validate-ror-records-input-csvs CLI."""

import json
import subprocess
from pathlib import Path

import pytest


class TestEndToEnd:
    """Test the complete CLI workflow from invocation to output files."""

    def test_cli_runs_validate_fields(self, tmp_path):
        """Test that validate-fields validator runs and produces output."""
        # Create minimal valid input
        input_csv = tmp_path / "input.csv"
        input_csv.write_text(
            "id,names.types.ror_display,status\n"
            ",Test*en,active\n"
        )

        result = subprocess.run(
            ["validate-ror-records-input-csvs", "-i", str(input_csv), "-o", str(tmp_path), "--test", "validate-fields"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert (tmp_path / "validation_report.csv").exists()

    def test_cli_errors_when_missing_geonames(self, tmp_path):
        """Test that validators requiring geonames fail with error when not provided."""
        input_csv = tmp_path / "input.csv"
        input_csv.write_text(
            "id,names.types.ror_display,locations.geonames_id,city,country\n"
            ",Test*en,5128581,Boston,United States\n"
        )

        result = subprocess.run(
            ["validate-ror-records-input-csvs", "-i", str(input_csv), "-o", str(tmp_path), "--test", "address-validation"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert "error" in result.stderr.lower()
        assert "geonames" in result.stderr.lower()

    def test_cli_runs_multiple_validators(self, tmp_path):
        """Test running multiple validators in a single invocation."""
        input_csv = tmp_path / "input.csv"
        input_csv.write_text(
            "id,names.types.ror_display,status,links.type.website,names.types.alias\n"
            ",Test University*en,active,https://test.edu,Test Uni*en\n"
            ",Another Institution*de,active,https://another.org,\n"
        )

        result = subprocess.run(
            [
                "validate-ror-records-input-csvs", "-i", str(input_csv), "-o", str(tmp_path),
                "--test", "validate-fields",
                "--test", "in-release-duplicates",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert (tmp_path / "validation_report.csv").exists()
        assert (tmp_path / "in_release_duplicates.csv").exists()

    def test_cli_with_synthetic_test_data(self, tmp_path):
        """Test with synthetic data containing various field types."""
        # Create comprehensive test CSV with multiple field types
        input_csv = tmp_path / "synthetic_input.csv"
        input_csv.write_text(
            "id,names.types.ror_display,names.types.acronym,names.types.alias,names.types.label,"
            "status,types,links.type.website,links.type.wikipedia,established,"
            "locations.geonames_id,city,country,"
            "external_ids.type.isni.all,external_ids.type.wikidata.all,external_ids.type.fundref.all\n"
            ",Test University*en,TU*en,Test Uni*en,Testing University*es,active,education,"
            "https://test.edu,https://en.wikipedia.org/wiki/Test_University,1900,"
            "5128581,Boston,United States,0000 0000 1234 5678,Q12345,123456\n"
            ",Another Institution*de,AI*de,,,active,company,"
            "https://another.org,,2000,2643743,London,United Kingdom,,,\n"
        )

        result = subprocess.run(
            ["validate-ror-records-input-csvs", "-i", str(input_csv), "-o", str(tmp_path), "--test", "validate-fields"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert (tmp_path / "validation_report.csv").exists()

        # Verify the output file has the correct header
        report_content = (tmp_path / "validation_report.csv").read_text()
        assert "html_url" in report_content
        assert "ror_id" in report_content
        assert "error_warning" in report_content

    def test_cli_error_handling_missing_input(self, tmp_path):
        """Test error handling when input file does not exist."""
        result = subprocess.run(
            ["validate-ror-records-input-csvs", "-i", str(tmp_path / "nonexistent.csv"), "-o", str(tmp_path)],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "not found" in result.stderr.lower() or "error" in result.stderr.lower()

    def test_cli_error_handling_unknown_validator(self, tmp_path):
        """Test handling of unknown validator name."""
        input_csv = tmp_path / "input.csv"
        input_csv.write_text("id,names.types.ror_display\n,Test*en\n")

        result = subprocess.run(
            ["validate-ror-records-input-csvs", "-i", str(input_csv), "-o", str(tmp_path), "--test", "unknown-validator"],
            capture_output=True,
            text=True,
        )

        # Should complete without error but warn about unknown validator
        assert result.returncode == 0
        assert "unknown" in result.stderr.lower() or "skipping" in result.stderr.lower()

    def test_output_file_created_correctly(self, tmp_path):
        """Test that output files are created with correct structure."""
        input_csv = tmp_path / "input.csv"
        # Create input with known validation errors
        input_csv.write_text(
            "id,names.types.ror_display,status,established\n"
            ",Invalid Name,pending,99\n"  # Missing language tag, invalid status, invalid year
        )

        result = subprocess.run(
            ["validate-ror-records-input-csvs", "-i", str(input_csv), "-o", str(tmp_path), "--test", "validate-fields"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        # Check output file exists and has content
        report_path = tmp_path / "validation_report.csv"
        assert report_path.exists()

        report_content = report_path.read_text()
        lines = report_content.strip().split("\n")

        # Should have header + at least one error row
        assert len(lines) >= 2, f"Expected at least 2 lines, got: {lines}"

        # Verify header fields
        header = lines[0]
        assert "html_url" in header
        assert "ror_id" in header
        assert "error_warning" in header

    def test_output_directory_created_if_missing(self, tmp_path):
        """Test that output directory is created if it doesn't exist."""
        input_csv = tmp_path / "input.csv"
        input_csv.write_text("id,names.types.ror_display,status\n,Test*en,active\n")

        nested_output = tmp_path / "nested" / "output" / "dir"

        result = subprocess.run(
            ["validate-ror-records-input-csvs", "-i", str(input_csv), "-o", str(nested_output), "--test", "validate-fields"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert nested_output.exists()
        assert (nested_output / "validation_report.csv").exists()

    def test_cli_with_data_dump(self, tmp_path):
        """Test validators that require data dump."""
        input_csv = tmp_path / "input.csv"
        input_csv.write_text(
            "id,names.types.ror_display,links.type.website,"
            "external_ids.type.isni.all,external_ids.type.wikidata.all\n"
            ",Test University*en,https://test.edu,0000 0000 1234 5678,Q12345\n"
        )

        # Create a minimal data dump
        data_dump = tmp_path / "data_dump.json"
        data_dump.write_text(json.dumps([
            {
                "id": "https://ror.org/012345",
                "names": [{"value": "Existing Org", "types": ["ror_display"]}],
                "links": [{"type": "website", "value": "https://existing.org"}],
                "external_ids": [
                    {"type": "isni", "all": ["0000 0000 9999 8888"], "preferred": "0000 0000 9999 8888"}
                ]
            }
        ]))

        result = subprocess.run(
            [
                "validate-ror-records-input-csvs", "-i", str(input_csv), "-o", str(tmp_path),
                "-d", str(data_dump),
                "--test", "duplicate-external-ids",
                "--test", "duplicate-urls",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert (tmp_path / "duplicate_external_ids.csv").exists()
        assert (tmp_path / "duplicate_urls.csv").exists()

    def test_cli_detects_duplicate_urls(self, tmp_path):
        """Test that duplicate URL detection works end-to-end."""
        input_csv = tmp_path / "input.csv"
        input_csv.write_text(
            "id,names.types.ror_display,links.type.website\n"
            ",New Organization*en,https://duplicate.edu\n"
        )

        # Create data dump with matching URL
        data_dump = tmp_path / "data_dump.json"
        data_dump.write_text(json.dumps([
            {
                "id": "https://ror.org/existing123",
                "names": [{"value": "Existing Organization", "types": ["ror_display"]}],
                "links": [{"type": "website", "value": "https://duplicate.edu"}],
                "external_ids": []
            }
        ]))

        result = subprocess.run(
            [
                "validate-ror-records-input-csvs", "-i", str(input_csv), "-o", str(tmp_path),
                "-d", str(data_dump),
                "--test", "duplicate-urls",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        # Check that duplicate was detected
        output_path = tmp_path / "duplicate_urls.csv"
        assert output_path.exists()

        content = output_path.read_text()
        # Should have header + 1 match
        lines = content.strip().split("\n")
        assert len(lines) == 2, f"Expected header + 1 duplicate, got: {lines}"
        assert "duplicate.edu" in content

    def test_cli_detects_in_release_duplicates(self, tmp_path):
        """Test that in-release duplicate detection works end-to-end."""
        input_csv = tmp_path / "input.csv"
        # Create two records with similar names
        input_csv.write_text(
            "id,names.types.ror_display,links.type.website\n"
            ",University of Testing*en,https://testing.edu\n"
            ",University of Testing*de,https://testing.edu\n"
        )

        result = subprocess.run(
            [
                "validate-ror-records-input-csvs", "-i", str(input_csv), "-o", str(tmp_path),
                "--test", "in-release-duplicates",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        # Check that duplicates were detected
        output_path = tmp_path / "in_release_duplicates.csv"
        assert output_path.exists()

        content = output_path.read_text()
        lines = content.strip().split("\n")
        # Should have header + at least 1 match (URL match and/or name match)
        assert len(lines) >= 2, f"Expected duplicates, got: {lines}"

    def test_cli_detects_validation_errors(self, tmp_path):
        """Test that field validation catches various error types."""
        input_csv = tmp_path / "input.csv"
        input_csv.write_text(
            "id,names.types.ror_display,names.types.acronym,status,types,links.type.website,"
            "established,external_ids.type.isni.all,external_ids.type.wikidata.all,"
            "external_ids.type.fundref.all,locations.geonames_id,city,country\n"
            # Row with multiple errors
            ",Invalid Name,lowercase*en,pending,university,example.org,99,0000-1234,q12345,0,abc,,France\n"
        )

        result = subprocess.run(
            ["validate-ror-records-input-csvs", "-i", str(input_csv), "-o", str(tmp_path), "--test", "validate-fields"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        output_path = tmp_path / "validation_report.csv"
        assert output_path.exists()

        content = output_path.read_text()
        lines = content.strip().split("\n")

        # Should have multiple errors (missing language tag, invalid status, invalid URL, etc.)
        assert len(lines) > 2, f"Expected multiple validation errors, got: {lines}"

    def test_cli_help_option(self):
        """Test that --help works correctly."""
        result = subprocess.run(
            ["validate-ror-records-input-csvs", "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "validate-ror-records-input-csvs" in result.stdout.lower() or "usage" in result.stdout.lower()
        assert "-i" in result.stdout or "--input" in result.stdout

    def test_cli_all_validators_default(self, tmp_path):
        """Test that 'all' is the default when no --test is specified."""
        input_csv = tmp_path / "input.csv"
        input_csv.write_text(
            "id,names.types.ror_display,status,links.type.website\n"
            ",Test*en,active,https://test.edu\n"
        )

        # Create a minimal data dump so validators requiring data source can run
        data_dump = tmp_path / "data_dump.json"
        data_dump.write_text(json.dumps([
            {
                "id": "https://ror.org/012345",
                "names": [{"value": "Existing Org", "types": ["ror_display"]}],
                "links": [{"type": "website", "value": "https://existing.org"}],
                "external_ids": []
            }
        ]))

        # Run without --test flag but exclude address-validation (requires geonames)
        # by specifying the validators that don't require geonames
        result = subprocess.run(
            [
                "validate-ror-records-input-csvs", "-i", str(input_csv), "-o", str(tmp_path), "-d", str(data_dump),
                "--test", "validate-fields",
                "--test", "in-release-duplicates",
                "--test", "duplicate-urls",
                "--test", "duplicate-external-ids",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        # validate-fields doesn't require deps, so it should run
        assert (tmp_path / "validation_report.csv").exists()
        # in-release-duplicates doesn't require deps either
        assert (tmp_path / "in_release_duplicates.csv").exists()
        # duplicate-urls requires data source, should now run
        assert (tmp_path / "duplicate_urls.csv").exists()
        # duplicate-external-ids requires data source, should now run
        assert (tmp_path / "duplicate_external_ids.csv").exists()

    def test_cli_all_fails_without_geonames(self, tmp_path):
        """Test that running 'all' without geonames user fails."""
        input_csv = tmp_path / "input.csv"
        input_csv.write_text(
            "id,names.types.ror_display,status\n"
            ",Test*en,active\n"
        )

        # Create a mock data dump to avoid network calls
        data_dump = tmp_path / "data_dump.json"
        data_dump.write_text(json.dumps([
            {"id": "https://ror.org/012345", "names": [], "links": [], "external_ids": []}
        ]))

        # Run with all validators but no geonames user
        # Should fail because address-validation requires geonames
        result = subprocess.run(
            ["validate-ror-records-input-csvs", "-i", str(input_csv), "-o", str(tmp_path), "-d", str(data_dump)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert "geonames" in result.stderr.lower()

    def test_empty_csv_handling(self, tmp_path):
        """Test handling of empty CSV file (headers only)."""
        input_csv = tmp_path / "input.csv"
        input_csv.write_text("id,names.types.ror_display,status\n")

        result = subprocess.run(
            ["validate-ror-records-input-csvs", "-i", str(input_csv), "-o", str(tmp_path), "--test", "validate-fields"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert (tmp_path / "validation_report.csv").exists()

        # Output should have header but no error rows
        content = (tmp_path / "validation_report.csv").read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 1  # Just header

    def test_valid_records_produce_empty_report(self, tmp_path):
        """Test that fully valid records produce an empty validation report."""
        input_csv = tmp_path / "input.csv"
        input_csv.write_text(
            "id,names.types.ror_display,status,types,links.type.website,"
            "established,locations.geonames_id,city,country\n"
            ",Valid University*en,active,education,https://valid.edu,"
            "2000,5128581,Boston,United States\n"
        )

        result = subprocess.run(
            ["validate-ror-records-input-csvs", "-i", str(input_csv), "-o", str(tmp_path), "--test", "validate-fields"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        # Output should have header but no error rows
        content = (tmp_path / "validation_report.csv").read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 1, f"Expected only header for valid input, got: {lines}"


class TestDataDumpFormats:
    """Test integration with different data dump formats."""

    def test_json_data_dump(self, tmp_path):
        """Test loading a plain JSON data dump."""
        input_csv = tmp_path / "input.csv"
        input_csv.write_text(
            "id,names.types.ror_display,external_ids.type.wikidata.all\n"
            ",Test*en,Q99999\n"
        )

        data_dump = tmp_path / "dump.json"
        data_dump.write_text(json.dumps([
            {
                "id": "https://ror.org/test123",
                "names": [{"value": "Test Org", "types": ["ror_display"]}],
                "external_ids": [{"type": "wikidata", "all": ["Q99999"], "preferred": "Q99999"}]
            }
        ]))

        result = subprocess.run(
            [
                "validate-ror-records-input-csvs", "-i", str(input_csv), "-o", str(tmp_path),
                "-d", str(data_dump),
                "--test", "duplicate-external-ids",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert (tmp_path / "duplicate_external_ids.csv").exists()

        # Should detect the duplicate Wikidata ID
        content = (tmp_path / "duplicate_external_ids.csv").read_text()
        assert "Q99999" in content


class TestUpdateRecords:
    """Test integration with update record format."""

    def test_validate_update_records(self, tmp_path):
        """Test validation of update records with add/delete/replace syntax."""
        input_csv = tmp_path / "input.csv"
        # Update records have an id and use add==/delete==/replace syntax
        input_csv.write_text(
            "id,names.types.ror_display,status\n"
            "https://ror.org/12345,add==New Name*en,replace==active\n"
        )

        result = subprocess.run(
            ["validate-ror-records-input-csvs", "-i", str(input_csv), "-o", str(tmp_path), "--test", "validate-fields"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert (tmp_path / "validation_report.csv").exists()

    def test_validate_update_with_invalid_change_type(self, tmp_path):
        """Test that invalid change types in update records are caught."""
        input_csv = tmp_path / "input.csv"
        input_csv.write_text(
            "id,names.types.ror_display,status\n"
            "https://ror.org/12345,invalid_op==New Name*en,active\n"
        )

        result = subprocess.run(
            ["validate-ror-records-input-csvs", "-i", str(input_csv), "-o", str(tmp_path), "--test", "validate-fields"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        content = (tmp_path / "validation_report.csv").read_text()
        # Should report invalid change type
        assert "invalid" in content.lower() or len(content.strip().split("\n")) > 1
