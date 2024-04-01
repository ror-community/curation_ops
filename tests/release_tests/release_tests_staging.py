import re
import csv
import json
import glob
import random
import requests
import jsondiff
import argparse


def get_ror_display_name(json_file):
    return next((name['value'] for name in json_file.get('names', []) if 'ror_display' in name.get('types', [])), None)


def retrieve_api(ror_id):
    api_url = f"https://api.staging.ror.org/v2/organizations/{ror_id}"
    r = requests.get(api_url)
    if r.status_code == 200:
        return "retrieved"
    return "failed"


def compare_api(ror_id, json_file):
    api_url = f"https://api.staging.ror.org/v2/organizations/{ror_id}"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        api_json = response.json()
        file_api_diff = jsondiff.diff(api_json, json_file, syntax='symmetric')
        if file_api_diff:
            return "different", file_api_diff
        return "same", None
    except requests.exceptions.RequestException as e:
        print(f"Error occurred while fetching data from API for ROR ID: {ror_id}")
        return "api_error", None


def search_name_api(org_name):
    api_url = 'https://api.staging.ror.org/v2/organizations'
    params = {
        'query': f'"{org_name}"',
        'all_status': 'True'
    }
    r = requests.get(api_url, params=params)
    results = r.json()["items"]
    for result in results:
        ror_display = get_ror_display_name(result)
        if ror_display == org_name:
            return "retrieved"
    return "failed"


def compare_random(compare_ids):
    random_ror_ids = []
    diff_response_ids = []
    for ror_id in compare_ids:
        api_url = f"https://api.ror.org/v2/organizations/{ror_id}"
        staging_api_url = f"https://api.staging.ror.org/v2/organizations/{ror_id}"
        print("Comparing staging and production for", ror_id, "...")
        prod_response = requests.get(api_url).json()
        staging_response = requests.get(staging_api_url).json()
        if prod_response != staging_response:
            diff_response_ids.append(ror_id)
        else:
            print("Staging matches production for", ror_id)
    return diff_response_ids


def check_release_files(release_directory, all_ror_ids_file, release_tests_outfile, jsondiff_outfile):
    if not os.path.exists(release_directory):
        print(f"Error: Release directory '{release_directory}' does not exist.")
        exit(1)

    with open(release_tests_outfile, 'w') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(["ror_id", "org_name", "retrieve_check",
                         "compare_check", "search_name_api_check"])
    with open(jsondiff_outfile, 'w') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(["ror_id", "diff"])
    ids_in_file = []
    json_files = glob.glob(os.path.join(release_directory, "*.json"))
    for file in json_files:
        with open(file, 'r+', encoding='utf8') as f_in:
            json_file = json.load(f_in)
        ids_in_file.append(json_file["id"])
        ror_id = re.sub('https://ror.org/', '', json_file["id"])
        org_name = get_ror_display_name(json_file)
        print("Testing -", org_name, "- ROR ID:", ror_id, "...")
        retrieve_check = retrieve_api(ror_id)
        compare_check, diff_json = compare_api(ror_id, json_file)
        if diff_json:
            with open(jsondiff_outfile, 'w') as f_out:
                writer = csv.writer(f_out)
                writer.writerow([ror_id, diff_json])
        search_name_api_check = search_name_api(
            org_name)
        with open(release_tests_outfile, 'a') as f_out:
            writer = csv.writer(f_out)
            writer.writerow([ror_id, org_name, retrieve_check,
                             compare_check, search_name_api_check])
    with open(all_ror_ids_file) as f_in:
        all_ror_ids = [line.strip()
                       for line in f_in if line.strip() not in ids_in_file]
        random_ids = random.sample(all_ror_ids, min(50, len(all_ror_ids)))
    compare_random_check = compare_random(random_ids)
    if compare_random_check:
        print("The following IDs have changed:", compare_random_check,
              "Investigate integrity of ROR dataset.")


def parse_arguments():
    parser = argparse.ArgumentParser(description='Run release tests for ROR')
    parser.add_argument('-r', '--release_directory', required=True,
                        help='Path to the directory containing JSON files')
    parser.add_argument('-a', '--all_ror_ids_file', default='all_ror_ids.txt',
                        help='Path to the release tests output file')
    parser.add_argument('-t', '--release_tests_outfile', default='release_tests.csv',
                        help='Path to the release tests output file')
    parser.add_argument('-j', '--jsondiff_outfile', default='jsondiff.csv',
                        help='Path to the jsondiff output file')
    args = parser.parse_args()
    return args


def main():
    args = parse_arguments()
    check_release_files(args.all_ror_ids_file,
                        args.release_tests_outfile, args.jsondiff_outfile)


if __name__ == '__main__':
    main()
