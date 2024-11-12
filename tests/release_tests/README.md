# ROR Release Testing Script

Script for automated release testing of ROR releases.

## Functionality
- Validates API endpoints by retrieving organization records
- Compares JSON responses between staging and production environments
- Tests search functionality using organization names
- Performs UI testing on a random sample of records
- Implements rate limiting to prevent API throttling (1000 calls per 300s)
- Processes requests in parallel (max 5 concurrent requests)
- Randomly samples and tests unprocessed records
- Generates detailed CSV reports for test results and differences

## Installation

### 1. Install Selenium Dependencies
```bash
# Ubuntu/Debian:
sudo apt-get install firefox-geckodriver

# macOS:
Install homebrew - https://brew.sh
brew install geckodriver

# Windows:
# Download geckodriver from https://github.com/mozilla/geckodriver/releases
# Add to system PATH
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

## Usage

Generate the all_ror_ids.txt file from the last data dump with the [script for getting all ROR IDs from a data dump file](https://github.com/ror-community/curation_ops/tree/main/utilities/get_all_ror_ids/get_all_ror_ids_from_data_dump), then:

```bash
python script.py -r /path/to/release/files -a all_ror_ids.txt [-e prd|stg] [-v 1|2]
```

### Arguments
- `-r, --release_directory`: Directory containing ROR JSON files (required)
- `-a, --all_ror_ids_file`: File containing all ROR IDs (default: all_ror_ids.txt)
- `-e, --environment`: API environment [prd|stg] (default: prd)
- `-v, --version`: API version [1|2] (default: 2)
- `-t, --release_tests_outfile`: Test results output file (default: release_tests.csv)
- `-j, --jsondiff_outfile`: JSON differences output file (default: jsondiff.csv)
- `-u, --ui_tests_outfile`: UI test results output file (default: ui_tests.csv)

## Output Files
- `release_tests.csv`: Results of API retrieval, comparison, and search tests
- `jsondiff.csv`: Detailed differences found between JSON responses
- `ui_tests.csv`: Results of UI retrieval and search testing