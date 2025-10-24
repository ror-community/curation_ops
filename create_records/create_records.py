import os
import csv
import json
import argparse
import requests
import tempfile
import shutil
import zipfile
from time import sleep
from datetime import datetime
from pathlib import Path



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


def split_csv_into_batches(input_file, batch_size, temp_dir):
    batch_files = []

    with open(input_file, 'r', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        header = next(reader)

        batch_num = 1
        batch_rows = []

        for row in reader:
            batch_rows.append(row)

            if len(batch_rows) >= batch_size:
                batch_file = os.path.join(temp_dir, f'batch_{batch_num:03d}.csv')
                write_batch_file(batch_file, header, batch_rows)
                batch_files.append(batch_file)
                batch_num += 1
                batch_rows = []

        # Write remaining rows if any
        if batch_rows:
            batch_file = os.path.join(temp_dir, f'batch_{batch_num:03d}.csv')
            write_batch_file(batch_file, header, batch_rows)
            batch_files.append(batch_file)

    return batch_files


def write_batch_file(file_path, header, rows):
    with open(file_path, 'w', encoding='utf-8', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(header)
        writer.writerows(rows)


def unzip_file(zip_path, extract_to):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    return extract_to


def find_record_type_folder(extracted_dir):
    for item in os.listdir(extracted_dir):
        item_path = os.path.join(extracted_dir, item)
        if os.path.isdir(item_path):
            for subitem in os.listdir(item_path):
                subitem_path = os.path.join(item_path, subitem)
                if os.path.isdir(subitem_path):
                    if subitem == 'new_records':
                        return subitem_path, 'new_records'
                    elif subitem == 'updates':
                        return subitem_path, 'updates'
    return None, None


def combine_json_files(source_folders, output_dir, record_type):
    combined_folder = os.path.join(output_dir, f'combined_{record_type}')
    os.makedirs(combined_folder, exist_ok=True)

    json_count = 0
    for folder in source_folders:
        if not os.path.exists(folder):
            continue

        for filename in os.listdir(folder):
            if filename.endswith('.json'):
                src = os.path.join(folder, filename)
                dst = os.path.join(combined_folder, filename)
                shutil.copy2(src, dst)
                json_count += 1

    return combined_folder, json_count


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


def process_split_batches(api_user, api_token, input_file, batch_size, output_dir, validate):
    temp_dir = tempfile.mkdtemp(prefix='ror_batch_')
    batches_dir = os.path.join(output_dir, 'batches')
    logs_dir = os.path.join(output_dir, 'logs')
    os.makedirs(batches_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)

    try:
        print(f"Splitting {input_file} into batches of {batch_size} rows...")
        batch_files = split_csv_into_batches(input_file, batch_size, temp_dir)
        total_batches = len(batch_files)
        print(f"Created {total_batches} batch(es)\n")

        batch_zip_files = []

        print("\nProcessing batches through API...\n")
        for idx, batch_file in enumerate(batch_files, 1):
            print(f"\nProcessing batch {idx}/{total_batches}: {os.path.basename(batch_file)}")

            batch_output_dir = tempfile.mkdtemp(prefix=f'batch_{idx:03d}_output_')

            process_single_file(api_user, api_token, batch_file, batch_output_dir, validate)

            for item in os.listdir(batch_output_dir):
                if item.endswith('.zip'):
                    zip_path = os.path.join(batch_output_dir, item)
                    batch_zip_dest = os.path.join(batches_dir, f"batch_{idx:03d}_{item}")
                    shutil.move(zip_path, batch_zip_dest)
                    batch_zip_files.append((idx, batch_zip_dest))
                    print(f"  Downloaded: {os.path.basename(batch_zip_dest)}")

            shutil.rmtree(batch_output_dir)
            if idx < total_batches:
                sleep(5)
        print("\nUnzipping and organizing results...\n")

        record_folders = []
        record_type = None

        for idx, zip_file in batch_zip_files:
            print(f"\nUnzipping batch {idx}/{total_batches}...")
            extract_dir = os.path.join(batches_dir, f"batch_{idx:03d}_extracted")
            unzip_file(zip_file, extract_dir)

            folder_path, detected_type = find_record_type_folder(extract_dir)
            if folder_path:
                record_folders.append(folder_path)
                if record_type is None:
                    record_type = detected_type
                    print(f"  Detected record type: {record_type}")
                elif record_type != detected_type:
                    print(f"  Warning: Mixed record types detected ({record_type} vs {detected_type})")

            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file == 'report.csv':
                        src = os.path.join(root, file)
                        dst = os.path.join(logs_dir, f"batch_{idx:03d}_report.csv")
                        shutil.copy2(src, dst)
                        print(f"  Copied report to logs/")

        if record_folders and record_type:
            print("\nCombining JSON records...\n")
            print(f"Combining {len(record_folders)} batch(es) of {record_type}...")
            combined_folder, json_count = combine_json_files(record_folders, output_dir, record_type)
            print(f"Combined {json_count} JSON files into: {combined_folder}")

        print("\nCOMPLETE: All batches processed successfully\n")
        print(f"Output directory: {output_dir}")
        print(f"  - batches/: Individual batch zip files and extracted contents")
        print(f"  - logs/: Report CSV files for each batch")
        if record_type:
            print(f"  - combined_{record_type}/: All {json_count} JSON records merged")

    finally:
        print(f"\nCleaning up temporary files...")
        shutil.rmtree(temp_dir)
        print("Temporary files removed.")


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
    parser.add_argument('-s', '--batch_size', type=int,
                        help='Number of rows per batch when splitting a single input file')
    return parser.parse_args()


def main():
    try:
        args = parse_arguments()
        api_user, api_token = read_environment_variables()
        os.makedirs(args.output_dir, exist_ok=True)

        if args.batch:
            process_batch(api_user, api_token, args.batch,
                          args.output_dir, args.validate)
        elif args.batch_size:
            if not args.input_file:
                raise ValueError("--batch_size requires --input_file to be specified")
            process_split_batches(api_user, api_token, args.input_file,
                                args.batch_size, args.output_dir, args.validate)
        else:
            process_single_file(api_user, api_token,
                                args.input_file, args.output_dir, args.validate)
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == '__main__':
    main()
