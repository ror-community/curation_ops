# add_to_milestone.py

Adds issues in the 'Ready for production release' column of the ror-updates project to a specified milestone.

## Installation

```
pip install -r requirements.txt`
```

## Setup

1. Set a `GITHUB_TOKEN` environment variable with a valid Github access token with permissions for ror-updates.

## Usage

```
python add_to_milestone.py <milestone_number>
```

- `-m, --milestone_number`: (Required) An integer representing the milestone number to add issues to.

