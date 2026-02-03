"""Test orchestration logic."""

import sys
from pathlib import Path
from typing import Optional

from validate_ror_records_input_csvs.core.io import read_csv, write_csv
from validate_ror_records_input_csvs.core.loader import DataLoader, DataSource
from validate_ror_records_input_csvs.validators.base import BaseValidator, ValidatorContext


VALIDATORS: dict[str, BaseValidator] = {}


def register_validator(validator: BaseValidator) -> None:
    VALIDATORS[validator.name] = validator


def run_validators(
    input_file: Path,
    output_dir: Path,
    data_dump_path: Optional[str],
    geonames_user: Optional[str],
    tests: list[str],
) -> int:
    """Returns 0 on success (always, per design)."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine which validators to run
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
        print("No validators to run", file=sys.stderr)
        return 0

    needs_data = any(v.requires_data_source for v in selected)
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
        input_file=input_file,
        output_dir=output_dir,
        data_source=data_source,
        geonames_user=geonames_user,
    )

    for validator in selected:
        can_run, reason = validator.can_run(ctx)
        if not can_run:
            print(f"Error: {reason}", file=sys.stderr)
            sys.exit(1)

        print(f"Running {validator.name}...")
        results = validator.run(ctx)
        output_path = output_dir / validator.output_filename
        write_csv(results, output_path, validator.output_fields)
        print(f"  {len(results)} issues -> {output_path}")

    return 0
