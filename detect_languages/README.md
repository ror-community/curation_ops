#### Overview
Detects languages in new and update record CSVs.

#### Requirements
- `fasttext` library
- `lingua-language-detection` library
- FastText's pre-trained language model (`lid.176.bin`), downloadable from [FastText's website](https://fasttext.cc/docs/en/language-identification.html)

#### Installation
   ```bash
   pip install -r requirements.txt
   ```

3. Download `lid.176.bin` from the provided link and place it in a folder named `model` within the script's directory.

#### Usage

    ```bash
    python detect_languages.py --input [CSV_FILE_PATH] --output [OUTPUT_FILE_PATH] --file-type [FILE_TYPE] --high-precision [TRUE/FALSE]
    ```

  - Parameters:
    - `--input [CSV_FILE_PATH]`: Path to the input CSV file (required).
    - `--output [OUTPUT_FILE_PATH]`: Path to the output CSV file. Default is 'detected_languages.csv'.
    - `--file-type [FILE_TYPE]`: Type of the input file, choices are 'new' or 'updates' (required).
    - `--high-precision [TRUE/FALSE]`: Use high precision language detection. Default is True.
