import os
import argparse
import requests


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


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Bulk update script for ROR API')
    parser.add_argument('-i', '--input_file', type=str,
                        required=True, help='Path to the CSV file')
    parser.add_argument('-o', '--output_file', type=str,
                        default='report.csv', help='Output file path')
    parser.add_argument('-v', '--validate', action='store_true',
                        help='Validate the bulk update')
    return parser.parse_args()


def main():
    try:
        args = parse_arguments()
        api_user, api_token = read_environment_variables()
        response = make_api_request(
            api_user, api_token, args.input_file, args.validate)
        if args.validate:
            write_output(args.output_file, response.text)
            print(f"Validation response written to {args.output_file}")
        else:
            response_json = response.json()
            file_url = response_json['file']
            file_name = os.path.basename(file_url)
            download_file(file_url, file_name)
            print(f"File downloaded: {file_name}")

    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == '__main__':
    main()
