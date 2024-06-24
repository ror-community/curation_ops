# Create issues from CSV file

Command-line tool to create new and update record issues in the ror-community/ror-updates repository from a CSV file.

## Installation

```
pip install -r requirements.txt
```

## Setup

1. Set a `GITHUB_TOKEN` environment variable with a valid GitHub access token with permissions for ror-updates.

## Usage

```
python create_issues_from_file.py -f <csv_file_path> -t <issue_type> [-a <additional_description>]
```

- `-f, --file`: Path to the CSV file containing the records.
- `-t, --issue-type`: Type of issue to create. Must be either `new` or `update`.
- `-a, --append-description` (optional): Additional description to append to the issue body for update issues.

The script will read the CSV file and create issues in the ror-community/ror-updates repository based on the provided records and issue type.