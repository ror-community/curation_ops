# Diff data dumps

Compare two data dump files and write their differences to a CSV file.

## Installation

```
pip install -r requirements.txt
```

## Usage

```
python diff_data_dumps.py -f1 file1.json -f2 file2.json -o diff.csv
```

## Arguments

- `-f1`, `--file1`: Path to the first JSON file (required)
- `-f2`, `--file2`: Path to the second JSON file (required)
- `-o`, `--output`: Path to the output CSV file (default: 'diff.csv')

## Output

The script generates a CSV file with the following columns:

- `id`: Record ID
- `field_path`: Path to the field with the difference
- `change_type`: Type of change (e.g., 'type_change', 'value_change', 'item_added', 'item_removed', 'error')
- `old_value`: Old value of the field
- `new_value`: New value of the field
