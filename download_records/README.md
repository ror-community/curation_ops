# Download records

Downloads records from the ROR API.

## Installation

```
pip install -r requirements.txt
```

## Input

The input to the script is a CSV file containing ROR IDs. The CSV file should have a column named "id" that holds the ROR IDs.


## Usage

```
python download_records.py -i <input_file> -s <schema_version>
```

- `-i, --input_file`: Path to the input CSV file containing ROR IDs.
- `-s, --schema_version`: Schema version for the records to download. Choices: 1 or 2.

## Output

The downloaded records are saved as individual JSON files in a newly-created directory. The directory name follows the format YYYYMMDD_HHMMSS, representing the timestamp when the script was run.

