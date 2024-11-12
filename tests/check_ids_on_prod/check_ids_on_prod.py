import os
import re
import csv
import json
import logging
import argparse
import requests
from multiprocessing import Pool

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', required=True,
                        help='Input directory containing JSON files')
    parser.add_argument('-o', '--output', required=True,
                        help='Output CSV file path')
    return parser.parse_args()


def find_json_files(input_dir):
    json_files = []
    logging.info(f"Searching for JSON files in: {input_dir}")
    if not os.path.exists(input_dir):
        logging.error(f"Input directory does not exist: {input_dir}")
        return json_files
    for root, dirs, files in os.walk(input_dir):
        logging.info(f"Checking directory: {root}")
        logging.info(f"Found files: {files}")
        for file in files:
            if file.endswith('.json'):
                json_files.append(os.path.join(root, file))   
    logging.info(f"Total JSON files found: {len(json_files)}")
    return json_files


def extract_ror_id_from_file(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
        return data.get('id')


def check_id_status(id):
    try:
        response = requests.get(f"https://api.ror.org/organizations/{id}")
        if 400 <= response.status_code < 500:
            return (id, '400 Range Error')
        elif 500 <= response.status_code < 600:
            return (id, '500 Range Error')
        elif response.status_code == 200:
            return (id, '200 Success')
        else:
            return (id, 'Other Error')
    except requests.RequestException:
        return (id, 'Request Failed')


def initialize_csv(output_file):
    with open(output_file, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['ID', 'Status'])


def log_result_to_csv(output_file, result):
    with open(output_file, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(result)


def execute_multiprocessing(ids, output_file, num_processes=4):
    initialize_csv(output_file)
    results = []
    with Pool(num_processes) as pool:
        results = pool.map(check_id_status, ids)
    for result in results:
        log_result_to_csv(output_file, result)
    non_400_ids = [(id, status)
                   for id, status in results if not '400 Range Error' in status]
    all_400_range_errors = all(
        '400 Range Error' in status for _, status in results)
    any_200_or_500_range_errors = any(
        '200 Success' in status or '500 Range Error' in status for _, status in results)
    return all_400_range_errors, any_200_or_500_range_errors, non_400_ids


def main():
    args = parse_arguments()
    json_files = find_json_files(args.input)
    if not json_files:
        logging.info("No JSON files in input directory")
        return
    ror_ids = [extract_ror_id_from_file(file) for file in json_files]
    ror_ids = [ror_id for ror_id in ror_ids if ror_id]
    if not ror_ids:
        logging.error("No ROR IDs found in JSON files for the input directory")
        return
    ror_id_pattern = re.compile(r'https?://ror\.org/[a-z0-9]{9}')
    all_ids_valid = all(ror_id_pattern.match(ror_id) for ror_id in ror_ids)
    if not all_ids_valid:
        logging.error("Invalid ROR ID(s) in JSON files for the input directory")
        return
    all_400_range_errors, any_200_or_500_range_errors, non_400_ids = execute_multiprocessing(
        ror_ids, args.output)
    if all_400_range_errors:
        logging.info("Success: All IDs returned 400 range errors.")
    elif any_200_or_500_range_errors:
        logging.error(
            "Failure: At least one ID returned a 200 or 500 range error.")
    if non_400_ids:
        logging.info("IDs with status other than 400 range errors:")
        for id, status in non_400_ids:
            logging.info(f"ID: {id}, Status: {status}")


if __name__ == "__main__":
    main()