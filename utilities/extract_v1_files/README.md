# ROR Record Extraction Script

Script for extracting v1 ROR records from a data dump based on matching ROR IDs in a release directory.

## Functionality
- Reads records from a ROR data dump JSON file
- Extracts ROR IDs from filenames in a release directory
- Matches and extracts records with corresponding ROR IDs
- Saves matched records as individual JSON files
- Preserves original JSON structure and formatting

## Installation
```bash
pip install -r requirements.txt
```

## Usage
```bash
python extract_v1_files.py -d data_dump.json -r /path/to/release/dir [-o output_dir]
```

### Arguments
- `-d, --data_dump`: Path to input data dump JSON file (required)
- `-r, --release_directory`: Directory containing ROR ID files (required)
- `-o, --output_directory`: Output directory for extracted records (default: extracted_files)

## Output
- Creates individual JSON files named `{ROR_ID}.json` in the output directory