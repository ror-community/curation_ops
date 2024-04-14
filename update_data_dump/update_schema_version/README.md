# Update schema version

Updates records in a ROR data dump file with a new schema version, excluding ROR IDs provided in a separate CSV file.

## Usage

```
python update_schema_version.py -i <input_csv> -d <data_dump_json> [-o <output_json>]
```

- `-i`, `--input_file`: Path to the input CSV file containing the records to be excluded (required).
- `-d`, `--data_dump_file`: Path to the input data dump file (required).
- `-o`, `--output_file`: Path to the output data dump file (required).

## Input CSV Format

The input CSV file is that returned by get_all_ror_ids_from_directory.py and should have the following columns:
- `id`: ROR ID for the record.


## Output

The script saves the updated JSON data dump to the specified output file and the updated indiviudal files in a separate directory (default: `updates`).