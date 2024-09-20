# Detect languages in data dump

Processes a ROR data dump file, detects the language of each name using the `detect_language` function, and writes the results to a CSV file.

## Setup

- Download FastText's pre-trained language model (`lid.176.bin`), from [FastText's website](https://fasttext.cc/docs/en/language-identification.html) and add to the script directory
- Create a CSV file containing the most common languages in the last data dump using `get_most_common_languages.py`


## Installation

```
pip install -r requirements.txt
```

## Usage

```
python detect_languages_in_data_dump.py -i <input_file> -l <language_file> [-o <output_file>]
```

- `-i`, `--input`: Path to the data dump file (required)
- `-l`, `--language_file`: Path to the input JSON file containing common languages (required)
- `-o`, `--output`: Path to the output CSV file (default: 'tagged_languages.csv')

## Output

The script generates a CSV file with the following columns:

- `id`: Record ID
- `name`: Name value
- `lang`: Detected language of the name
- `country_code`: Country code from the record's location