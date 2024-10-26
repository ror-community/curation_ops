# JSON Integrity Checks

Scripts for validating ROR records against the CSV inputs used to create them.

## New Records Check
Validates that values from input CSV exist in corresponding JSON files.

```bash
python new_records_check_integrity.py -i input.csv -d /path/to/json -o output.csv
```

### New Records Error Types
- `missing`: Value specified in CSV is not present in JSON
- `transposition`: Value exists in JSON but in wrong field

## Update Records Check
Verifies whether specified changes in CSV have been applied to JSON records.

```bash
python update_records_check_integrity.py -i input.csv -d /path/to/json -o output.csv
```

### Update Records Error Types
- `missing`: Addition requested but value not found in JSON
- `still_present`: Deletion requested but value still exists in JSON
- `transposition`: Value exists in wrong field

## Arguments
- `-i/--input_file`: Input CSV file (required)
- `-d/--directory`: Directory containing JSON files (required)
- `-o/--output_file`: Output CSV file (optional, defaults provided)

## Output
Both scripts generate CSV files listing discrepancies between input specifications and JSON content.

### Notes
- Wikipedia URLs are considered equivalent regardless of URL encoding (e.g., `Polícia_de_Segurança_Pública` = `Pol%C3%ADcia_de_Seguran%C3%A7a_P%C3%BAblica`)
- Update records support change types: `add`, `delete`, `replace`