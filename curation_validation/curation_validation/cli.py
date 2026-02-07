import argparse
import sys
from pathlib import Path


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="curation-validation",
        description="Unified validation utility for ROR curation records",
    )

    parser.add_argument(
        "-c", "--csv",
        type=str,
        default=None,
        help="Path to CSV input file",
    )

    parser.add_argument(
        "-j", "--json-dir",
        type=str,
        default=None,
        help="Path to JSON records directory",
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
        help="GeoNames API username",
    )

    parser.add_argument(
        "--test",
        action="append",
        default=None,
        help="Validator(s) to run (repeatable). Default: all",
    )

    parsed = parser.parse_args(args)

    if parsed.csv is None and parsed.json_dir is None:
        parser.error("At least one of --csv or --json-dir is required")

    if parsed.test is None:
        parsed.test = ["all"]

    return parsed


def main() -> int:
    args = parse_args()

    csv_file = Path(args.csv) if args.csv else None
    json_dir = Path(args.json_dir) if args.json_dir else None

    if csv_file and not csv_file.exists():
        print(f"Error: CSV file not found: {csv_file}", file=sys.stderr)
        return 1

    if json_dir and not json_dir.exists():
        print(f"Error: JSON directory not found: {json_dir}", file=sys.stderr)
        return 1

    from curation_validation.validators import register_all_validators
    from curation_validation.runner import run_validators

    register_all_validators()

    return run_validators(
        csv_file=csv_file,
        json_dir=json_dir,
        output_dir=args.output_dir,
        data_dump_path=args.data_dump,
        geonames_user=args.geonames_user,
        tests=args.test,
    )


if __name__ == "__main__":
    sys.exit(main())
