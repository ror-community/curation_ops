import pytest

from curation_validation.cli import parse_args


class TestParseArgs:
    def test_csv_only(self):
        args = parse_args(["-c", "input.csv"])
        assert args.csv == "input.csv"
        assert args.json_dir is None

    def test_json_only(self):
        args = parse_args(["-j", "json_dir/"])
        assert args.json_dir == "json_dir/"
        assert args.csv is None

    def test_both_inputs(self):
        args = parse_args(["-c", "input.csv", "-j", "json_dir/"])
        assert args.csv == "input.csv"
        assert args.json_dir == "json_dir/"

    def test_all_options(self):
        args = parse_args([
            "-c", "input.csv",
            "-j", "json_dir/",
            "-o", "output/",
            "-d", "dump.json",
            "-u", "testuser",
            "--test", "validate-fields",
            "--test", "leading-trailing",
        ])
        assert args.csv == "input.csv"
        assert args.json_dir == "json_dir/"
        assert str(args.output_dir) == "output"
        assert args.data_dump == "dump.json"
        assert args.geonames_user == "testuser"
        assert args.test == ["validate-fields", "leading-trailing"]

    def test_default_output_dir(self):
        args = parse_args(["-c", "input.csv"])
        assert str(args.output_dir) == "."

    def test_default_test_is_all(self):
        args = parse_args(["-c", "input.csv"])
        assert args.test == ["all"]

    def test_requires_at_least_one_input(self):
        with pytest.raises(SystemExit):
            parse_args([])
