import csv
import re
import argparse
import os


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Check for "#" in Related organizations section of CSV file.')
    parser.add_argument('-i', '--input_file',
                        help='Path to the CSV file to process')
    parser.add_argument('-o', '--output', default='relationship_matches.csv',
                        help='Output CSV file name (default: relationship_matches.csv)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Increase output verbosity')
    return parser.parse_args()


def check_related_organizations(input_file, verbose=False):
    issues_found = []
    with open(input_file, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            issue_number = row['Issue Number']
            issue_text = row['Issue Text']
            # Find the "Related organizations:" section
            match = re.search(
                r'Related organizations:(.*?)(?:\n\w+:|$)', issue_text, re.DOTALL)
            if match:
                related_orgs_section = match.group(1).strip()
                # Check if there's a "#" in this section
                if '#' in related_orgs_section:
                    issues_found.append((issue_number, related_orgs_section))
                    if verbose:
                        print(f"Issue {issue_number} contains a '#' in the Related organizations section:")
                        print(related_orgs_section)
                        print()
    return issues_found


def write_results_to_csv(issues, output_file):
    with open(output_file, 'w', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Issue Number', 'Related Organizations Section'])
        for issue in issues:
            writer.writerow(issue)


def main():
    args = parse_arguments()
    print(f"Processing file: {args.input_file}")
    issues = check_related_organizations(args.input_file, args.verbose)
    print(f"\nFound {len(issues)} issues with '#' in Related organizations section.")
    if not args.verbose:
        for issue_number, _ in issues:
            print(f"Issue Number: {issue_number}")
    write_results_to_csv(issues, args.output)
    print(f"\nResults written to {args.output}")


if __name__ == "__main__":
    main()
