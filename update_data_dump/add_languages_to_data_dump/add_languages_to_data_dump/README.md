# Add languages to data dump

Updates a ROR data dump fule with language information from the CSV file returned by `detect_languages_in_data_dump.py`. Run `detect_outliers.py` first and correct any errant language tagging.

## Usage

```
python add_languages_to_data_dump.py -i <input_csv> -d <data_dump_json> [-o <output_json>]
```

- `-i`, `--input_file`: Path to the input CSV file containing language information (required).
- `-d`, `--data_dump_file`: Path to the input data dump file (required).
- `-o`, `--output_file`: Path to the output data dump file (default: 'dump_w_languages_added.json').

## Input CSV Format

The input CSV file is that returned by `detect_languages_in_data_dump.py` and should have the following columns:
- `id`: Identifier for the record.
- `name`: Name value.
- `lang`: Language code for the corresponding name.


## Output

The script saves the updated JSON data dump to the specified output file (default: `dump_w_languages_added.json`).