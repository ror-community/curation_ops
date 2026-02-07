# curation-validation

Validation utility for [ROR](https://ror.org) curation inputs and outputs. Runs a configurable set of checks against new and updated organization records in CSV and/or JSON format, producing CSV reports of any issues found.

## Installation

Requires Python >= 3.10.

```bash
pip install .
```

For development:

```bash
pip install -e ".[dev]"
```

## Usage

```bash
curation-validation -c <csv_file> [-j <json_dir>] [-o <output_dir>] [options]
```

At least one of `--csv` or `--json-dir` is required.

### Arguments

| Flag | Description | Default |
|------|-------------|---------|
| `-c`, `--csv` | Path to CSV input file | |
| `-j`, `--json-dir` | Path to directory of JSON record files | |
| `-o`, `--output-dir` | Output directory for reports | `.` |
| `-d`, `--data-dump` | Path to ROR data dump (JSON or ZIP) | Fetched from GitHub |
| `-u`, `--geonames-user` | GeoNames API username | |
| `--test` | Validator(s) to run (repeatable) | All |

### Examples

Validate new records from a CSV:

```bash
curation-validation -c new_records.csv -o reports/
```

Validate with both CSV and JSON (enables integrity checks):

```bash
curation-validation -c records.csv -j json_dir/ -o reports/
```

Run specific validators:

```bash
curation-validation -c records.csv --test validate_fields --test leading_trailing
```

Check for duplicates against the current ROR dataset with GeoNames address validation:

```bash
curation-validation -c records.csv -u my_geonames_user --test production-duplicates
```

Use a local data dump instead of fetching from GitHub:

```bash
curation-validation -c records.csv -d /path/to/ror-data.zip -o reports/
```

## Validators

| Name | Formats | Requires | Description |
|------|---------|----------|-------------|
| `validate_fields` | csv, json | | Checks field values against expected formats and patterns |
| `leading_trailing` | csv, json | | Detects leading/trailing whitespace or punctuation |
| `unprintable-chars` | csv, json | | Finds non-printable characters in field values |
| `duplicate_values` | csv, json | | Finds the same value appearing in multiple fields within a record |
| `in-release-duplicates` | csv, json | | Finds duplicate records within the input dataset via URL and fuzzy name matching |
| `duplicate-urls` | csv, json | Data dump | Finds input records with website URLs already present in ROR |
| `duplicate-external-ids` | csv, json | Data dump | Finds input records sharing external IDs (ISNI, Wikidata, FundRef) with existing ROR records |
| `address-validation` | csv, json | GeoNames | Validates city/country against the GeoNames API |
| `production-duplicates` | csv, json | GeoNames | Searches for input records that may already exist in ROR by name and country |
| `new-record-integrity` | csv + json | | Verifies that CSV field values appear correctly in corresponding JSON files (new records) |
| `update-record-integrity` | csv + json | | Verifies that add/delete/replace changes from CSV are reflected in JSON files (updates) |

Validators requiring the ROR data dump will download the latest release from GitHub automatically unless a local path is provided with `--data-dump`.

## Output

Each validator produces a CSV report in the output directory. Files are named `{format}_{validator}.csv` (e.g., `csv_validate_fields.csv`) or `{validator}.csv` for validators that operate on both formats together. Reports are only written when issues are found.


## Testing

```bash
pytest
```

## License

MIT
