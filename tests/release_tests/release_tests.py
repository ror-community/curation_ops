import os
import re
import csv
import json
import glob
import time
import random
import logging
import argparse
import requests
import urllib.parse
import multiprocessing
from time import sleep
from functools import partial
from deepdiff import DeepDiff
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

MAX_PARALLEL_REQUESTS = 5
RATE_LIMIT_CALLS = 1000
RATE_LIMIT_PERIOD = 300

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def init_shared_rate_limiter():
    manager = multiprocessing.Manager()
    shared_calls = manager.list()
    shared_lock = manager.Lock()
    return GlobalRateLimiter(RATE_LIMIT_CALLS, RATE_LIMIT_PERIOD, shared_calls, shared_lock)


class GlobalRateLimiter:
    def __init__(self, max_calls, period, shared_calls, shared_lock):
        self.max_calls = max_calls
        self.period = period
        self.calls = shared_calls
        self.lock = shared_lock

    def wait(self):
        with self.lock:
            now = time.time()
            self.calls[:] = [t for t in self.calls if now - t < self.period]
            if len(self.calls) >= self.max_calls:
                sleep_time = self.period - (now - self.calls[0])
                time.sleep(max(sleep_time, 0))
            self.calls.append(now)


def rate_limited_request(url, params=None, rate_limiter=None):
    if rate_limiter:
        rate_limiter.wait()
    response = requests.get(url, params=params)
    if response.status_code == 404:
        return response
    response.raise_for_status()
    return response


def get_ror_display_name(json_file, version):
    if version == 1:
        return json_file.get('name')
    return next((name['value'] for name in json_file.get('names', []) if 'ror_display' in name.get('types', [])), None)


def retrieve_api(args):
    ror_id, rate_limiter, base_url, version = args
    api_url = f"{base_url}/v{version}/organizations/{ror_id}"
    r = rate_limited_request(api_url, rate_limiter=rate_limiter)
    return ror_id, "retrieved" if r.status_code == 200 else "failed"


def compare_api(args):
    ror_id, json_file, rate_limiter, base_url, version = args
    api_url = f"{base_url}/v{version}/organizations/{ror_id}"
    try:
        response = rate_limited_request(api_url, rate_limiter=rate_limiter)
        response.raise_for_status()
        if not response.content.strip():
            return ror_id, "api_error", "Empty response received"
        try:
            api_json = response.json()
        except requests.exceptions.JSONDecodeError as e:
            return ror_id, "api_error", f"Invalid JSON response: {str(e)}"
            
        diff = DeepDiff(api_json, json_file, ignore_order=True)
        return ror_id, "different" if diff else "same", diff or None
        
    except requests.exceptions.RequestException as e:
        return ror_id, "api_error", f"Request error: {str(e)}"
    except Exception as e:
        return ror_id, "api_error", f"Unexpected error: {str(e)}"


def search_name_api(args):
    ror_id, org_name, rate_limiter, base_url, version = args
    api_url = f'{base_url}/v{version}/organizations'
    params = {'query': f'"{org_name}"', 'all_status': 'True'}
    try:
        r = rate_limited_request(api_url, params=params, rate_limiter=rate_limiter)
        if r.status_code == 404:
            return ror_id, org_name, "not_found"
        if not r.content.strip():
            return ror_id, org_name, "empty_response"
            
        try:
            results = r.json()["items"]
        except (KeyError, requests.exceptions.JSONDecodeError) as e:
            return ror_id, org_name, f"invalid_response: {str(e)}"
            
        for result in results:
            ror_display = get_ror_display_name(result, version)
            if ror_display == org_name:
                return ror_id, org_name, "retrieved"
        return ror_id, org_name, "failed"
        
    except requests.exceptions.RequestException as e:
        return ror_id, org_name, f"request_error: {str(e)}"
    except Exception as e:
        return ror_id, org_name, f"unexpected_error: {str(e)}"


def process_file(args):
    file_path, version = args
    with open(file_path, 'r', encoding='utf8') as f_in:
        json_file = json.load(f_in)
    ror_id = re.sub('https://ror.org/', '', json_file["id"])
    org_name = get_ror_display_name(json_file, version)
    return ror_id, org_name, json_file


