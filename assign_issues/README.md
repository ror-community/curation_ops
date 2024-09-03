# GitHub Issue Assignment Script

Assigns GitHub issues to a specific user in a given repository, using a CSV file as input.

## Installation

```
pip install -r requirements.txt
```

## Setup

1. Set a `GITHUB_TOKEN` environment variable with a valid GitHub access token that has permissions for the target repository.

## Usage

```
python github_issue_assigner.py --input INPUT_CSV --assignee GITHUB_USERNAME [--token GITHUB_TOKEN] [--repo OWNER/REPO]
```

### Arguments:

- `--input`: Path to the input CSV file (required)
- `--assignee`: GitHub username of the assignee (required)
- `--token`: GitHub Personal Access Token (optional, defaults to GITHUB_TOKEN environment variable)
- `--repo`: GitHub repository in the format "owner/repo" (optional, default: "ror-community/ror-updates")

### Input CSV Format:

The input CSV file should have the following structure:

```
issue
https://github.com/owner/repo/issues/{issue_number}
```

## Example

To assign issues from `issues.csv` to the user `curator1` in the `ror-community/ror-updates` repository:

```
python github_issue_assigner.py --input issues.csv --assignee curator1
```

## Notes

- The script will clear existing assignees before assigning the specified user.