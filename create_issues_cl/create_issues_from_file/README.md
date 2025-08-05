# Create issues from CSV file

Command-line tool to create new and update record issues in the ror-community/ror-updates repository from a CSV file.

## Installation

```
pip install -r requirements.txt
```

## Setup

1. Set a `GITHUB_TOKEN_PERSONAL` environment variable with a valid GitHub access token with permissions for ror-updates.

## Usage

```
python create_issues_from_file.py -i <csv_file_path> -t <issue_type> [-f <format>] [-a <additional_description>] [-p <parent_issue>]
```

### Arguments

- `-i, --input-file`: Path to the CSV file containing the records (required)
- `-t, --issue-type`: Type of issue to create. Must be either `new` or `update` (required)
- `-f, --format`: CSV file format. Options are `bulk` (default) or `api`
- `-a, --append-description`: Additional description to append to the issue body for update issues (optional)
- `-p, --parent-issue`: Parent issue number to add created issues as sub-issues (optional)

### Examples

**Create new issues from bulk format CSV:**
```bash
python create_issues_from_file.py -i new_records.csv -t new
```

**Create new issues from API format CSV:**
```bash
python create_issues_from_file.py -i new_records_api.csv -t new -f api
```

**Create update issues with additional description:**
```bash
python create_issues_from_file.py -i update_records.csv -t update -a "Requested by XYZ"
```

**Create issues as sub-issues of a parent issue:**
```bash
python create_issues_from_file.py -i new_records.csv -t new -p 23636
```

The script will read the CSV file and create issues in the ror-community/ror-updates repository based on the provided records and issue type. When a parent issue number is provided using `-p`, each created issue will be automatically added as a sub-issue to the specified parent issue.