def retrieve_from_ui(ror_id, driver, environment='prd'):
    base_url = "https://ror.org" if environment == 'prd' else "https://staging.ror.org"
    ui_url = f"{base_url}/{ror_id}"
    href_value = "/" + ror_id
    driver.get(ui_url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, features="html.parser")
    link_in_ui = soup.find('a', {'href': href_value})
    return "retrieved" if link_in_ui is not None else "failed"


def search_name_ui(org_name, driver, environment='prd'):
    base_url = "https://ror.org" if environment == 'prd' else "https://staging.ror.org"
    quoted_name = urllib.parse.quote(org_name)
    ui_url = f'{base_url}/search?filter=status:active,status:inactive,status:withdrawn&query="{quoted_name}"'
    driver.get(ui_url)
    sleep(2)
    soup = BeautifulSoup(driver.page_source, features="html.parser")
    name_in_ui = soup.find('h2', string=org_name)
    return "retrieved" if name_in_ui is not None else "failed"


def perform_ui_tests(file_data, driver, environment='prd'):
    ui_test_results = []
    for ror_id, org_name, _ in file_data:
        retrieve_result = retrieve_from_ui(ror_id, driver, environment)
        search_result = search_name_ui(org_name, driver, environment)
        ui_test_results.append(
            (ror_id, org_name, retrieve_result, search_result))
    return ui_test_results


def compare_single(args):
    ror_id, rate_limiter, base_url, version = args
    prod_api_url = f"https://api.ror.org/v{version}/organizations/{ror_id}"
    staging_api_url = f"{base_url}/v{version}/organizations/{ror_id}"
    prod_response = rate_limited_request(
        prod_api_url, rate_limiter=rate_limiter).json()
    staging_response = rate_limited_request(
        staging_api_url, rate_limiter=rate_limiter).json()
    return ror_id if prod_response != staging_response else None


def compare_random(compare_ids, shared_rate_limiter, base_url, version):
    pool = multiprocessing.Pool(MAX_PARALLEL_REQUESTS)
    results = pool.map(compare_single, [
                       (ror_id, shared_rate_limiter, base_url, version) for ror_id in compare_ids])
    pool.close()
    pool.join()
    return [ror_id for ror_id in results if ror_id is not None]


