# Map v1 IDs to v2 files

Maps ROR IDs from v1 JSON files to v2 JSON files based on matching name, website link, and geonames city ID.

## Usage

```
python map_v1_ids_to_v2_records.py -v1 <v1_directory> -v2 <v2_directory> [-o <output_directory>]
```

- `-v1, --v1_directory`: Directory containing v1 JSON files (required)
- `-v2, --v2_directory`: Directory containing v2 JSON files (required)
- `-o, --output_directory`: Directory to save mapped JSON files (default: 'mapped_files')

## Functionality

1. Reads v1 and v2 JSON files from specified directories.
2. Maps v1 IDs to v2 records based on matching name, website link, and geonames city ID.
3. Saves mapped JSON files to the output directory.
4. Logs any failed mappings to the console.
