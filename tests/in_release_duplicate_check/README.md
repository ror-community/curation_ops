# in_release_duplicate_check.py

This script checks for duplicate name metadata in a directory containing ROR (Research Organization Registry) records.

## Installation

1. Clone the repository or download the script file.
2. Install the required dependencies by running the following command:

   ```bash
   pip install -r requirements.txt
   ```

## Usage

```bash
python in_release_duplicate_check.py -i <input_directory> [-o <output_file>]
```

- `-i, --input_dir`: Input directory path containing JSON files of ROR records (required).
- `-o, --output_file`: Output CSV file path (default: "in_release_duplicates.csv").

## Functionality

1. The script reads all JSON files in the specified input directory.
2. It extracts the names (ROR display name, aliases, and labels) and country code for each ROR record.
3. It compares the normalized names of each record with all other records.
4. If the match ratio between two names is greater than or equal to 85 and the country codes match (if available), it considers them as potential duplicates.
5. The script writes the potential duplicate records to the output CSV file with columns: "ror_id", "name", "duplicate_ror_id", "duplicate_name", and "match_ratio".