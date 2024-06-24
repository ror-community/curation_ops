import os
import sys
import csv
import json
import glob


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


def check_leading_trailing(file):
    outfile = os.getcwd() + '/leading_trailing.csv'
    header = ['ror_id', 'field', 'value']
    with open(outfile, 'w') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(header)
    for file in glob.glob("*.json"):
        with open(file, 'r+') as f_in:
            record = json.load(f_in)
            ror_id = record['id']
            flattened = flatten_json(record)
            for key, value in flattened.items():
                if value is not None and isinstance(value, str):
                    first_char = value[0]
                    last_char = value[-1]
                    whitespace_and_punctuation = '!#$%&*+, -./:;<=>?@\\^_`{|}~\t\n\v\f\r'
                    if first_char in whitespace_and_punctuation or last_char in whitespace_and_punctuation:
                        with open(outfile, 'a') as f_out:
                            writer = csv.writer(f_out)
                            writer.writerow([ror_id, key, value])


if __name__ == '__main__':
    check_leading_trailing(sys.argv[1])
