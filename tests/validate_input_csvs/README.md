# validate-ror-records-input-csvs

CSV validation utility for ROR record input files.

## Installation

```bash
pip install -e .
```

For development:
```bash
pip install -e ".[dev]"
```

## Usage

```bash
validate-ror-records-input-csvs -i <input.csv> -o <output_dir> [options]
```

### Options

| Flag | Description |
|------|-------------|
| `-i, --input` | Input CSV file (required) |
| `-o, --output-dir` | Output directory for reports (default: current directory) |
| `-d, --data-dump` | Path to ROR data dump (JSON or ZIP). If not provided, downloads latest from GitHub automatically |
| `-u, --geonames-user` | GeoNames API username (required for address-validation) |
| `--test` | Validator(s) to run (can specify multiple, default: all) |

### Examples

Run validators that don't require GeoNames (data dump auto-downloaded):
```bash
validate-ror-records-input-csvs -i new_records.csv -o reports/ --test validate-fields --test duplicate-urls
```

Run all validators (requires GeoNames username):
```bash
validate-ror-records-input-csvs -i new_records.csv -o reports/ -u my_geonames_user
```

Use a local data dump instead of auto-downloading:
```bash
validate-ror-records-input-csvs -i new_records.csv -o reports/ -d v2.2-ror-data.json --test duplicate-external-ids
```

Run only validators that don't need external services:
```bash
validate-ror-records-input-csvs -i new_records.csv -o reports/ --test validate-fields --test in-release-duplicates
```

## Validators

| Validator | Description | Requires |
|-----------|-------------|----------|
| `validate-fields` | Validates field formats (URLs, IDs, types, etc.) for both new and update CSVs | - |
| `in-release-duplicates` | Finds duplicate records within the input CSV using URL matching and fuzzy name matching (85% threshold) | - |
| `duplicate-external-ids` | Checks for external ID conflicts (ISNI, Wikidata, FundRef, GRID) with existing ROR data | ROR data dump (auto-downloaded) |
| `duplicate-urls` | Checks for URL conflicts with existing ROR data (normalized comparison) | ROR data dump (auto-downloaded) |
| `address-validation` | Validates city/country against GeoNames API | `--geonames-user` (required) |

## Output

Each validator produces a CSV report in the output directory:

| Validator | Output File |
|-----------|-------------|
| `validate-fields` | `validation_report.csv` |
| `in-release-duplicates` | `in_release_duplicates.csv` |
| `duplicate-external-ids` | `duplicate_external_ids.csv` |
| `duplicate-urls` | `duplicate_urls.csv` |
| `address-validation` | `address_discrepancies.csv` |

## Field Validation Rules

The `validate-fields` validator checks:

- `status`: Must be `active`, `inactive`, or `withdrawn`
- `types`: Must be one of: `education`, `healthcare`, `company`, `funder`, `archive`, `nonprofit`, `government`, `facility`, `other`
- `names`: Must include language tag (e.g., `University Name*en`)
- `acronyms`: Must be uppercase letters, numbers, and spaces (or `delete`)
- `links`: Must start with `http://` or `https://`
- `established`: Must be 4-digit year (1000-9999)
- `wikipedia`: Must match `http(s)://[lang].wikipedia.org/...` or `delete`
- `ISNI`: Must match `0000 0000 0000 000X` format (with optional `*preferred` suffix) or `delete`
- `Wikidata`: Must match `Q[number]` format (with optional `*preferred` suffix) or `delete`
- `FundRef`: Must be a positive integer (with optional `*preferred` suffix) or `delete`
- `geonames_id`: Must be a positive integer (with optional `*preferred` suffix) or `delete`
- `city/country`: Required fields (warning if empty)

For update CSVs, field values support change types: `add==value`, `delete==value`, or plain replacement.

## Development

Run tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=validate_ror_records_input_csvs
```
