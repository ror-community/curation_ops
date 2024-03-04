import requests
import json


def catch_requests_exceptions(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.RequestException:
            return None
    return wrapper


@catch_requests_exceptions
def query_geonames_api(place_name, username='roradmin'):
    url = "http://api.geonames.org/searchJSON"
    params = {
        'q': place_name,
        'maxRows': 10,
        'username': username
    }
    response = requests.get(url, params=params)
    return response.json()


def parse_response(response):
    if "geonames" not in response or len(response["geonames"]) == 0:
        return None
    best_match = response["geonames"][0]
    return best_match["name"], best_match["geonameId"]


def search_geonames(place_name):
    response = query_geonames_api(place_name)
    if response:
        result = parse_response(response)
        if result:
            name, geoname_id = result
            best_match = f"{name} | Geonames ID: [ {geoname_id}](https://www.geonames.org/{geoname_id})"
            return best_match
    return None
