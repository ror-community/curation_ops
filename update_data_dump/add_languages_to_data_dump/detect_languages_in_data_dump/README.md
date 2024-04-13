# Detect languages in data dump

Processes a ROR data dump file, detects the language of each name using the `detect_language` function, and writes the results to a CSV file.


## Requirements
- `fasttext` library
- `lingua-language-detection` library
- FastText's pre-trained language model (`lid.176.bin`), downloadable from [FastText's website](https://fasttext.cc/docs/en/language-identification.html)


## Installation

```
pip install -r requirements.txt
```


## Usage

```
python detect_languages_in_data_dump.py -i <input_file> [-o <output_file>]
```

- `-i`, `--input`: Path to the data dump file (required)
- `-o`, `--output`: Path to the output CSV file (default: 'tagged_languages.csv')


## Output

The script generates a CSV file with the following columns:
- `id`: Record ID
- `name`: Name value
- `lang`: Detected language of the name
- `country_code`: Country code from the record's location

