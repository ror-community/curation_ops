"""Regression checks for relationship generation."""

import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


GENERATOR = Path(__file__).with_name("generate_relationships.py").resolve()
FIELDS = [
    "Record ID", "Related ID", "Name of org in Record ID",
    "Name of org in Related ID", "Relationship of Related ID to Record ID",
    "Current location of Related ID",
]


class RelationshipGenerationTests(unittest.TestCase):
    def run_generator(self, version, records, relationships):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "new").mkdir()
            for identifier, status in records.items():
                record = {
                    "id": "https://ror.org/" + identifier,
                    "status": status,
                    "relationships": [],
                    "name": identifier,
                    "names": [{"value": identifier, "lang": "en",
                               "types": ["ror_display", "label"]}],
                    "admin": {"last_modified": {"date": "2026-10-06"}},
                }
                (root / "new" / (identifier + ".json")).write_text(
                    json.dumps(record), encoding="utf-8")
            with (root / "relationships.csv").open("w", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=FIELDS)
                writer.writeheader()
                for record_id, related_id, relationship in relationships:
                    writer.writerow(dict(zip(FIELDS, [
                        "https://ror.org/" + record_id,
                        "https://ror.org/" + related_id,
                        record_id, related_id, relationship, "Release",
                    ])))
            result = subprocess.run(
                [sys.executable, str(GENERATOR), "relationships.csv", "-v", str(version)],
                cwd=root, capture_output=True, text=True, timeout=30)
            generated = {
                identifier: json.loads((root / "new" / (identifier + ".json")).read_text())
                for identifier in records
            }
            return result, generated

    def test_successor_chain_can_include_an_inactive_intermediate(self):
        relationships = [
            ("04k0yqc48", "00bhc0620", "Successor"),
            ("00bhc0620", "04k0yqc48", "Predecessor"),
            ("00bhc0620", "05ecg5h20", "Successor"),
            ("05ecg5h20", "00bhc0620", "Predecessor"),
        ]
        for version in (1, 2):
            with self.subTest(version=version):
                result, generated = self.run_generator(version, {
                    "04k0yqc48": "inactive", "00bhc0620": "inactive",
                    "05ecg5h20": "active",
                }, relationships)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                for record_id, related_id, relationship in relationships:
                    expected_type = relationship if version == 1 else relationship.lower()
                    self.assertIn({
                        "id": "https://ror.org/" + related_id,
                        "label": related_id, "type": expected_type,
                    }, generated[record_id]["relationships"])

    def test_structural_links_from_active_to_inactive_remain_rejected(self):
        for version in (1, 2):
            for relationship in ("Parent", "Child", "Related"):
                with self.subTest(version=version, relationship=relationship):
                    result, generated = self.run_generator(version, {
                        "05ecg5h20": "active", "00bhc0620": "inactive",
                    }, [("05ecg5h20", "00bhc0620", relationship)])
                    self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                    self.assertIn("has a status other than active", result.stdout)
                    self.assertEqual(generated["05ecg5h20"]["relationships"], [])


if __name__ == "__main__":
    unittest.main()
