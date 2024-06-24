## Create records

Script for creating records using the bulk update endpoint in the ROR API. Allows submitting a CSV file for validation or record creation. See the [ROR API documentation](https://github.com/ror-community/ror-api?tab=readme-ov-file#create-new-record-file-v2-only) for the full details for the bulk update endpoint.

## Installation

```
pip install -r requirements.txt
```

## Usage

- `-i` or `--input_file`: Path to the input CSV file.
- `-o` or `--output_file`: Path to the output file (default: `report.csv`).
- `-v` or `--validate`: Flag to perform validation only (optional).

```
python create_records.py -i <input_csv_file> [-o <output_file>] [-v]
```

Example:

```
python create_records.py -i input.csv -o output.csv -v
```

## Configuration

The script requires the following environment variables:

- `GENERATE_API_USER`: ROR API user.
- `GENERATE_API_TOKEN`: ROR API token.

## Output

- If the `-v` flag is used, the validation response is written to the specified output file.
- If the `-v` flag is not used, the processed file is downloaded and saved with the original file name.
