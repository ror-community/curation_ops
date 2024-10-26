# Duplicate values check

Script to identify duplicate values across fields in records, excluding expected duplicates in administrative data, external identifiers, language tags, relationship types, and name types.

## Usage

```bash
python duplicate_check.py -i /path/to/json/files -o output.csv
```

## Arguments

- `-i, --input_dir`: Directory containing ROR JSON records
- `-o, --output_file`: Path for output CSV (default: duplicate_values.csv)

## Output

CSV file with columns:
- ror_id: Organization's ROR ID
- field: Field containing duplicate value
- value: The duplicated value
- duplicated_in: Original field where value first appears

## Ignored Duplicates

- Administrative fields (admin_*)
- External IDs in preferred/all pairs
- Language tags (*_lang)
- Relationship types
- Name types