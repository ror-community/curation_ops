import os
import csv
import argparse
import requests
from time import sleep
from datetime import datetime



def read_environment_variables():
    api_user = os.environ.get('GENERATE_API_USER')
    api_token = os.environ.get('GENERATE_API_TOKEN')
    if not api_user or not api_token:
        raise ValueError(
            'Missing environment variables: GENERATE_API_USER or GENERATE_API_TOKEN')
    return api_user, api_token


def make_api_request(api_user, api_token, input_file, validate):
    url = 'https://api.ror.org/v2/bulkupdate'
    headers = {
        'Route-User': api_user,
        'Token': api_token
    }
    files = {
        'file': open(input_file, 'rb')
    }
    params = {}
    if validate:
        params['validate'] = True
    try:
        response = requests.post(url, headers=headers,
                                 files=files, params=params)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise SystemExit(f"An error occurred: {e}")
    return response


def write_output(output_file, response_data):
    try:
        with open(output_file, 'w') as file:
            file.write(response_data)
    except IOError as e:
        raise SystemExit(f"An error occurred while writing the output file: {e}")


def download_file(url, output_file):
    try:
        response = requests.get(url)
        response.raise_for_status()
        with open(output_file, 'wb') as file:
            file.write(response.content)
    except requests.exceptions.RequestException as e:
        raise SystemExit(f"An error occurred while downloading the file: {e}")
    except IOError as e:
        raise SystemExit(f"An error occurred while saving the downloaded file: {e}")


def parse_directory(directory_path):
    csv_files = []
    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.lower().endswith('.csv'):
                csv_files.append(os.path.join(root, file))
    return csv_files


def process_single_file(api_user, api_token, input_file, output_dir, validate):
    response = make_api_request(api_user, api_token, input_file, validate)
    if validate:
        output_file = os.path.join(output_dir, f"validation_{os.path.basename(input_file)}")
        write_output(output_file, response.text)
        print(f"Validation response written to {output_file}")
    else:
        response_json = response.json()
        file_url = response_json['file']
        file_name = os.path.basename(file_url)
        output_file = os.path.join(output_dir, file_name)
        download_file(file_url, output_file)
        print(f"File downloaded: {output_file}")


def process_batch(api_user, api_token, directory_path, output_dir, validate):
    csv_files = parse_directory(directory_path)
    for csv_file in csv_files:
        print(f"Processing file: {csv_file}")
        process_single_file(api_user, api_token, csv_file,
                            output_dir, validate)
        sleep(5)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Bulk update script for ROR API')
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('-i', '--input_file',
                             type=str, help='Path to the CSV file')
    input_group.add_argument('-b', '--batch', type=str,
                             help='Path to the directory containing CSV files')
    parser.add_argument('-o', '--output_dir', type=str, default=f'batch_{datetime.now().strftime("%Y%m%d_%H%M%S")}', help='Output directory path')
    parser.add_argument('-v', '--validate', action='store_true',
                        help='Validate the bulk update')
    return parser.parse_args()


def main():
    try:
        args = parse_arguments()
        api_user, api_token = read_environment_variables()
        os.makedirs(args.output_dir, exist_ok=True)
        if args.batch:
            process_batch(api_user, api_token, args.batch,
                          args.output_dir, args.validate)
        else:
            process_single_file(api_user, api_token,
                                args.input_file, args.output_dir, args.validate)
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == '__main__':
    main()
