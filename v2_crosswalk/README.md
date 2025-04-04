# V2 Crosswalk
Script to generate ROR record files or data dump in another schema version.

## Usage

### Convert individual records
1. Run the script with the input and output paths specified in the `-i` and `-o` arguments and the output schema version specified in the `-v` argument. Input schema version is expected to be the opposite of the specified output schema version, ex if `-v 2` is passed, input files should be in v1.Input path should be a directory that contains 1 or more ROR records as individual JSON files.

        python crosswalk.py -i ./path/to/v1/files -o ./path/to/v2/files -v 2

2. v2 files are created in the output path location with the same filename as the v1 file.

### Convert data dump
1. Run the script with the path to the data dump zip file specified in the `-f` argument, the input and output paths specified in the `-i` and `-o` arguments, and the output schema version specified in the `-v` argument. Input schema version is expected to be the opposite of the specified output schema version, ex if `-v 2` is passed, input files should be in v1.

        python crosswalk.py  -i ./path/to/v1/files -o ./path/to/v2/files -f ./V1_INPUT/v1.32-2023-09-14-ror-data.zip -v 2

2. v2 data dump JSON file is created in the output path location with `_schema_v2` appended to the v1 filename. A zip file is not created because additional steps, such as updating created and last modified dates and generated a CSV version, are needed before packaging up the release.

### Update created/last modified dates (data dump only)
Running the conversion script above does not automatically add created and last modified dates to v2 records. To

1. Generate a CSV with created and last modified dates for each record in the data dump using https://github.com/ror-community/curation_ops/tree/main/created_last_modified

2. Run the `update_dates_v2.py` script with the v2 data dump JSON filepath specifed in the `-f` argument and the dates CSV filepath specified in the `-d` argument.

        python update_dates_v2.p -f ./V2_OUTPUT/v1.32-2023-09-14-ror-data_schema_v2.json -d ./V1_INPUT/20230914_created_last_modified.csv




