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

            # 29 records have empty geonames city
            #if record["addresses"][0]["geonames_city"]:
            #    geonames_id = record["addresses"][0]["geonames_city"]["id"]
            #    if str(geonames_id) not in geonames_ids:
            #        geonames_ids.append(str(geonames_id))
    #print(len(geonames_ids))
    print(len(country_codes))
    #with open(outfile, 'a', encoding='utf8') as f_out:
    #    f_out.write('\n'.join(geonames_ids))

if __name__ == '__main__':
	get_geonames_ids(sys.argv[1])

