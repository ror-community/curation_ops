import os
import sys
import json


def get_unique_funder_ids(file):
    outfile = os.getcwd() + "/unique_funder_ids.txt"
    funder_ids= []
    with open(file, 'r+', encoding='utf8') as f_in:
        json_file = json.load(f_in)
        for record in json_file:
            if len(record['external_ids']) > 0:
                if 'FundRef' in record['external_ids']:
                    print(record['external_ids']['FundRef'])
                    if record['external_ids']['FundRef']['preferred']:
                        if record['external_ids']['FundRef']['preferred'] not in funder_ids:
                            funder_ids.append(record['external_ids']['FundRef']['preferred'])
                    if record['external_ids']['FundRef']['all']:
                        for funder_id in record['external_ids']['FundRef']['all']:
                             if funder_id not in funder_ids:
                                  funder_ids.append(funder_id)

    print(len(funder_ids))
    with open(outfile, 'a', encoding='utf8') as f_out:
        f_out.write('\n'.join(funder_ids))

if __name__ == '__main__':
    get_unique_funder_ids(sys.argv[1])

