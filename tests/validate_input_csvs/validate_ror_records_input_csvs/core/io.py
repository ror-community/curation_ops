"""File I/O utilities for CSV and JSON handling."""

import csv
from pathlib import Path
from typing import Any


def read_csv(file_path: Path) -> list[dict[str, Any]]:
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)
    except IOError as e:
        raise IOError(f"Error reading {file_path}: {e}")


def write_csv(
    data: list[dict[str, Any]],
    file_path: Path,
    fieldnames: list[str]
) -> None:
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)


def detect_file_type(records: list[dict[str, Any]]) -> str:
    """Returns 'new' if no records have an id, 'updates' otherwise."""
    for record in records:
        id_value = record.get("id", "")
        if id_value and id_value.strip():
            return "updates"
    return "new"
