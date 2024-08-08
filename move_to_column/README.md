# move_to_column.py
Moves GitHub issues listed in a CSV file to a specified column curationproject.

## Installation
```
pip install -r requirements.txt
```

## Setup
1. Set a `GITHUB_TOKEN` environment variable with a valid GitHub access token.

## Usage
```
python move_to_column.py -i <input_file> -c <target_column>
```
- `-i, --input_file`: (Required) Path to the new or updates record CSV file containing issue URLs.
- `-c, --target_column`: (Required) Name of the target column to move issues to.