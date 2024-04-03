#v1 legacy script
import os
import sys
import json


def get_geonames_ids(f):
    outfile = os.getcwd() + "/unique_geonames_ids.txt"
    geonames_ids= []
    country_codes = []
    with open(f, 'r+', encoding='utf8') as f_in:
        json_file = json.load(f_in)
        for record in json_file:
            print(record["country"]["country_code"])
            country_code = record["country"]["country_code"]
            if country_code not in country_codes:
                country_codes.append(country_code)
    print(len(country_codes))


if __name__ == '__main__':
	get_geonames_ids(sys.argv[1])

