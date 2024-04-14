# Data dump to CSV
Creates a CSV version of a ROR JSON data dump. The CSV contains a subset of fields from the JSON file, some of which have been flattened for easier parsing. The JSON file remains the version of record.

## Usage

1. Run the script that corresponds to the schema version of the data dump, specifying the data dump JSON files as a positional argument.

For v1 dump:

        python convert_to_csv.py /path/to/dump/v1.32-2023-09-14-ror-data.json

For v2 dump:

        python convert_to_csv_v2.py /path/to/dump/v1.32-2023-09-14-ror-data_schema_v2.json


CSV will be created in the same directory as the input JSON file, with the same filename but with .csv extension (ex `/path/to/dump/v1.32-2023-09-14-ror-data.csv`).

