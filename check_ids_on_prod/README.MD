## Overview
Check pre-release new record JSON files against prod and return status. Logs failure if any files return 200 or 500 status.


## Installation
```
pip install -r requirements.txt
```

## Usage
- `-i` or `--input`: The directory containing JSON files with ROR IDs to check.
- `-o` or `--output`: The path to the output CSV file where the results will be logged.

```
python check_prod_for_ids.py -i <input_directory> -o <output_csv_file>
```

Example:
```
python check_prod_for_ids.py -i ./json_files -o ./results/status_check.csv
```

## Output
Output is a CSV file with two columns:
- `ID`: The ROR ID checked.
- `Status`: The result of the check (e.g., 200 Success, 400 Range Error).
