# ROR Data Dump Testing Script

Script for validating ROR data dump integrity. Compares data dumps against release files and production API responses.

## Functionality
- Verifies release files are present in data dumps
- Compares old and new data dumps for unexpected changes
- Validates randomly sampled records against API responses
- Detects discrepancies between different data sources
- Generates comprehensive CSV reports for any differences found

## Installation
```bash
pip install -r requirements.txt
```

## Usage
```bash
python script.py -r /path/to/release/dir -o old_dump.json -n new_dump.json [-v 1|2] [-e stg|prd] [-a]
```

### Arguments
- `-r, --release_dir`: Directory containing release JSON files (required)
- `-o, --old_data_dump_file`: Path to previous data dump file (required)
- `-n, --new_data_dump_file`: Path to new data dump file (required)
- `-v, --schema-version`: ROR Schema version [1|2] (default: 2)
- `-e, --environment`: API environment [stg|prd] (default: prd)
- `-a, --api-tests`: Run API tests (optional, default: False)
- `-m, --missing_ids_outfile`: Missing IDs report file (default: missing_ids.csv)
- `-d, --release_diff_outfile`: Release differences report file (default: release_file_data_dump_file_diff.csv)
- `-p, --prod_data_dump_discrepancies_file`: Production discrepancies report file (default: prod_data_dump_discrepancies.csv)
- `-j, --jsondiff_outfile`: JSON differences report file (default: jsondiff.csv)

## Output Files
- `missing_ids.csv`: Records found in release files but missing from data dump
- `release_file_data_dump_file_diff.csv`: Differences between release files and data dump
- `prod_data_dump_discrepancies.csv`: Differences between data dump and API responses
- `jsondiff.csv`: Differences between old and new data dumps