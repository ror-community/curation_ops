# Create issues

Command-line tool to create new ROR record issues or update existing ROR record issues in the ror-community/ror-updates repository.

## Installation

```
pip install -r requirements.txt
```

## Setup

1. Set a `GITHUB_TOKEN` environment variable with a valid GitHub access token with permissions for ror-updates.

## Usage

```
python create_issues.py [-n | -u]
```

- `-n, --new`: Create a new ROR record issue.
- `-u, --update`: Update an existing ROR record issue.

The script will prompt for necessary information based on the selected option.