import sys
from pathlib import Path
from typing import Optional

from curation_validation.core.exceptions import ConfigurationError
from curation_validation.core.io import write_csv
from curation_validation.core.loader import DataLoader, DataSource
from curation_validation.validators.base import BaseValidator, ValidatorContext


VALIDATORS: dict[str, BaseValidator] = {}


def register_validator(validator: BaseValidator) -> None:
    VALIDATORS[validator.name] = validator


def determine_available_formats(
    csv_file: Optional[Path],
    json_dir: Optional[Path],
) -> set[str]:
    available = set()
    if csv_file is not None:
        available.add("csv")
    if json_dir is not None:
        available.add("json")
    if "csv" in available and "json" in available:
        available.add("csv_json")
    return available


def run_validators(
    csv_file: Optional[Path],
    json_dir: Optional[Path],
    output_dir: Path,
    data_dump_path: Optional[str],
    geonames_user: Optional[str],
    tests: list[str],
) -> int:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    available_formats = determine_available_formats(csv_file, json_dir)

    if "all" in tests:
        selected = list(VALIDATORS.values())
    else:
        selected = []
        for name in tests:
            if name not in VALIDATORS:
                print(f"Warning: Unknown validator '{name}', skipping", file=sys.stderr)
                continue
            selected.append(VALIDATORS[name])

    if not selected:
        return 0

    run_all = "all" in tests

    runnable = []
    for validator in selected:
        if "csv_json" in validator.supported_formats:
            if "csv_json" not in available_formats:
                if run_all:
                    print(f"Skipping {validator.name}: requires both --csv and --json-dir")
                    continue
                raise ConfigurationError(
                    f"{validator.name} requires both --csv and --json-dir"
                )
        runnable.append(validator)

    if not runnable:
        print("No validators to run with the available inputs")
        return 0

    needs_data = any(v.requires_data_source for v in runnable)
    data_source: Optional[DataSource] = None

    if needs_data:
        if data_dump_path:
            print(f"Loading data from: {data_dump_path}")
            loader = DataLoader(data_dump_path)
        else:
            print("Downloading latest ROR data dump from GitHub...")
            loader = DataLoader("github")
        data_source = loader.load()
        print(f"Loaded {len(data_source)} records")

    ctx = ValidatorContext(
        csv_file=csv_file,
        json_dir=json_dir,
        output_dir=output_dir,
        data_source=data_source,
        geonames_user=geonames_user,
    )

    for validator in runnable:
        can_run, reason = validator.can_run(ctx)
        if not can_run:
            if run_all:
                print(f"Skipping {validator.name}: {reason}", file=sys.stderr)
                continue
            print(f"Error: {reason}", file=sys.stderr)
            sys.exit(1)

        run_formats = []
        for fmt in validator.supported_formats:
            if fmt == "csv_json":
                if "csv_json" in available_formats:
                    run_formats.append("csv_json")
            elif fmt in available_formats:
                run_formats.append(fmt)

        for fmt in sorted(run_formats):
            if fmt != "csv_json":
                output_filename = f"{fmt}_{validator.output_filename}"
            else:
                output_filename = validator.output_filename

            print(f"Running {validator.name} ({fmt})...")
            results = validator.run(ctx)
            if results:
                output_path = output_dir / output_filename
                write_csv(results, output_path, validator.output_fields)
                print(f"  {len(results)} issues -> {output_path}")
            else:
                print(f"  No issues found")

    return 0
