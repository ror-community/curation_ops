import csv
import argparse
from math import sqrt
from collections import defaultdict
import numpy as np


def parse_arguments():
    parser = argparse.ArgumentParser(description='Language Outlier Detection')
    parser.add_argument('-i', '--input_file', required=True,
                        help='Path to the input CSV file')
    parser.add_argument('-o', '--output_file',
                        default='detected_outliers.csv', help='Path to the output CSV file')
    return parser.parse_args()


def read_csv_file(file_path):
    data = []
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            data.append(row)
    return data


def calculate_language_distribution(data):
    distribution = defaultdict(lambda: defaultdict(int))
    for row in data:
        country_code = row['country_code']
        lang = row['lang']
        distribution[country_code][lang] += 1
    return distribution


def detect_outliers(data, distribution):
    for row in data:
        country_code = row['country_code']
        lang = row['lang']
        country_distribution = distribution[country_code]
        total_count = sum(country_distribution.values())
        if len(country_distribution) == 1:
            row['outlier'] = 'FALSE'
        else:
            counts = list(country_distribution.values())
            q1 = np.percentile(counts, 25)
            q3 = np.percentile(counts, 75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            dominant_percentage = max(country_distribution.values()) / total_count
            min_count_threshold = 100
            if country_distribution[lang] < lower_bound or country_distribution[lang] > upper_bound:
                if dominant_percentage >= 0.9 and country_distribution[lang] == max(country_distribution.values()):
                    row['outlier'] = 'FALSE'
                elif country_distribution[lang] >= min_count_threshold:
                    row['outlier'] = 'FALSE'
                else:
                    significant_languages = [lang for lang, count in country_distribution.items() if count / total_count >= 0.3]
                    if len(significant_languages) > 1 and lang in significant_languages:
                        row['outlier'] = 'FALSE'
                    else:
                        row['outlier'] = 'TRUE'
            else:
                row['outlier'] = 'FALSE'
    return data


def write_csv_file(file_path, data):
    fieldnames = data[0].keys()
    with open(file_path, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)


def main():
    args = parse_arguments()
    input_data = read_csv_file(args.input_file)
    language_distribution = calculate_language_distribution(input_data)
    output_data = detect_outliers(input_data, language_distribution)
    write_csv_file(args.output_file, output_data)
    print(f"Outlier detection completed. Output file: {args.output_file}")


if __name__ == '__main__':
    main()
