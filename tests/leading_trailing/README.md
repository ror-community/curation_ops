# leading_trailing.py

Checks for leading and trailing whitespace and punctuation characters in a directory containing ROR records.

## Usage

```
python leading_trailing.py -i <input_directory> [-o <output_file>]
```

- `-i, --input_dir`: Required. Directory containing ROR JSON files.
- `-o, --output_file`: Optional. Output CSV file path. Default is "leading_trailing_chars.csv".

## Output

The script generates a CSV file with the following columns:
- `ror_id`: The ID of the ROR record.
- `field`: The flattened JSON key where the leading/trailing character was found.
- `value`: The value containing the leading/trailing character.