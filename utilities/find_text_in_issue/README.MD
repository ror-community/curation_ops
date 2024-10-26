# Find text in issue

Tool for searching GitHub issues and their comments in repos, primarily used to identify text in ror-updates issues, in combination with an additional filtering script for new record relationships.

## Installation

```bash
pip install -r requirements.txt
```

## Setup

1. Set a `GITHUB_TOKEN` environment variable with a valid GitHub access token with appropriate permissions.

## Primary Script

### find_text_in_issue.py

Searches GitHub issues and their comments for specified text strings. Takes a CSV of issue URLs and ROR IDs as input (release input file), and outputs matches to CSV with full issue details.

```bash
python find_text_in_issue.py -i <input_csv> -s <search_string> [options]
```

#### Required Arguments:
- `-i, --input_csv`: Path to input CSV file containing GitHub issue numbers and ROR IDs
- `-s, --search_string`: String to search for within issue bodies and comments

#### Optional Arguments:
- `-o, --output_csv`: Output CSV file path (default: 'matches_in_issue_body.csv')
- `-r, --repo`: GitHub repository name (default: "ror-community/ror-updates")

## Additional Filtering

### find_new_records_relationships.py

A companion script for filtering search results to find new record relationships. Processes output from `find_text_in_issue_no_column.py` to identify issues with '#' references in "Related organizations" sections.

```bash
python find_new_records_relationships.py -i <input_csv> [-o output.csv] [-v]
```