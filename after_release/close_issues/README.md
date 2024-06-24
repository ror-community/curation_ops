# Close Issues

Update and close issues using release files.


## Setup
1. Set a `GITHUB_TOKEN` environment variable with a valid Github access token that has permissions for ror-updates.


## Installation
```
pip install -r requirements.txt
```

## Usage

```
python close_issues.py -r <release_number> -i <input_file> -t <record_type>
```

- `-r`, `--release`: Release number (required)
- `-i`, `--input`: Input CSV file path (required)
- `-t`, `--type`: File type ('new' or 'updates') (required)


## Input File Format

The input CSV file should have the following columns (included in the release files by default):
- `html_url`: URL of the GitHub issue
- `id`: ROR ID (for 'new' records)
