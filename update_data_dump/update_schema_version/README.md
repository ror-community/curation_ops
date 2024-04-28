# Update schema version

Updates records in a ROR data dump file with a new schema version, based on the ROR IDs provided in a separate CSV file. The script can either include or exclude the specified ROR IDs from the schema version update.

## Usage

```
python update_schema_version.py -i <input_csv> -d <data_dump_json> -o <output_json> -u <updates_dir> -c <exclude_or_include> -s <schema_version>
```

- `-i`, `--input_file`: Path to the input CSV file containing the ROR IDs (required).
- `-d`, `--data_dump_file`: Path to the input data dump file (required).
- `-o`, `--output_file`: Path to the output data dump file (required).
- `-u`, `--updates_dir`: Directory to save individual JSON files (default: `updates`).
- `-c`, `--exclude_or_include`: Flag for whether to exclude or include IDs in the input file from the schema version update. Choices: `exclude`, `include` (required).
- `-s`, `--schema_version`: Schema version with which to update JSON files. Choices: `1.0`, `2.0` (required).

## Input CSV Format

The input CSV file should have the following column:

- `ror_id`: ROR ID for the record.

## Output

The script saves the updated JSON data dump to the specified output file and the updated individual files in a separate directory (default: `updates`).