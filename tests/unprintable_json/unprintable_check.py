import json
import csv
import glob
import argparse
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


def check_unprintable(input_dir, output_file):
    header = ['ror_id', 'field', 'value']
    with open(output_file, 'w') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(header)
    for file in glob.glob(f"{input_dir}/*.json"):
        with open(file, 'r+') as f_in:
            json_file = json.load(f_in)
        ror_id = json_file['id']
        flattened = flatten_json(json_file)
        for key, value in flattened.items():
            if value is not None:
                if any([ch.isprintable() == False for ch in str(value)]):
                    with open(output_file, 'a') as f_out:
                        writer = csv.writer(f_out)
                        writer.writerow([ror_id, key, value])
           

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Check for unprintable characters in directory containing ROR records")
    parser.add_argument("-i", "--input_dir", required=True,
                        help="Input CSV file path.")
    parser.add_argument("-o", "--output_file",
                        default="unprintable_chars.csv", help="Output CSV file path.")
    return parser.parse_args()


def main():
    args = parse_arguments()
    check_unprintable(args.input_dir, args.output_file)


if __name__ == '__main__':
    main()