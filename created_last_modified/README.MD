# Created and Last Modified

Parses a series of ROR data dump files to determine when a specific record was first created and the last date it was modified.

## Requirements:
- Python 3
- Files to be processed should have a date in their filename in the format `YYYY-MM-DD`.

## How to Use:

### Arguments:
- `-l`, `--file_list`: The path to a file that contains a sorted list of paths for the data dump files you want to process. One filepath per line.
- `-o`, `--output`: (Optional) The name of the output CSV file. Default is `created_last_modified.csv`.

### Execution:

Run the script by using the following command:
```bash
python created_last_modified.py -l path/to/file_list.txt -o output_filename.csv
```

For example, if you have a list of data dump files in `file_list.txt`, and you want the output to be saved as `data_output.csv`, you would run:

```bash
python created_last_modified.py -l file_list.txt -o data_output.csv
```