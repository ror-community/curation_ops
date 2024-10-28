# Address Check

Validates city and country data in a new records CSV against the GeoNames API.

## Requirements
- `requests` library (`pip install -r requirements.txt`)
- GeoNames API account (get one at http://www.geonames.org/login)

## Usage
```bash
python address_check.py -i input.csv -u your_geonames_username [-o output.csv] [-v] [-l logfile.log]
```

### Arguments
- `-i, --input_file`: Input CSV file (required)
- `-u, --api_user`: GeoNames API username (required)
- `-o, --output_file`: Output CSV file (default: address_discrepancies.csv)
- `-v, --verbose`: Enable verbose logging
- `-l, --log_file`: Custom log file path (default: address_check.log)

### Input CSV Format
Required columns:
- `names.types.ror_display`: Organization name
- `locations.geonames_id`: GeoNames location ID
- `city`: City name
- `country`: Country name

### Output
Generates a CSV file with discrepancies containing:
- Organization name
- GeoNames ID
- CSV city/country
- API city/country