# Get all ROR IDS from data dump file

Extracts all ROR IDs from a data dump and saves them to a text file.

## Usage

```
python get_all_ror_ids_from_data_dump.py -i input_file.json [-o output_file.txt]
```

- `-i`, `--input`: Path to the data dumpy file (required)
- `-o`, `--output`: Path to the output text file (optional, default: `all_ror_ids.txt`)


## Output

The script saves the extracted ROR IDs to the specified txt file, with each ID on a separate line.
