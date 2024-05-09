# Create Issues from Funder ID

Create issues in the ror-updates repository from a Crossref Funder ID.

## Setup

1. Set a `GITHUB_TOKEN` environment variable with a valid GitHub access token that has permissions for ror-updates.

## Installation

```
pip install -r requirements.txt
```

## Usage

```
python create_issue_from_funder_id.py -i <funder_id>
```

- `-i`, `--funder_id`: Crossref Funder ID of the organization (required)