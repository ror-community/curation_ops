import json
import sys
import requests
import time
import os
import csv

deprecated_geonames = {
    6949678:	1668295,
    6691781:	683506,
    8299623:	2640923,
    2644597:	8224216,
    1797132:	9072919,
    3336587:	3162639,
    6316741:	3467723,
    2966839:	3313472,
    8617692:	4005937,
    4703387:	7534469,
    195902:	    8299780,
    12179257:	6616111
}

def get_geonames_count(input_file):
    geonames_ids = []
    with open(input_file, 'r+') as f:
        geonames_cache = json.load(f)
        print(f"Total records: {len(geonames_cache)}")
        for k, v in geonames_cache.items():
            if v not in geonames_ids:
                geonames_ids.append(v)
    print(f"Unique geonames IDs: {len(geonames_ids)}")


def get_geonames_cache_errors(input_file):
    fields = ['geonames_id', 'error']
    errors = []
    with open(input_file, 'r+') as f:
        geonames_cache = json.load(f)
        for k, v in geonames_cache.items():
            if 'Error' in v:
                errors.append([k.strip('"'), v])
    with open('errors' + input_file, 'w') as f:
        # using csv.writer method from CSV package
        write = csv.writer(f)
        write.writerow(fields)
        write.writerows(errors)

def dedup_cache_data(input_file):
    dedup_cache = {}
    with open(input_file, 'r+') as f:
        input_cache = json.load(f)
        for key,value in input_cache.items():
            if value not in dedup_cache.values():
                dedup_cache[key] = value
    with open('dedup_'+input_file, 'w') as f:
        json.dump(dedup_cache, f, ensure_ascii=False, indent=4)

def update_deprecated_ids(input_file):
    with open(input_file, 'r+') as f:
        records = json.load(f)
        for record in records:
            for location in record['locations']:
                if location['geonames_id'] in deprecated_geonames.keys():
                    location['geonames_id'] = deprecated_geonames[location['geonames_id']]
        path, filename = os.path.split(input_file)

        with open(os.path.join(path, 'updated_'+filename), 'w') as f:
            json.dump(records, f, ensure_ascii=False, indent=4)


if __name__ == '__main__':
	update_deprecated_ids(sys.argv[1])
