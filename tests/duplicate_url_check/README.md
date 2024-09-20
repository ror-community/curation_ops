# Duplicate URL check

Compare URLs in new records CSV against data dump to identify duplicates.

## Installation

```
pip install -r requirements.txt
```

## Usage

```
python duplicate_url_check.py -i <input_csv> -d <input_json> -o <output_csv>
```

## Arguments

- `-i`, `--input_file`: Path to input CSV file
- `-d`, `--data_dump`: Path to input data dump file
- `-o`, `--output_file`: Path to output CSV file for matched results (default is "matched_urls.csv")


## Output

CSV file with columns: `csv_id`, `ror_id`, `record_name`
