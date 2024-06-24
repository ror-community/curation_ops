# Check for Duplicate External IDs

Finds matches between release files in a directory and a data dump file based on overlapping external IDs.

## Usage

```
python check_for_duplicate_external_ids.py -i <input_directory> -d <data_dump> [-o <output_file>]
```

- `-i`, `--input_directory`: Directory containing the files (required).
- `-d`, `--data_dump`: Path to the data dump file (required).
- `-o`, `--output_file`: Path to the output CSV file (default: `duplicate_external_ids.csv`).

## Output

The script generates a CSV file with the following columns:

- `id`: ID of the record from the input file.
- `ror_display_name`: ROR display name of the record from the input  file.
- `data_dump_id`: ID of the matching record from the data dump file.
- `data_dump_ror_display_name`: ROR display name of the matching record from the data dump file.
- `overlapping_external_id`: The overlapping external ID found between the two records.