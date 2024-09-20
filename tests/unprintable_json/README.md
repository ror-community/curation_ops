# Unprintable character check

Checks for unprintable characters in JSON files within a specified directory and outputs the results to a CSV file.

## Usage

```
python unprintable_check.py -i INPUT_DIR [-o OUTPUT_FILE]
```

- `-i INPUT_DIR`: Path to the directory containing the JSON files to be checked (required).
- `-o OUTPUT_FILE`: Path to the output CSV file (optional, default: "unprintable_chars.csv").

## Output

The script generates a CSV file with the following columns:
- `ror_id`: The ID of the JSON record.
- `field`: The flattened field name where the unprintable character was found.
- `value`: The value containing the unprintable character.