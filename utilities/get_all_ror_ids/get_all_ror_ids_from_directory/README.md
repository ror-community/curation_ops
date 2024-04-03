# Get Names and ROR IDs ad directory

Extracts names and ROR IDs from JSON files in a specified directory and saves them to a CSV file.

## Usage

```
python get_all_ror_ids_from_directory.py -i /path/to/input/directory [-o output_file.csv]
```

- `-i`, `--input_dir`: Path to the directory containing JSON files (required)
- `-o`, `--output_file`: Path to the output CSV file (optional, default: `all_names_ror_ids.csv`)

## Output

The script saves the extracted names and ROR IDs to the specified CSV file, with each name and ID on a separate row.