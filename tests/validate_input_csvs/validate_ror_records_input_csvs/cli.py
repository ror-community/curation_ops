import argparse
import sys
from pathlib import Path

from validate_ror_records_input_csvs.runner import run_validators


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="validate-ror-records-input-csvs",
        description="Unified CSV validation utility for ROR curation",
    )

    parser.add_argument(
        "-i", "--input",
        type=Path,
        required=True,
        help="Input CSV file",
    )

    parser.add_argument(
        "-o", "--output-dir",
        type=Path,
        default=Path("."),
        help="Output directory for reports (default: current directory)",
    )

    parser.add_argument(
        "-d", "--data-dump",
        type=str,
        default=None,
        help="Path to data dump JSON/zip file (default: fetch from GitHub)",
    )

    parser.add_argument(
        "-u", "--geonames-user",
        type=str,
        default=None,
        help="GeoNames API username (required for address-validation)",
    )

    parser.add_argument(
        "--test",
        action="append",
        default=None,
        help="Validator(s) to run (repeatable). Default: all",
    )

    parsed = parser.parse_args(args)

    if parsed.test is None:
        parsed.test = ["all"]

    return parsed


def main() -> int:
    args = parse_args()

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        return 1

    from validate_ror_records_input_csvs.validators import register_all_validators
    register_all_validators()

    return run_validators(
        input_file=args.input,
        output_dir=args.output_dir,
        data_dump_path=args.data_dump,
        geonames_user=args.geonames_user,
        tests=args.test,
    )


if __name__ == "__main__":
    sys.exit(main())
