import os
import sys
import json


def get_all_ror_ids(f):
	outfile = os.getcwd() + "/all_ror_ids.txt"
	with open(f, 'r+', encoding='utf8') as f_in:
		json_file = json.load(f_in)
	ror_ids= []
	for record in json_file:
		ror_ids.append(record["id"])
	with open(outfile, 'a') as f_out:
		f_out.write('\n'.join(ror_ids))  

if __name__ == '__main__':
	get_all_ror_ids(sys.argv[1])

