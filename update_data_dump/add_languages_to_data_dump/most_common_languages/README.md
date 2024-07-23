# Most Common Languages

Processes a JSON file containing information about organizations and their associated languages to count the unique languages per country, remove outlier languages based on a specified threshold, and save the results to a CSV file.

## Usage

```
python get_most_common_languages.py -i INPUT_FILE [-o OUTPUT_FILE] [-t THRESHOLD]
```

## Arguments

- `-i`, `--input_file`: Path to the input JSON file (required)
- `-o`, `--output_file`: Path to the output CSV file (default: 'most_common_languages.csv')
- `-t`, `--threshold`: Threshold for removing outlier languages (default: 0.1)

## Output

- CSV file with columns for country and most common languages.
- Ensures that English ('en') is included in the list of common languages for each country.