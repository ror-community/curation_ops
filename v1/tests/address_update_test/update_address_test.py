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

def compare_api(ror_id):
    outfile = os.getcwd() + '/jsondiff.csv'
    api_url = "https://api.ror.org/organizations/" + ror_id
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


def check_release_files():
    release_tests_outfile = os.getcwd() + "/release_tests.csv"
    jsondiff_outfile = os.getcwd() + "/jsondiff.csv"
    with open(jsondiff_outfile, 'w') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(["ror_id", "field","diff"])
    for file in glob.glob("*.json"):
        with open(file, 'r+', encoding='utf8') as f_in:
            json_file = json.load(f_in)
            ror_id = re.sub('https://ror.org/', '', json_file["id"])
            org_name = json_file["name"]
            print("Testing -", org_name, "- ROR ID:", ror_id, "...")
            compare_check = compare_api(ror_id)


if __name__ == '__main__':
    check_release_files()
