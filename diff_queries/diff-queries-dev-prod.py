import argparse
import requests
from os import path
from deepdiff import DeepDiff

ROR_API_ENDPOINT_DEV = "https://api.dev.ror.org/organizations"
ROR_API_ENDPOINT_PROD = "https://api.dev.ror.org/organizations"
INPUT_DIR = "input/"
#OUTPUT_DIR = "output/"

def process_file(input_file):
    with open(input_file) as file:
        for line in file:
            try:
                dev_response = requests.get(ROR_API_ENDPOINT_DEV + '?' + line).json()
                prod_response = requests.get(ROR_API_ENDPOINT_PROD + '?' + line).json()
                diff = DeepDiff(dev_response, prod_response)
                print("Diff esults for query:")
                print(line)
                print(diff)
            except Exception as e:
                print("Error for query:")
                print(line)
                print(e)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--filename', type=str)
    args = parser.parse_args()
    input_file = INPUT_DIR + args.filename
    if path.exists(input_file):
        process_file(input_file)
    else:
        print("File " + input_file + " does not exist. Cannot process file.")
if __name__ == '__main__':
    main()