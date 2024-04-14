import os
import sys
import csv
from string import printable


def check_unprintable(f):
	outfile = os.getcwd() + '/check_unprintable.csv'
	with open(f, encoding='utf-8-sig') as f_in:
		reader = csv.DictReader(f_in)
		for row in reader:
			for field in row:
				if any([ch.isprintable() == False for ch in row[field]]):
					with open(outfile, 'a') as f_out:
						writer = csv.writer(f_out)
						writer.writerow([row['issue_number'], field, row[field]])

if __name__ == '__main__':
	check_unprintable(sys.argv[1])