# Compare JSON Files

Compares v1 and v2 ROR JSON files in two directories and generates a CSV report identifying any missing files, as well as missing or mismatched values.

## Usage

```
python compare_v1_v2_files.py -v1 /path/to/v1/directory -v2 /path/to/v2/directory -o output.csv
```

- `-v1`, `--v1_dir`: Path to the v1 input directory
- `-v2`, `--v2_dir`: Path to the v2 input directory
- `-o`, `--output_csv`: Output CSV file path (default: `compare_v1_v2_report.csv`)


## CSV Report
- ID: The ID of the JSON file
- Matched ID Found: Indicates whether a matching ID was found in the other directory
- Key-Value Pairs Matched: Indicates whether all key-value pairs matched between the two versions
- All Values Matched: Indicates whether all values matched between the two versions
- Mismatched Keys: Lists the keys that have mismatched values between the two versions
