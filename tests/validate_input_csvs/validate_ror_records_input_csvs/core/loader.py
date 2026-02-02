"""Load ROR data from various sources."""

import json
import os
import re
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

import requests

from validate_ror_records_input_csvs.core.exceptions import DataLoadError


class DataSource:
    """In-memory ROR data source for lookups."""

    def __init__(self, records: list[dict]):
        self._records_by_id: dict[str, dict] = {}
        self._records: list[dict] = records
        for record in records:
            if "id" in record:
                self._records_by_id[record["id"]] = record

    @classmethod
    def from_file(cls, file_path: str | Path) -> "DataSource":
        file_path = Path(file_path)

        if not file_path.exists():
            raise DataLoadError(f"File not found: {file_path}")

        try:
            if file_path.suffix == ".zip":
                return cls._load_from_zip(file_path)
            else:
                return cls._load_from_json(file_path)
        except (json.JSONDecodeError, KeyError, zipfile.BadZipFile) as e:
            raise DataLoadError(f"Error parsing {file_path}: {e}")

    @classmethod
    def _load_from_json(cls, file_path: Path) -> "DataSource":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return cls(data)
        elif isinstance(data, dict):
            return cls([data])
        else:
            raise DataLoadError(f"Unexpected JSON structure in {file_path}")

    @classmethod
    def _load_from_zip(cls, file_path: Path) -> "DataSource":
        """Prefers schema_v2 JSON files if available."""
        with zipfile.ZipFile(file_path, "r") as zf:
            json_files = [n for n in zf.namelist() if n.endswith(".json")]
            v2_files = [n for n in json_files if "schema_v2" in n]
            target_file = v2_files[0] if v2_files else json_files[0] if json_files else None

            if not target_file:
                raise DataLoadError(f"No JSON files found in {file_path}")

            with zf.open(target_file) as f:
                data = json.load(f)

            if isinstance(data, list):
                return cls(data)
            else:
                raise DataLoadError(f"Expected array of records in {target_file}")

    def get_record(self, ror_id: str) -> Optional[dict]:
        return self._records_by_id.get(ror_id)

    def id_exists(self, ror_id: str) -> bool:
        return ror_id in self._records_by_id

    def get_all_ids(self) -> list[str]:
        return list(self._records_by_id.keys())

    def get_all_records(self) -> list[dict]:
        return self._records

    def find_related_records(self, ror_id: str) -> list[dict]:
        """Find all records that have a relationship to the given ID."""
        related = []
        for record in self._records_by_id.values():
            for rel in record.get("relationships", []):
                if rel.get("id") == ror_id:
                    related.append(record)
                    break
        return related

    def __len__(self) -> int:
        return len(self._records_by_id)


class DataLoader:
    """Load ROR data from file or GitHub repo contents."""

    GITHUB_CONTENTS_URL = "https://api.github.com/repos/ror-community/ror-data/contents"
    VERSION_PATTERN = re.compile(r"v(\d+)\.(\d+)-(\d{4}-\d{2}-\d{2})-ror-data\.zip")

    def __init__(self, source: str | Path = "github"):
        self.source = source

    def load(self) -> DataSource:
        if self.source == "github":
            return self._load_from_github()
        else:
            return DataSource.from_file(self.source)

    def _parse_version(self, filename: str) -> tuple[int, int, str]:
        """Parse version from filename. Returns (major, minor, date) for sorting."""
        match = self.VERSION_PATTERN.match(filename)
        if match:
            return (int(match.group(1)), int(match.group(2)), match.group(3))
        return (0, 0, "")

    def _load_from_github(self) -> DataSource:
        try:
            response = requests.get(self.GITHUB_CONTENTS_URL, timeout=30)
            response.raise_for_status()
            contents = response.json()

            # Filter for ROR data zip files and sort by version
            zip_files = [
                item for item in contents
                if item["name"].endswith(".zip") and self.VERSION_PATTERN.match(item["name"])
            ]

            if not zip_files:
                raise DataLoadError("No ROR data zip files found in repository")

            # Sort by version (major, minor, date) and get the latest
            zip_files.sort(key=lambda x: self._parse_version(x["name"]), reverse=True)
            latest = zip_files[0]

            zip_response = requests.get(latest["download_url"], timeout=120)
            zip_response.raise_for_status()

            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
                tmp.write(zip_response.content)
                tmp_path = tmp.name

            try:
                return DataSource.from_file(tmp_path)
            finally:
                os.unlink(tmp_path)

        except requests.RequestException as e:
            raise DataLoadError(f"Error fetching from GitHub: {e}")
