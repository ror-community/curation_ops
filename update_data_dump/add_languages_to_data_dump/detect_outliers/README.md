# Language Outlier Detection

Detects language outliers in the CSV file returned from `detect_languages_in_data_dump.py` based on the distribution of languages within each country.


## Installation

```
pip install -r requirements.txt
```


## Usage
```
python detect_outliers.py -i <input_file> [-o <output_file>]
```

- `-i`, `--input_file`: Path to the input CSV file (required).
- `-o`, `--output_file`: Path to the output CSV file (default: 'detected_outliers.csv').


## Functionality

1. Reads the input CSV file containing language data per country.
2. Calculates the language distribution for each country.
3. Detects language outliers based on the following criteria:
   - If a language count is outside the interquartile range (IQR) of the country's language counts.
   - If a language is not the dominant language (>90%) and has a count below a minimum threshold.
   - If a language is not among the significant languages (>30%) when multiple significant languages are present.
4. Adds an 'outlier' column to each row indicating whether the language is an outlier ('TRUE') or not ('FALSE').
5. Writes the updated data to the output CSV file.


## Output
The script generates an output CSV file with an additional 'outlier' column indicating the outlier status of each language entry.