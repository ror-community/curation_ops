## Get Record Metadata

Extracts metadata from GitHub issues in the ror-updates project for new or updated ROR records.

## Setup
1. Set a `GITHUB_TOKEN` environment variable with a valid Github access token that has permissions for ror-updates.

## Installation
```
pip install -r requirements.txt
```

## Usage
```
python get_record_metadata.py -t [new|update] [-r REPO] [-p PROJECT_NUMBER] [-c COLUMN_NAME] [-f OUTPUT_FILE]
```

### Arguments
- `-t, --issue_type`: Type of issues to process (required, 'new' or 'update')
- `-r, --repo`: GitHub repository (default: "ror-community/ror-updates")
- `-p, --project_number`: GitHub project number (default: 19, ROR Updates project)
- `-c, --column_name`: Project column name (default: "Ready for sign-off / metadata QA")
- `-f, --output_file`: Output file path (default: based on issue type)
