import sys
import os
import re
import csv
import json
import glob
import random
import urllib.parse
import requests
import jsondiff
from time import sleep
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

options = Options()
options.headless = True
driver = webdriver.Firefox(options=options)


def retrieve_api(ror_id):
    api_url = "https://api.staging.ror.org/organizations/" + ror_id
    r = requests.get(api_url)
    if r.status_code == 200:
        return "retrieved"
    return "failed"


def compare_api(ror_id):
    outfile = os.getcwd() + '/jsondiff.csv'
    api_url = "https://api.staging.ror.org/organizations/" + ror_id
    api_json = requests.get(api_url).json()
    json_file_path = os.getcwd() + "/" + ror_id + ".json"
    with open(json_file_path, 'r+', encoding='utf8') as f_in:
            json_file = json.load(f_in)
    file_api_diff = jsondiff.diff(api_json, json_file, syntax='symmetric')
    if api_json != json_file:
        with open(outfile, 'a') as f_out:
            writer = csv.writer(f_out)
            for key, value in file_api_diff.items():
                writer.writerow([ror_id, key, value])
        return "different"
    return "same"

def search_name_api(org_name):
    api_url = "https://api.staging.ror.org/organizations?query=" + \
        urllib.parse.quote(org_name)
    r = requests.get(api_url)
    results = r.json()["items"]
    for result in results:
        if result["name"] == org_name:
            return "retrieved"
    return "failed"


def compare_random(ids_in_file):
    with open(os.getcwd() + "/all_ror_ids.txt") as f_in:
        all_ror_ids = [line.strip() for line in f_in]
    all_ror_ids = [ror_id for ror_id in all_ror_ids if ror_id not in ids_in_file]
    random_ror_ids = []
    for _ in range(50):
        random_ror_ids.append(random.choice(all_ror_ids))
    for ror_id in random_ror_ids:
        api_url = "https://api.ror.org/organizations/" + ror_id
        test_api_url = "https://api.staging.ror.org/organizations/" + ror_id
        print("Comparing staging and production for", ror_id, "...")
        r1 = requests.get(api_url).json()
        r2 = requests.get(test_api_url).json()
        if r1 != r2:
            return ror_id
        else:
            print("Dev matches production for", ror_id)
    return None


def check_release_files():
    release_tests_outfile = os.getcwd() + "/release_tests.csv"
    jsondiff_outfile = os.getcwd() + "/jsondiff.csv"
    with open(release_tests_outfile, 'w') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(["ror_id", "org_name", "retrieve_check", "compare_check", "search_name_api_check"])
    with open(jsondiff_outfile, 'w') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(["ror_id", "field","diff"])
    ids_in_file = []
    for file in glob.glob("*.json"):
        with open(file, 'r+', encoding='utf8') as f_in:
            json_file = json.load(f_in)
            ids_in_file.append(json_file["id"])
            ror_id = re.sub('https://ror.org/', '', json_file["id"])
            org_name = json_file["name"]
            print("Testing -", org_name, "- ROR ID:", ror_id, "...")
            retrieve_check = retrieve_api(ror_id)
            compare_check = compare_api(ror_id)
            search_name_api_check = search_name_api(org_name)
            with open(release_tests_outfile, 'a') as f_out:
                writer = csv.writer(f_out)
                writer.writerow([ror_id, org_name, retrieve_check, compare_check, search_name_api_check])
    compare_random_check = compare_random(ids_in_file)
    if compare_random_check is not None:
        print(compare_random_check,
              "has changed. Investigate integrity of ROR dataset.")


if __name__ == '__main__':
    check_release_files()
