# Infer acronym languages from data dump

Infers the languages of acronyms from a ROR data dump based on the language assignments of aliases and labels and outputs the results to CSV files.

## Installation

```
pip install -r requirements.txt
```

## Usage

```
python infer_acronym_langs_from_data_dump.py -i INPUT_JSON [-o OUTPUT_CSV] [-u UNMATCHED_CSV]
```

- `-i`, `--input`: Path to the input JSON file (required)
- `-o`, `--output`: Path to the output CSV file (default: 'inferred_acronyms_w_langs.csv')
- `-u`, `--unmatched`: Path to the unmatched acronyms CSV file (default: 'unmatched_acronyms.csv')

## Note

The script assumes the input data dump is that for the v2 version of ROR's scema.