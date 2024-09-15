# Create Release Notes

Script for generatin release notes.

## Installation

```
pip install -r requirements.txt
```


## Usage

```
python ror_release_script.py -r <release_number> -m <milestone_number> -d <directory_path> [options]
```

### Required Arguments:

- `-r, --release`: The release number (e.g., "v1.XX")
- `-m, --milestone`: The milestone number for the GitHub issues
- `-d, --directory`: Path to the release directory containing "new" and "updates" subdirectories with JSON files

### Optional Arguments:

- `-o, --output`: Output file name (default is "release_notes.md")
- `-p, --print`: Flag to print output to console instead of writing to a file


## Output

The script generates a markdown file (or prints to console) containing:

- Total number of organizations
- Number of records added
- Number of records updated
- Lists of added and updated records with their ROR IDs and names

