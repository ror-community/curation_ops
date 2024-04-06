import csv
import argparse
import requests


def query_geonames_api(geonames_id, username):
    api_url = "http://api.geonames.org/getJSON"
    params = {
        'geonameId': geonames_id,
        'username': username
    }
    response = requests.get(api_url, params=params)
    data = response.json()
    return data.get("name", ""), data.get("countryName", "")


def validate_city_country(record, api_data):
    return record["city"] == api_data[0] and record["country"] == api_data[1]


def arg_parse():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input_file", type=str, required=True)
    parser.add_argument("-u", "--api_user", type=str, required=True)
    parser.add_argument("-o", "--output_file", type=str,
                        default='address_discrepancies.csv')
    return parser.parse_args()


def main():
    args = arg_parse()
    discrepancies = []
    with open(args.input_file, 'r') as f_in:
        reader = csv.DictReader(f_in)
        for row in reader:
            api_city_country = query_geonames_api(
                row['locations.geonames_id'], args.api_user)
            if not validate_city_country(row, api_city_country):
                discrepancies.append({
                    "name": row["names.types.ror_display"],
                    "geonames_id": row["locations.geonames_id"],
                    "csv_city": row["city"],
                    "csv_country": row["country"],
                    "api_city": api_city_country[0],
                    "api_country": api_city_country[1]
                })
    with open(args.output_file, 'w', newline='') as f_out:
        fieldnames = ["names.types.ror_display", "locations.geonames_id", "csv_city",
                      "csv_country", "api_city", "api_country"]
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        for record in discrepancies:
            writer.writerow(record)


if __name__ == "__main__":
    main()
