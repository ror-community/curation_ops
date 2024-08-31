# Check for Duplicate External IDs

Scripts that find matches between input files and a data dump file based on overlapping external IDs. One script processes a new records file CSV input, while the other processes a directory of ROR records (in JSON format).

## Scripts

1. `check_for_duplicate_external_ids_csv.py`: Processes a CSV input file.
2. `check_for_duplicate_external_ids_json.py`: Processes JSON files in a directory.

## Usage

### CSV Input

```
python check_for_duplicate_external_ids_csv.py -i <input_csv> -d <data_dump> [-o <output_file>]
```

- `-i`, `--input_csv`: Path to the input CSV file (required).
- `-d`, `--data_dump`: Path to the data dump file (required).
- `-o`, `--output_file`: Path to the output CSV file (default: `duplicate_external_ids.csv`).

### JSON Input

```
python check_for_duplicate_external_ids_json.py -i <input_directory> -d <data_dump> [-o <output_file>]
```

- `-i`, `--input_directory`: Directory containing the JSON files (required).
- `-d`, `--data_dump`: Path to the data dump file (required).
- `-o`, `--output_file`: Path to the output CSV file (default: `duplicate_external_ids.csv`).

## Output

Both scripts generate a CSV file with the following columns:

- `id`: ID of the record from the input file.
- `ror_display_name`: ROR display name of the record from the input file.
- `data_dump_id`: ID of the matching record from the data dump file.
- `data_dump_ror_display_name`: ROR display name of the matching record from the data dump file.
- `overlapping_external_id`: The overlapping external ID found between the two records.

