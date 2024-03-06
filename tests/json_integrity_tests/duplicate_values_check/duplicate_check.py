import csv
import glob
import json
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


def check_in_json(input_dir, output_file):
	header = ['ror_id', 'field', 'value', 'duplicated_in']
	with open(output_file, 'w') as f_out:
		writer = csv.writer(f_out)
		writer.writerow(header)
	for file in glob.glob(f"{input_dir}/*.json"):
		with open(file, 'r+', encoding='utf8') as f_in:
			json_file = json.load(f_in)
		ror_id = json_file['id']
		flattened = flatten_json(json_file)
		seen = {}
		ignore = [
			'',
			None,
			[],
			'ror_display',
			'alias',
			'label',
			'acronym',
			'isni',
			'admin_created_date',
			'admin_last_modified_date'
		]
		for key, value in flattened.items():
			if key not in ignore:
				if isinstance(value, str) and value not in ignore:
					if value in seen.values():
						with open(output_file, 'a') as f_out:
							writer = csv.writer(f_out)
							inverted_seen = {v: k for k, v in seen.items()}
							writer.writerow([ror_id, key, value, inverted_seen[value]])
					else:
						seen[key] = value


def parse_arguments():
	parser = argparse.ArgumentParser(
		description="Check for duplicate values in directory containing ROR records")
	parser.add_argument("-i", "--input_file", required=True,
						help="Input CSV file path.")
	parser.add_argument("-o", "--output_file",
						default="duplicate_values.csv", help="Output CSV file path.")
	return parser.parse_args()


def main():
	args = parse_arguments()
	check_in_json(args.input_file, args.output_file)


if __name__ == '__main__':
	main()
