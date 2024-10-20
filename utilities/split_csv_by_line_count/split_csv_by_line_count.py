import os
import sys
import csv
import argparse
import logging
from collections import Counter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("csv_splitter.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Split a CSV file into smaller files based on line count.")
    parser.add_argument("-i", "--input_file", required=True,
                        help="Path to the input CSV file")
    parser.add_argument("-l", "--line_count", type=int,
                        required=True, help="Number of lines per output file")
    parser.add_argument(
        "-o", "--output_dir", help="Directory to save output files (default: {input_file_name}_split_{line_count})")
    parser.add_argument("-v", "--validate", action="store_true",
                        help="Validate the split files by comparing with the input file")
    args = parser.parse_args()
    if args.line_count <= 0:
        parser.error("line_count must be a positive integer")
    if not args.output_dir:
        input_name = os.path.splitext(os.path.basename(args.input_file))[0]
        args.output_dir = f"{input_name}_split_{args.line_count}"
    return args


def create_output_directory(output_dir):
    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as e:
        logger.error(f"Error creating output directory: {e}")
        sys.exit(1)


def split_csv(input_file, line_count, output_dir):
    try:
        input_filename = os.path.splitext(os.path.basename(input_file))[0]
        with open(input_file, 'r', newline='') as f_in:
            reader = csv.reader(f_in)
            header = next(reader)
            file_number = 1
            current_line_count = 0
            current_writer = None
            for row in reader:
                if current_line_count == 0:
                    output_file = os.path.join(output_dir, f"{input_filename}_split_{line_count}_p{file_number:03d}.csv")
                    output_csv = open(output_file, 'w', newline='')
                    current_writer = csv.writer(output_csv)
                    current_writer.writerow(header)
                current_writer.writerow(row)
                current_line_count += 1
                if current_line_count >= line_count:
                    output_csv.close()
                    file_number += 1
                    current_line_count = 0
            if current_line_count > 0:
                output_csv.close()
        logger.info(f"CSV splitting complete. Output files saved in: {output_dir}")
    except IOError as e:
        logger.error(f"Error reading input file or writing output files: {e}")
        sys.exit(1)


def read_csv_to_counter(file_path):
    with open(file_path, 'r', newline='') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        return Counter(tuple(row) for row in reader)


def read_split_files_to_counter(output_dir, input_filename):
    counter = Counter()
    for filename in os.listdir(output_dir):
        if filename.startswith(input_filename) and filename.endswith('.csv'):
            file_path = os.path.join(output_dir, filename)
            with open(file_path, 'r', newline='') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                counter.update(tuple(row) for row in reader)
    return counter


def validate_split_files(input_file, output_dir):
    input_filename = os.path.splitext(os.path.basename(input_file))[0]
    try:
        input_data = read_csv_to_counter(input_file)
        split_data = read_split_files_to_counter(output_dir, input_filename)
        if input_data == split_data:
            logger.info(
                "Validation successful: The split files match the input file.")
        else:
            logger.error(
                "Validation failed: Discrepancies found between the input file and the split files.")

            only_in_input = input_data - split_data
            only_in_split = split_data - input_data

            if only_in_input:
                logger.error(f"Rows in input file but not in split files: {sum(only_in_input.values())}")
                for row, count in only_in_input.items():
                    logger.error(f"  {row} (count: {count})")

            if only_in_split:
                logger.error(f"Rows in split files but not in input file: {sum(only_in_split.values())}")
                for row, count in only_in_split.items():
                    logger.error(f"  {row} (count: {count})")

    except IOError as e:
        logger.error(f"Error during validation: {e}")
        sys.exit(1)


def main():
    args = parse_arguments()
    create_output_directory(args.output_dir)
    split_csv(args.input_file, args.line_count, args.output_dir)
    if args.validate:
        validate_split_files(args.input_file, args.output_dir)


if __name__ == "__main__":
    main()
