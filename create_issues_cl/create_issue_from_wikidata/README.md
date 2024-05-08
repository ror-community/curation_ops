# Create GitHub Issues from Wikidata

Create issues in the ror-updates repository from a Wikidata ID.

## Setup

1. Set a `GITHUB_TOKEN` environment variable with a valid GitHub access token that has permissions for ror-updates.

## Installation

```
pip install -r requirements.txt
```

## Usage

```
python create_issues_from_wikidata.py -w <wikidata_id>
```

- `-w`, `--wikidata_id`: Wikidata ID of the organization (required)
