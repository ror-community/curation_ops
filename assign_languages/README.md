# assign_languages.py

This script updates a GitHub issue with assigned languages for the organization name and aliases.


## Installation
   ```
   pip install -r requirements.txt
   ```
[Download the fasttext language detection binary from the fasttext site](https://fasttext.cc/docs/en/language-identification.html) and include in the script directory.

## Usage
```
python assign_languages.py -i ISSUE_NUMBER [-r REPO_NAME]
```
- `-i`, `--issue_number`: GitHub issue number (required)
- `-r`, `--repo_name`: GitHub repository name (default: 'ror-community/ror-updates')


## Note

The script assumes a ror-updates new issue format for the issue body, with the organization name and aliases following the patterns:
- `Name of organization: <name>`
- `Aliases: <alias1>; <alias2>; ...`

Make sure the issue body follows this format for the script to work correctly.