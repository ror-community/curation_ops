## Overview
Validates new and updated record files, identifying any issues in the data fields of the CSV file.

## Usage
To use the script, run it from the command line with the required arguments.

### Arguments
- `-i` or `--input_file`: Path to the input CSV file. (Required)
- `-f` or `--file_type`: Type of records in the CSV file. Choices are 'new' or 'updates'. (Required)
- `-o` or `--output_file`: Path for the output CSV report file. (Optional, defaults to 'validation_report.csv')

## Usage
```
python main.py -i path/to/input.csv -f new|updates -o path/to/output.csv
```