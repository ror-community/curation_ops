import os
import sys
import json
import csv
import glob
from string import printable


def flatten_json(j):
    flattened = {}
    def flatten(obj, name=''):
        if type(obj) is dict:
            for item in obj:
                flatten(obj[item], name + item + '_')
        elif type(obj) is list:
            i = 0
            for item in obj:
                flatten(item, name + str(i) + '_')
                i += 1
        else:
            flattened[name[:-1]] = obj
    flatten(j)
    return flattened


def check_unprintable():
    outfile = os.getcwd() + '/unprintable_characters.csv'
    header = ['ror_id', 'field', 'value']
    with open(outfile, 'w') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(header)
    for file in glob.glob("*.json"):
        with open(file, 'r+') as f_in:
            json_file = json.load(f_in)
        ror_id = json_file['id']
        flattened = flatten_json(json_file)
        for key, value in flattened.items():
            if value is not None:
                if any([ch.isprintable() == False for ch in str(value)]):
                    with open(outfile, 'a') as f_out:
                        writer = csv.writer(f_out)
                        writer.writerow([ror_id, key, value])
           

if __name__ == '__main__':
    check_unprintable()