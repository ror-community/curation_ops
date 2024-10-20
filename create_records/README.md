## Create records

Script for creating records using the bulk update endpoint in the ROR API. Allows submitting CSV files for validation or record creation. See the [ROR API documentation](https://github.com/ror-community/ror-api?tab=readme-ov-file#create-new-record-file-v2-only) for details.

## Installation

```
pip install -r requirements.txt
```

## Usage

- `-i` or `--input_file`: Path to a single CSV file.
- `-b` or `--batch`: Path to a directory containing multiple CSV files.
- `-o` or `--output_dir`: Output directory path (default: timestamped directory).
- `-v` or `--validate`: Perform validation only (optional).

```
python create_records.py (-i <input_csv_file> | -b <directory>) [-o <output_dir>] [-v]
```

Examples:

```
python create_records.py -i input.csv -o output_dir -v
python create_records.py -b batch_directory -o output_dir
```

## Configuration

Required environment variables:
- `GENERATE_API_USER`: ROR API user.
- `GENERATE_API_TOKEN`: ROR API token.

## Output

- Validation: Responses written to `validation_<filename>.csv` in the output directory.
- Creation: Processed files downloaded to the output directory.