# Automated Triage

Automates the triaging process for new organization requests and updates to the Research Organization Registry (ROR).

## Functionality

- Fetches open GitHub issues with "triage needed" label from ror-community/ror-updates repository
- Processes new organization requests and update requests separately
- For new organizations:
  - Searches Wikidata, ISNI, Crossref Funder Registry, and other databases
  - Generates potential aliases using OpenAI's GPT model
  - Checks for publication affiliation usage in OpenAlex
  - Searches for ORCID affiliation usage
  - Looks for possible matches in existing ROR records
  - Checks for previous similar requests
  - Searches Geonames for location data
- For updates:
  - Encodes the requested changes into a specific update format
  - Validates the encoded update
- Posts triage results as comments on the respective GitHub issues

Additional scripts provide supporting functionality:
- validate_encoding.py: Validates the format of encoded updates
- encode_updates.py: Encodes update requests into a specific format
- generate_aliases.py: Generates potential aliases for organizations
- search_geonames.py: Searches Geonames for location data
- detect_language.py: Detects the language of organization names

## Output Formats

### New Organization Requests

For each new organization request, the script generates a comment on the issue with the following information:

- Wikidata: Name, ID, and match ratio (if found)
- ISNI: Matched ID(s) and name(s)
- Funder ID: Crossref Funder Registry ID (if found)
- Publication affiliation usage: OpenAlex search results
- ORCID affiliation usage: Links to ORCID profiles
- Possible ROR matches: Existing ROR IDs and names
- Previous requests: Links to similar GitHub issues
- Geonames match: Name and ID of matched location

### Update Requests

For update requests, the script generates an encoded update string in the following format:

```
Update: field1.operation==value1 | field2.operation==value2 | ...$
```

Where:
- `field` is the name of the field to be updated
- `operation` is one of: add, delete, or replace
- `value` is the new or modified data
- Fields are separated by `|`
- The update string is terminated with `$`

Example:
```
Update: ror_display.replace==New Organization Name | alias.add==Old Organization Name | isni.add==0000 0001 2345 6789$
```

This encoded update is posted as a comment on the GitHub issue for review.


## Installation

```
pip install -r requirements.txt
```

## Usage

Set the required environment variables (GITHUB_TOKEN, OPENAI_API_KEY) and run:

```
python triage_issues.py
```

