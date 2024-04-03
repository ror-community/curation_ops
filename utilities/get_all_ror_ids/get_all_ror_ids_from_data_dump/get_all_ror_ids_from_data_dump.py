import os
import json
import argparse


def get_all_ror_ids(input_file, output_file):
    with open(input_file, 'r+', encoding='utf8') as f_in:
        json_file = json.load(f_in)
        ror_ids = []
        for record in json_file:
            ror_ids.append(record["id"])
    with open(output_file, 'w') as f_out:
        f_out.write('\n'.join(ror_ids))


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Extract ROR IDs from a JSON file.')
    parser.add_argument('-i', '--input', required=True, help='Input JSON file')
    parser.add_argument('-o', '--output', default='all_ror_ids.txt',
                        help='Output file (default: all_ror_ids.txt)')
    return parser.parse_args()


def main():
    args = parse_arguments()
    input_file = args.input
    output_file = args.output
    if not os.path.isfile(input_file):
        print(f"Input file '{input_file}' does not exist.")
        return
    get_all_ror_ids(input_file, output_file)
    print(f"ROR IDs extracted and saved to '{output_file}'.")


if __name__ == '__main__':
    main()
