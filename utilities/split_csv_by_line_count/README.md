## Split CSV by line count

Script to split a large CSV file into smaller files based on line count.

## Installation

```
pip install -r requirements.txt
```

## Usage

```
python split_csv_by_line_count.py -i <input_file> -l <line_count> [-o <output_dir>] [-v]
```

Arguments:
- `-i` or `--input_file`: Path to input CSV file (required)
- `-l` or `--line_count`: Number of lines per output file (required)
- `-o` or `--output_dir`: Output directory (default: {input_file_name}_split_{line_count})
- `-v` or `--validate`: Validate split files against input file (optional)

## Output

Split CSV files are saved in the specified output directory.

## Logging

Logs are written to `csv_splitter.log` and displayed in the console.

## Validation

If `-v` is used, the script compares split files with the input file and reports any discrepancies.