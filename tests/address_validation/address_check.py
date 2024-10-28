import csv
import argparse
import requests
import logging
from pathlib import Path


def setup_logging(verbose, log_file='address_check.log'):
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def query_geonames_api(geonames_id, username):
    api_url = "http://api.geonames.org/getJSON"
    params = {
        'geonameId': geonames_id,
        'username': username
    }
    try:
        logging.debug(f"Querying GeoNames API for ID: {geonames_id}")
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        name = data.get("name", "")
        country = data.get("countryName", "")
        if name and country:
            logging.debug(f"Successfully retrieved data: {name}, {country}")
        else:
            logging.warning(f"Incomplete data received for ID {geonames_id}")
        return name, country
    except requests.exceptions.RequestException as e:
        logging.error(f"API request failed for ID {geonames_id}: {str(e)}")
        return "", ""


def validate_city_country(record, api_data):
    matches = record["city"] == api_data[0] and record["country"] == api_data[1]
    if matches:
        logging.debug(f"Match found for {record['names.types.ror_display']}: {record['city']}, {record['country']}")
    else:
        logging.info(f"Discrepancy found for {record['names.types.ror_display']}: CSV: {record['city']}, {record['country']} | API: {api_data[0]}, {api_data[1]}")
    return matches


def process_records(input_file, output_file, api_user):
    record_count = 0
    discrepancy_count = 0
    fieldnames = ["names.types.ror_display", "locations.geonames_id", "csv_city", "csv_country", "api_city", "api_country"]
    
    try:
        with open(input_file, 'r') as f_in, open(output_file, 'w', newline='') as f_out:
            reader = csv.DictReader(f_in)
            writer = csv.DictWriter(f_out, fieldnames=fieldnames)
            writer.writeheader()
            
            logging.info(f"Processing input file: {input_file}")
            for row in reader:
                record_count += 1
                logging.debug(f"Processing record {record_count}: {row['names.types.ror_display']}")
                
                api_city_country = query_geonames_api(row['locations.geonames_id'], api_user)
                
                if not validate_city_country(row, api_city_country):
                    discrepancy_count += 1
                    writer.writerow({
                        "names.types.ror_display": row["names.types.ror_display"],
                        "locations.geonames_id": row["locations.geonames_id"],
                        "csv_city": row["city"],
                        "csv_country": row["country"],
                        "api_city": api_city_country[0],
                        "api_country": api_city_country[1]
                    })
                    
            logging.info(f"Processed {record_count} records, found {discrepancy_count} discrepancies")
            return discrepancy_count
            
    except IOError as e:
        logging.error(f"File operation failed: {str(e)}")
        raise


def arg_parse():
    parser = argparse.ArgumentParser(description="Validate city and country data against GeoNames API")
    parser.add_argument("-i", "--input_file", type=str, required=True, help="Input CSV file path")
    parser.add_argument("-u", "--api_user", type=str, required=True, help="GeoNames API username")
    parser.add_argument("-o", "--output_file", type=str, default='address_discrepancies.csv', help="Output CSV file path (default: address_discrepancies.csv)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("-l", "--log_file", type=str, default='address_check.log', help="Log file path (default: address_check.log)")
    return parser.parse_args()


def main():
    args = arg_parse()
    setup_logging(args.verbose, args.log_file)
    try:
        logging.info("Starting address check process")
        if not Path(args.input_file).exists():
            logging.error(f"Input file not found: {args.input_file}")
            return 1
            
        process_records(args.input_file, args.output_file, args.api_user)
        logging.info("Address check process completed successfully")
        return 0
    except Exception as e:
        logging.error(f"Unexpected error occurred: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())