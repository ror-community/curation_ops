## Overview
Check new record JSON file IDs against prod and return status. Logs failure if any files/IDs return 200 or 500 status.

## Installation
```
pip install -r requirements.txt
```

## Usage
- `-i` or `--input`: The directory containing JSON files with ROR IDs to check.
- `-o` or `--output`: The path to the output CSV file where the results will be logged.
- `-v` or `--verbose`: Enable detailed logging output (optional).

```
python check_ids_on_prod.py -i <input_directory> -o <output_csv_file> [-v]
```

Examples:
```
# Basic usage
python check_ids_on_prod.py -i ./json_files -o ./results/status_check.csv

# With verbose logging
python check_ids_on_prod.py -i ./json_files -o ./results/status_check.csv -v
```

## Output
Output is a CSV file with two columns:
- `ID`: The ROR ID checked.
- `Status`: The result of the check (e.g., 200 Success, 400 Range Error).

### Logging Levels
- **Normal Mode**: Shows only warnings, errors, and critical status information.
- **Verbose Mode** (`-v`): Shows detailed debug information including:
  - Directory searching progress
  - File processing details
  - ID checking status
  - CSV operations
  - Multiprocessing progress