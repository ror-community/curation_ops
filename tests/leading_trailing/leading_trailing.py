import csv
import json
import glob
import argparse


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


def check_leading_trailing(input_dir, output_file):
    header = ['ror_id', 'field', 'value']
    with open(output_file, 'w') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(header)
    for file in glob.glob(f"{input_dir}/*.json"):
        with open(file, 'r+') as f_in:
            record = json.load(f_in)
        ror_id = record['id']
        flattened = flatten_json(record)
        for key, value in flattened.items():
            if value and isinstance(value, str):
                first_char = value[0]
                last_char = value[-1]
                whitespace_and_punctuation = '!#$%&*+, -./:;<=>?@\\^_`{|}~\t\n\v\f\r'
                if first_char in whitespace_and_punctuation or last_char in whitespace_and_punctuation:
                    with open(output_file, 'a') as f_out:
                        writer = csv.writer(f_out)
                        writer.writerow([ror_id, key, value])


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Check for leading and trailing characters in directory containing ROR records")
    parser.add_argument("-i", "--input_dir", required=True,
                        help="Input CSV file path.")
    parser.add_argument("-o", "--output_file",
                        default="leading_trailing_chars.csv", help="Output CSV file path.")
    return parser.parse_args()


def main():
    args = parse_arguments()
    check_leading_trailing(args.input_dir, args.output_file)


if __name__ == '__main__':
    main()
