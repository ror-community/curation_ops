# Add type funder to data dump

Updates a ROR data dump with type 'funder' for all records with a Funder ID.

## Usage

```
python add_funder_type_to_data_dump.py -i <input_csv> -d <data_dump_json> [-o <output_json>]
```

- `-d`, `--data_dump_file`: Path to the input data dump file (required).
- `-o`, `--output_file`: Path to the output data dumpp file (required).


## Output

The script saves the updated JSON data dump to the specified output file.