# Update data dump last modifed date

Updates records in a data dump file with a specified `last_modified` date based on a list of record IDs provided in a CSV file.

## Usage

```
python update_data_dump_last_mod.py -i INPUT_CSV -d DATA_DUMP_JSON -o OUTPUT_JSON -u UPDATES_DIR -t DATE
```

## Arguments

- `-i`, `--input_file`: Path to the input CSV file containing record IDs (required)
- `-d`, `--data_dump_file`: Path to the input JSON file (required)
- `-o`, `--output_file`: Path to the output JSON file (required)
- `-u`, `--updates_dir`: Directory to save individual JSON files (default: 'updates')
- `-t`, `--date`: Date to update the `last_modified` field (YYYY-MM-DD) (required)


## Output

- Updated JSON records are saved to the specified output file.
- Individual JSON files for updated records are saved in the specified updates directory.