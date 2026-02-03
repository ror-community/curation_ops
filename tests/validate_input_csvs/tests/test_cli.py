# tests/test_cli.py
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from validate_ror_records_input_csvs.cli import parse_args, main


class TestParseArgs:
    def test_required_input(self):
        with pytest.raises(SystemExit):
            parse_args([])

    def test_input_only(self):
        args = parse_args(["-i", "input.csv"])
        assert args.input == Path("input.csv")
        assert args.output_dir == Path(".")
        assert args.data_dump is None
        assert args.geonames_user is None
        assert args.test == ["all"]

    def test_all_options(self):
        args = parse_args([
            "-i", "input.csv",
            "-o", "./output",
            "-d", "dump.json",
            "-u", "myuser",
            "--test", "validate-fields",
            "--test", "duplicate-urls",
        ])
        assert args.input == Path("input.csv")
        assert args.output_dir == Path("./output")
        assert args.data_dump == "dump.json"
        assert args.geonames_user == "myuser"
        assert args.test == ["validate-fields", "duplicate-urls"]

    def test_short_flags(self):
        args = parse_args(["-i", "input.csv", "-o", "out", "-d", "dump.json", "-u", "user"])
        assert args.input == Path("input.csv")
        assert args.output_dir == Path("out")


class TestMain:
    def test_missing_input_file(self, tmp_path, capsys):
        with patch.object(sys, 'argv', ['validate-ror-records-input-csvs', '-i', str(tmp_path / 'nonexistent.csv')]):
            result = main()
        assert result != 0
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower() or "error" in captured.err.lower()
