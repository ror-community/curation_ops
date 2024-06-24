# On production duplicate check

Checks for duplicate records in ROR based on the organization names in records for a given directory of record files.


## Installation
   ```
   pip install -r requirements.txt
   ```

## Usage

```
python on_production_duplicate_check.py -i <input_directory> [-o <output_file>]
```

- `-i`, `--input_dir`: Required. The directory path containing the JSON files of ROR records to check for duplicates.
- `-o`, `--output_file`: Optional. The output CSV file path to store the duplicate records found. Default is "on_production_duplicates.csv".

## Functionality

1. The script iterates over each JSON file in the specified input directory.
2. For each JSON file, it extracts the names and country code from the record.
3. The names are searched in ROR API for potential duplicate records, based on the normalized organization name and country code.
4. If the match ratio between two names is greater than or equal to 85 and the country codes match (if available), it considers them as potential duplicates.
5. The script writes the potential duplicate records to the output CSV file with columns: "ror_id", "name", "duplicate_ror_id", "duplicate_name", and "match_ratio".


## Output

The script generates a CSV file with the following columns:
- `ror_id`: The ROR ID of the original record.
- `name`: The name of the original record.
- `matched_ror_id`: The ROR ID of the matched duplicate record.
- `matched_name`: The name of the matched duplicate record.
- `match_ratio`: The match ratio between the original and matched names.