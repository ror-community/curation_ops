# ROR JSON Integrity Check Scripts

Scripts for validating ROR JSON records against their  CSV inputs:

## New Records Check
```bash
python new_records_check_integrity.py -i input.csv -d /path/to/json -o output.csv
```

## Update Records Check

```bash
python update_records_check_integrity.py -i input.csv -d /path/to/json -o output.csv
```

## Arguments
- `-i/--input_file`: Input CSV file (required)
- `-d/--directory`: Directory containing JSON files (required)
- `-o/--output_file`: Output CSV file (optional, defaults provided)

## Output
Both scripts generate CSV files listing discrepancies between input specifications and JSON content.