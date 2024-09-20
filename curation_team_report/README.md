# Curation Team Report

Generate reports on GitHub issues in specific project columns in the [ror-updates project](https://github.com/orgs/ror-community/projects/19) for the ROR curation team.

## Installation

```
pip install -r requirements.txt
```

## Setup

Set the `GITHUB_TOKEN` environment variable with a valid GitHub access token.

## Usage

```
python curation_team_report.py [-o ORG] [-p PROJECT] [-c COLUMNS] [-f OUTPUT]
```

Options:
- `-o, --organization`: GitHub organization (default: "ror-community")
- `-p, --project`: GitHub project name (default: "Curation tracker 2024 - DRAFT")
- `-c, --columns`: Comma-separated list of column names to report on
- `-f, --output`: Output directory for CSV reports (default: current directory)

## Output

Generates CSV files for each specified column, containing issue details. Default columns extracted are "Needs Discussion" and "Second Review".