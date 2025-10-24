## Create records

Script for creating records using the bulk update endpoint in the ROR API. Allows submitting CSV files for validation or record creation. See the [ROR API documentation](https://github.com/ror-community/ror-api?tab=readme-ov-file#create-new-record-file-v2-only) for details.

## Installation

```
pip install -r requirements.txt
```

## Usage

### Options

- `-i` or `--input_file`: Path to a single CSV file.
- `-b` or `--batch`: Path to a directory containing multiple CSV files.
- `-s` or `--batch_size`: Split a single CSV file into batches of N rows (requires `-i`).
- `-o` or `--output_dir`: Output directory path (default: timestamped directory `batch_YYYYMMDD_HHMMSS`).
- `-v` or `--validate`: Perform validation only (optional).

### Command Syntax

```
python create_records.py (-i <input_csv_file> | -b <directory>) [-s <batch_size>] [-o <output_dir>] [-v]
```

### Examples

**Single file validation:**
```
python create_records.py -i input.csv -o output_dir -v
```

**Batch directory processing:**
```
python create_records.py -b batch_directory -o output_dir
```

**Split large CSV into batches of 100 rows:**
```
python create_records.py -i large_input.csv -s 100 -o output_dir
```

## Configuration

Required environment variables:
- `GENERATE_API_USER`: ROR API user.
- `GENERATE_API_TOKEN`: ROR API token.

## Output

### Single File Mode

- **Validation:** Responses written to `validation_<filename>` in the output directory.
- **Creation:** Downloaded zip file in the output directory.

### Batch Mode (Directory)

- Downloaded zip files for each CSV in the output directory.
- 5-second delay between processing each file.

### Batch Split Mode (`--batch_size`)

Creates an organized output structure:

```
output_dir/
├── batches/
│   ├── batch_001_<timestamp>.zip
│   ├── batch_001_extracted/
│   ├── batch_002_<timestamp>.zip
│   ├── batch_002_extracted/
│   └── ...
├── logs/
│   ├── batch_001_report.csv
│   ├── batch_002_report.csv
│   └── ...
└── combined_new_records/ or combined_updates/
    ├── <ror_id>.json
    ├── <ror_id>.json
    └── ...
```

- **batches/**: Individual batch zip files and their extracted contents
- **logs/**: Report CSV files from each batch
- **combined_new_records/** or **combined_updates/**: All JSON records merged from all batches