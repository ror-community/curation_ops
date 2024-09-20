# Create Relationships

Extracts relationships [ror-updates](https://github.com/ror-community/ror-updates) to create a relationship file for use with the create relationships action.


## Installation

Set up your GitHub token as an environment variable:
   ```
   export GITHUB_TOKEN=your_github_token_here
   ```

Install the required packages:
   ```
   pip install -r requirements.txt
   ```


## Usage
```
python create_relationships.py -i input_file.csv
```

### Arguments

- `-r`, `--repo`: GitHub repository name (default: "ror-community/ror-updates")
- `-p`, `--project_number`: GitHub project number (default: 19, ROR Updates project)
- `-c`, `--column_name`: Project column name where records are located (default: "Ready for production release")
- `-i`, `--input_file`: Input CSV file with ROR data (required)
- `-o`, `--output_file`: Output CSV file for relationships (default: 'relationships.csv')

## Output

Generates a relationships CSV file containing the following information for each entry:

- Issue number from GitHub
- Issue URL
- Issue title from GitHub
- Name of organization in Record ID
- Record ID
- Related ID
- Name of organization in Related ID
- Relationship of Related ID to Record ID
- Current location of Related ID

