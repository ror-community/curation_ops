# ROR Duplicate Check Scripts

Scripts for checking duplicate name and URL metadata in ROR (Research Organization Registry) records:

1. `in_release_duplicate_check_csv.py`: Checks for duplicates in a CSV file containing ROR records.
2. `in_release_duplicate_check_json.py`: Checks for duplicates in a directory containing JSON files of ROR records.

## Installation
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### CSV Input Script

```bash
python in_release_duplicate_check_csv.py -i <input_file.csv> [-o <output_file.csv>]
```

- `-i, --input_file`: Input CSV file path containing ROR records (required).
- `-o, --output_file`: Output CSV file path (default: "csv_duplicates.csv").

### JSON Input Script

```bash
python in_release_duplicate_check_json.py -i <input_directory> [-o <output_file.csv>]
```

- `-i, --input_dir`: Input directory path containing JSON files of ROR records (required).
- `-o, --output_file`: Output CSV file path (default: "in_release_duplicates.csv").

## Functionality

Both scripts perform the following tasks:

1. Read ROR records from the input source (CSV file or JSON files in a directory).
2. Extract names (ROR display name, aliases, and labels) and URLs for each ROR record.
3. Compare the normalized names and URLs of each record with all other records.
4. Check for URL matches and name matches with a fuzzy matching ratio of 85 or higher.
5. For the JSON script, it also considers the country code when available, only comparing records from the same country.
6. Write potential duplicate records to the output CSV file with columns: "ror_id", "name", "url", "duplicate_ror_id", "duplicate_name", "duplicate_url", "match_type", and "match_ratio".