def check_release_files(release_directory, all_ror_ids_file, release_tests_outfile, jsondiff_outfile, ui_tests_outfile, shared_rate_limiter, base_url, version, environment='prd'):
    if not os.path.exists(release_directory):
        logging.error(f"Release directory '{release_directory}' does not exist.")
        exit(1)
    json_files = glob.glob(os.path.join(release_directory, "**", "*.json"), recursive=True)
    total_files = len(json_files)
    logging.info(f"Found {total_files} JSON files to process.")
    pool = multiprocessing.Pool(MAX_PARALLEL_REQUESTS)
    with open(release_tests_outfile, 'w') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(["ror_id", "org_name", "retrieve_check", "compare_check", "search_name_api_check"])
    with open(jsondiff_outfile, 'w') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(["ror_id", "diff"])
    processed_ids = set()
    all_file_data = []
    chunk_size = 100

    for i in range(0, total_files, chunk_size):
        chunk = json_files[i:i+chunk_size]
        logging.info(f"Processing chunk {i//chunk_size + 1} of {(total_files-1)//chunk_size + 1}")
        
        logging.info("Processing files...")
        file_data = pool.map(process_file, [(file_path, version) for file_path in chunk])
        all_file_data.extend(file_data)  # Accumulate file data
        ror_ids = [data[0] for data in file_data]
        org_names = [data[1] for data in file_data]
        json_files_data = [data[2] for data in file_data]

        logging.info("Performing retrieve API checks...")
        retrieve_results = pool.map(retrieve_api, [(ror_id, shared_rate_limiter, base_url, version) for ror_id in ror_ids])
        
        logging.info("Performing compare API checks...")
        compare_results = pool.map(compare_api, [(ror_id, json_file, shared_rate_limiter, base_url, version) for ror_id, json_file in zip(ror_ids, json_files_data)])
        
        logging.info("Performing search name API checks...")
        search_results = pool.map(search_name_api, [(ror_id, org_name, shared_rate_limiter, base_url, version) for ror_id, org_name in zip(ror_ids, org_names)])

        logging.info("Writing results to files...")
        with open(release_tests_outfile, 'a') as f_out:
            writer = csv.writer(f_out)
            for i, ror_id in enumerate(ror_ids):
                writer.writerow([ror_id, org_names[i], retrieve_results[i][1], compare_results[i][1], search_results[i][2]])

        with open(jsondiff_outfile, 'a') as f_out:
            writer = csv.writer(f_out)
            for result in compare_results:
                if result[2]:
                    writer.writerow([result[0], result[2]])

        processed_ids.update(ror_ids)
        logging.info(f"Processed {len(processed_ids)} out of {total_files} files.")

    pool.close()
    pool.join()

    logging.info("Reading all ROR IDs for unprocessed IDs and random selection...")
    with open(all_ror_ids_file) as f_in:
        all_ror_ids = set(re.sub('https://ror.org/', '', line.strip()).lower() for line in f_in)
    unprocessed_ids = list(all_ror_ids - set(ror_id.lower() for ror_id in processed_ids))
    random_ids = random.sample(unprocessed_ids, min(500, len(unprocessed_ids)))
    logging.info(f"Selected {len(random_ids)} random unprocessed IDs for comparison.")

    logging.info("Performing random comparison checks...")
    compare_random_check = compare_random(random_ids, shared_rate_limiter, base_url, version)
    if compare_random_check:
        logging.warning(f"The following IDs have changed: {compare_random_check}. Investigate integrity of ROR dataset.")
    else:
        logging.info("No changes detected in random comparison checks.")

    ui_test_files = random.sample(all_file_data, min(100, len(all_file_data)))
    logging.info(f"Selected {len(ui_test_files)} files for UI tests.")

    logging.info("Starting UI tests...")
    options = Options()
    options.headless = True
    with webdriver.Firefox(options=options) as driver:
        ui_test_results = perform_ui_tests(ui_test_files, driver, environment)

    logging.info("Writing UI test results...")
    with open(ui_tests_outfile, 'w') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(["ror_id", "org_name", "retrieve_from_ui", "search_name_ui"])
        writer.writerows(ui_test_results)
    logging.info(f"UI tests completed for {len(ui_test_results)} files.")

    logging.info("All tests completed.")


def parse_arguments():
    parser = argparse.ArgumentParser(description='Run release tests for ROR')
    parser.add_argument('-r', '--release_directory', required=True,
                        help='Path to the directory containing JSON files')
    parser.add_argument('-a', '--all_ror_ids_file', default='all_ror_ids.txt',
                        help='Path to the file containing all ROR IDs')
    parser.add_argument('-t', '--release_tests_outfile',
                        default='release_tests.csv', help='Path to the release tests output file')
    parser.add_argument('-j', '--jsondiff_outfile',
                        default='jsondiff.csv', help='Path to the jsondiff output file')
    parser.add_argument('-u', '--ui_tests_outfile',
                        default='ui_tests.csv', help='Path to the UI tests output file')
    parser.add_argument('-e', '--environment', choices=[
                        'prd', 'stg'], default='prd', help='Choose between production and staging environments')
    parser.add_argument('-v', '--version', type=int, choices=[1, 2], default=2,
                        help='API version to use (1 or 2)')
    return parser.parse_args()


def main():
    start_time = time.time()
    args = parse_arguments()
    shared_rate_limiter = init_shared_rate_limiter()
    base_domain = "api.ror.org" if args.environment == 'prd' else "api.staging.ror.org"
    base_url = f"https://{base_domain}"
    check_release_files(
        args.release_directory,
        args.all_ror_ids_file,
        args.release_tests_outfile,
        args.jsondiff_outfile,
        args.ui_tests_outfile,
        shared_rate_limiter,
        base_url,
        args.version,
        args.environment
    )

    end_time = time.time


if __name__ == '__main__':
    main()