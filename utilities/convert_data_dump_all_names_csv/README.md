# Convert data dump to all names CSV

Converts ROR data dump file to a CSV file containing all names and their types.

## Usage

```
python convert_data_dump_all_names_csv.py -i <input_file> [-o <output_file>]
```

- `<input_file>`: Path to ROR data dump ZIP or schema v2 JSON file (required)
- `<output_file>`: Path to output CSV file (optional)

If no output file is specified, it will be named `<input_file_base>_all_names.csv`.

## Output

CSV file with columns:
- ROR Display Name
- ROR ID
- Name
- Name Type