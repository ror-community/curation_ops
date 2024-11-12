import re
import csv
import json
import glob
import string
import urllib
import argparse
import itertools
import requests
from thefuzz import fuzz
import time
import logging
import multiprocessing
from functools import partial

MAX_PARALLEL_REQUESTS = 5
RATE_LIMIT_CALLS = 1000
RATE_LIMIT_PERIOD = 300

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


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


def init_shared_rate_limiter():
    manager = multiprocessing.Manager()
    shared_calls = manager.list()
    shared_lock = manager.Lock()
    return GlobalRateLimiter(RATE_LIMIT_CALLS, RATE_LIMIT_PERIOD, shared_calls, shared_lock)


def normalize_text(org_name):
    org_name = org_name.lower()
    org_name = re.sub(r'[^\w\s]', '', org_name)
    exclude = set(string.punctuation)
    org_name = ''.join(ch for ch in org_name if ch not in exclude)
    return org_name


def get_all_names(j):
    all_names = []
    name_types = ['ror_display', 'alias', 'label']
    for name_type in name_types:
        all_names += [name['value']
                      for name in j.get('names', []) if name_type in name.get('types', [])]
    return all_names


def get_country_code(record):
    locations = record.get('locations', [])
    if locations:
        return locations[0].get('geonames_details', {}).get('country_code')
    return None


def ror_search(org_name, record_country_code, rate_limiter):
    base_url = 'https://api.ror.org/v2/organizations'
    normalized_name = normalize_text(org_name)
    params_query = {'query': normalized_name}
    params_affiliation = {'affiliation': normalized_name}
    all_params = [params_query, params_affiliation]
    ror_matches = []
    for params in all_params:
        rate_limiter.wait()
        r = requests.get(base_url, params=params)
        print(r.url)
        api_response = r.json()
        if api_response['number_of_results'] != 0:
            results = api_response['items']
            for result in results:
                if 'organization' in result:
                    result = result['organization']
                ror_id = result['id']
                result_country_code = get_country_code(result)
                if record_country_code == result_country_code:
                    result_names = get_all_names(result)
                    for result_name in result_names:
                        name_mr = fuzz.ratio(
                            normalized_name, normalize_text(result_name))
                        if name_mr >= 90:
                            ror_matches.append([ror_id, result_name, name_mr])

    ror_matches = list(ror_matches for ror_matches,
                       _ in itertools.groupby(ror_matches))
    return ror_matches


def check_duplicates(input_dir, output_file):
    header = ["ror_id", "name", "matched_ror_id",
              "matched_name", "match_ratio"]
    with open(output_file, 'w') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(header)
    files = glob.glob(f"{input_dir}/*.json")
    shared_rate_limiter = init_shared_rate_limiter()
    pool = multiprocessing.Pool(MAX_PARALLEL_REQUESTS)
    process_file_partial = partial(
        process_file, rate_limiter=shared_rate_limiter)
    for result in pool.imap_unordered(process_file_partial, files):
        if result:
            with open(output_file, 'a') as f_out:
                writer = csv.writer(f_out)
                writer.writerows(result)
    pool.close()
    pool.join()


def process_file(file, rate_limiter):
    with open(file, 'r+') as f_in:
        json_file = json.load(f_in)
    ror_id = json_file['id']
    record_country_code = get_country_code(json_file)
    record_names = get_all_names(json_file)
    results = []
    for record_name in record_names:
        print("Searching", ror_id, "-", record_name, "...")
        ror_matches = ror_search(
            record_name, record_country_code, rate_limiter)
        if ror_matches:
            for match in ror_matches:
                results.append([ror_id, record_name] + match)
    return results


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Check for duplicate name records on production from a directory containing ROR records")
    parser.add_argument("-i", "--input_dir", required=True,
                        help="Input directory path.")
    parser.add_argument("-o", "--output_file",
                        default="on_production_duplicates.csv", help="Output CSV file path.")
    return parser.parse_args()


def main():
    args = parse_arguments()
    check_duplicates(args.input_dir, args.output_file)


if __name__ == '__main__':
    main()
