import json
import sys
import requests
import time
import os


GEONAMES = {}
GEONAMES['USER'] = "roradmin"
GEONAMES['URL'] = 'http://api.geonames.org/getJSON'

def get_geonames_response(id):
    print("Fetching Geonames ID " + str(id))
    # queries geonames api with the location geonames id as a query parameter
    msg = None
    result = None
    query_params = {}
    query_params['geonameId'] = id
    query_params['username'] = GEONAMES['USER']
    url = GEONAMES['URL']
    try:
        response = requests.get(url,params=query_params)
        response.raise_for_status()
        result = json.loads(response.text)
    except requests.exceptions.HTTPError as errh:
        msg = "Http Error: " + str(errh)
        result = msg
        print (msg)
    except requests.exceptions.ConnectionError as errc:
        msg = "Error Connecting: " + str(errc)
        result = msg
        print (msg)
    except requests.exceptions.Timeout as errt:
        msg = "Timeout Error: " + str(errt)
        result = msg
        print (msg)
    except requests.exceptions.RequestException as err:
        msg = "Request exception: " + str(err)
        result = msg
        print (msg)
    return result


def create_geonames_cache(input_file):
    response_cache = {}
    with open(input_file, 'r+') as geonames_ids:
        for geonames_id in geonames_ids:
            result = get_geonames_response(geonames_id.strip('\n'))
            response_cache[geonames_id.strip('\n')] = result
            #time.sleep(1)
    '''
    if os.path.exists('geonames_cache_02.json'):
        if os.stat('geonames_cache_02.json').st_size > 0:
            with open("geonames_cache_02.json", "r+") as outfile:
                    existing_cache = json.load(outfile)
                    existing_cache.update(response_cache)
                    json.dump(existing_cache, outfile)
    else:
    '''
    with open("geonames_cache_04.json", "w") as outfile:
        json.dump(response_cache, outfile)


if __name__ == '__main__':
	create_geonames_cache(sys.argv[1])
