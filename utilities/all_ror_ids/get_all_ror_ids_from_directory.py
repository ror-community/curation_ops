import os
import csv
import sys
import glob
import json


def get_all_names_ror_ids():
    outfile = os.getcwd() + "/all_names_ror_ids.csv"
    with open(outfile, 'w') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(['name', 'ror_id'])
    for file in glob.glob("*.json"):
        with open(file, 'r+', encoding='utf8') as f_in:
            record = json.load(f_in)
            ror_id = record['id']
            name = record['name']
            with open(outfile, 'a') as f_out:
                writer = csv.writer(f_out)
                writer.writerow([name, ror_id])


if __name__ == '__main__':
    get_all_names_ror_ids()
