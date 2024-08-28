import csv
import json
import argparse
import logging
from furl import furl
from multiprocessing import Pool, cpu_count
import numpy as np
import traceback

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Normalize and match URLs from CSV and JSON files.")
    parser.add_argument('-i', '--input_file', required=True,
                        help="Path to the input CSV file.")
    parser.add_argument('-d', '--data_dump', required=True,
                        help="Path to the input JSON file.")
    parser.add_argument('-o', '--output_file', default="matched_urls.csv",
                        help="Path to the output file for matched results.")
    return parser.parse_args()


def read_csv(filepath):
    try:
        with open(filepath, mode='r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        return rows
    except Exception as e:
        logger.error(f"Failed to read CSV file from {filepath}: {e}")
        raise


def read_json(filepath):
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"Failed to read JSON file from {filepath}: {e}")
        raise


def normalize_url_furl(url, context=None):
    if url is None:
        logger.warning(f"Received None URL for normalization. Context: {context}")
        return None
    try:
        f = furl(url)
        # Remove URL path, query parameters, and fragments
        f.path.normalize()
        f.path = ''
        f.remove(args=True, fragment=True)
        if f.host.startswith('www.'):
            f.host = f.host[4:]
        # Remove scheme (http:// or https://)
        f.scheme = None
        return f.url.lower()
    except AttributeError as e:
        logger.error(f"AttributeError in normalize_url_furl: {e}. URL: {url}, Context: {context}")
        return None
    except Exception as e:
        logger.error(f"Error in normalize_url_furl: {e}. URL: {url}, Context: {context}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None


def get_ror_display_name(record):
    return [name['value'] for name in record.get('names', []) if 'ror_display' in name.get('types', [])][0]


def preprocess_json_data(json_data):
    processed_data = []
    for i, record in enumerate(json_data):
        json_url = next((link['value'] for link in record.get(
            'links', []) if link['type'] == 'website'), None)
        if json_url:
            normalized_url = normalize_url_furl(json_url, context=f"JSON record {i}, ROR ID: {record.get('id', 'Unknown')}")
            if normalized_url:
                processed_data.append({
                    'normalized_url': normalized_url,
                    'ror_id': record['id'],
                    'record_name': get_ror_display_name(record)
                })
            else:
                logger.warning(f"Skipping JSON record {i} due to normalization failure. ROR ID: {record.get('id', 'Unknown')}")
    return processed_data


def create_url_dict(processed_json_data):
    url_dict = {}
    for record in processed_json_data:
        normalized_url = record['normalized_url']
        # Add entry without 'www'
        url_dict[normalized_url] = record
        # Add entry with 'www' if not already present
        if not normalized_url.startswith('www.'):
            url_dict[f'www.{normalized_url}'] = record
    return url_dict


def match_urls(csv_data, url_dict):
    matched_records = []
    for i, csv_row in enumerate(csv_data):
        csv_url = csv_row.get('links.type.website')
        if csv_url:
            csv_normalized_url = normalize_url_furl(csv_url, context=f"CSV row {i}, ID: {csv_row.get('id', 'Unknown')}")
            if csv_normalized_url is None:
                logger.error(f"Normalization failed for CSV row {i}. ID: {csv_row.get('id', 'Unknown')}, URL: {csv_url}")
                logger.error(
                    "Stopping further processing due to normalization failure.")
                return None  # Return None to indicate failure
            if csv_normalized_url in url_dict:
                json_record = url_dict[csv_normalized_url]
                matched_records.append({
                    'csv_id': csv_row['id'],
                    'ror_id': json_record['ror_id'],
                    'record_name': json_record['record_name']
                })
        else:
            logger.warning(f"No URL found for CSV row {i}. ID: {csv_row.get('id', 'Unknown')}")
    return matched_records


def parallel_match_urls(csv_data, url_dict):
    with Pool(cpu_count()) as p:
        results = p.starmap(match_urls, [(csv_chunk, url_dict)
                                         for csv_chunk in np.array_split(csv_data, cpu_count())])
    # Check if any chunk failed (returned None)
    if any(result is None for result in results):
        logger.error(
            "URL matching failed in one or more processes. Stopping further processing.")
        return None
    return [item for sublist in results for item in sublist]


def report_matches(matched_data, output_file_filepath):
    try:
        with open(output_file_filepath, 'w', newline='') as csvfile:
            fieldnames = ['csv_id', 'ror_id', 'record_name']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for match in matched_data:
                writer.writerow(match)
        logger.info(f"Matched data written to {output_file_filepath}")
    except Exception as e:
        logger.error(f"Failed to write match data: {e}")
        raise


def main():
    args = parse_args()
    logger.info("Reading CSV data...")
    csv_data = read_csv(args.input_file)
    logger.info("Reading JSON data...")
    json_data = read_json(args.data_dump)
    logger.info("Preprocessing JSON data...")
    processed_json_data = preprocess_json_data(json_data)
    logger.info("Creating URL dictionary...")
    url_dict = create_url_dict(processed_json_data)
    logger.info("Matching URLs in parallel...")
    matched_data = parallel_match_urls(csv_data, url_dict)
    if matched_data is None:
        logger.error(
            "URL matching process failed. Exiting without writing output.")
        return
    logger.info("Reporting matches...")
    report_matches(matched_data, args.output_file)
    logger.info("Process completed successfully.")


if __name__ == "__main__":
    main()
