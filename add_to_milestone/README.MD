# add_to_milestone.py

Adds issues from a specific project column to a milestone in a GitHub repository.

## Installation

```
pip install -r requirements.txt
```

## Setup

1. Set a `GITHUB_TOKEN` environment variable with a valid GitHub access token with appropriate permissions for the target repository.

## Usage

```
python add_to_milestone.py -m <milestone_number> [options]
```

### Required Arguments:

- `-m, --milestone`: An integer representing the milestone number to add issues to.

### Optional Arguments:

- `-r, --repo`: GitHub repository name in the format owner/repo (default is "ror-community/ror-updates")
- `-p, --project_number`: GitHub project number (default is 19, which is the ror-updates project)
- `-c, --column_name`: Project column name where issues are located (default is "Ready for production release")
