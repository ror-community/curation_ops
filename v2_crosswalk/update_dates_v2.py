import argparse
import json
import os
import logging
import sys
from zipfile import ZipFile, ZIP_DEFLATED
from datetime import datetime
from csv import DictReader
import sys

ERROR_LOG = "errors.log"
INPUT_PATH = "./"
OUTPUT_PATH = "./"

logging.basicConfig(filename=ERROR_LOG,level=logging.ERROR, filemode='w')

def update_dates(dump_file, date_file):
    dates_list = []
    with open(date_file, 'r') as f:
        dict_reader = DictReader(f)
        dates_list = list(dict_reader)
    with open(dump_file, 'r') as f:
        print(dump_file)
        dump_json = json.load(f)
        for record in dump_json:
            date_item = [i for i in dates_list if i['ror_id']==record['id']]
            print("updating record " + record['id'])
            record['admin']['created']['date'] = date_item[0]['created']
            record['admin']['last_modified']['date'] = date_item[0]['last_modified']
        open(dump_file, "w").write(
            json.dumps(dump_json, indent=4, separators=(',', ': '))
        )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--dumpjsonfilepath', type=str)
    parser.add_argument('-d', '--datescsvfilepath', type=str)
    parser.add_argument('-o', '--outputfilepath', type=str, default="./V2_OUTPUT/")

    args = parser.parse_args()

    if os.path.exists(args.dumpjsonfilepath) and os.path.exists(args.datescsvfilepath):
        update_dates(args.dumpjsonfilepath, args.datescsvfilepath)
    else:
        print("One or both input files do not exist")

    #file_size = os.path.getsize(ERROR_LOG)
    # if (file_size == 0):
    #    os.remove(ERROR_LOG)
    #elif (file_size != 0):
    #    with open(ERROR_LOG, 'r') as f:
    #        print(f.read())
    #    sys.exit(1)

if __name__ == "__main__":
    main()