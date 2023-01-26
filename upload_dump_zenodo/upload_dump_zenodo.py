import argparse
import json
import os
import logging
import requests
import sys

ZENODO_API_URL_SANDBOX = "https://sandbox.zenodo.org/api/"
ZENODO_API_URL_PROD = "https://zenodo.org/api/"
ZENODO_API_URL = ""
ZENODO_TOKEN = ""
GITHUB_API_URL = "https://api.github.com/repos/ror-community/ror-updates/releases/tags/"
DUMP_FILE_DIR = "./"
HEADERS = {"Content-Type": "application/json"}


def get_dump_file(release):
    "Getting dump filename"
    for file in os.listdir(DUMP_FILE_DIR):
        if file.split("-", 1)[0] == release:
            return file
    return None


def get_release_notes_data(release):
    "Getting release notes data from Github"
    notes_data = {}
    try:
        r = requests.get(GITHUB_API_URL + release)
        r.raise_for_status()
        notes_data['url'] = r.json()['html_url']
        body = r.json()['body']
        for line in body.splitlines():
            if "- **Total organizations**" in line:
                notes_data['total'] = line.split(":")[1].strip()
            if "- **Records added**" in line:
                notes_data['added'] = line.split(":")[1].strip()
            if "- **Records updated**" in line:
                notes_data['updated'] = line.split(":")[1].strip()
    except requests.exceptions.HTTPError as e:
        raise SystemExit(e)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)
    return notes_data


def format_description(release_data):
    description = '<p>Data dump from the Research Organization Registry (ROR), a community-led registry \
            of open identifiers for research organizations.</p>\n\n<p>Release ' + release_data['filename'].split('-', 1)[0] + ' contains ROR IDs and metadata \
            for ' + release_data['total'] + '&nbsp;research organizations in JSON format. '
    if 'updated' in release_data or 'added' in release_data:
        description += 'This includes '
        if 'added' in release_data and 'updated' in release_data:
            description += 'the addition of ' + release_data['added'] + ' new records and metadata updates to ' \
                + release_data['updated'] + ' existing records.'
        if 'added' in release_data and 'updated' not in release_data:
            description += 'the addition of ' + release_data['added'] + ' new records.'
        if 'updated' in release_data and 'added' not in release_data:
            description += 'metadata updates to ' + release_data['updated'] + ' existing records.'
    description += '<a href=\"https://github.com/ror-community/ror-updates/releases/tag/' + release_data['filename'].split('-', 1)[0] + '\"> \
            See the release notes</a>.</p>\n\n<p>Beginning with its <a href=\"https://doi.org/10.5281/zenodo.6347575\">\
            March 2022 release</a>, ROR is curated independently from GRID. Semantic versioning beginning with v1.0 was added \
            to reflect this departure from GRID. The existing data structure was not changed.</p>\n\n<p>From March 2022 onward, \
            data releases are versioned as follows:</p>\n\n<ul>\n\t<li><strong>Minor versions (ex 1.1, 1.2, 1.3):</strong>&nbsp; \
            Contain changes to data, such as a new records and updates to existing records. No changes to the data model/structure.\
            </li>\n\t<li><strong>Patch versions (ex 1.0.1):</strong>&nbsp;Used infrequently to correct errors in a release. \
            No changes to the data model/structure.</li>\n\t<li><strong>Major versions (ex 1.x, 2.x, 3.x):</strong>&nbsp; \
            Contains changes to data model/structure, as well as the data itself. Major versions will be released with significant advance notice. \
            </li>\n</ul>\n\n<p>For convenience, the date is also include in the release file name, ex: v1.0-2022-03-15-ror-data.zip.</p>'
    return description


def update_metadata(version_url, release_data):
    print("Updating metadata")
    try:
        r = requests.get(version_url, params={'access_token': ZENODO_TOKEN})
        r.raise_for_status()
        metadata = r.json()['metadata']
        related_ids = metadata['related_identifiers']
        related_ids.append({'identifier': release_data['previous_version_doi'], 'relation': 'isNewVersionOf', 'resource_type': 'dataset', 'scheme': 'doi'})
        metadata['publication_date'] = release_data['filename'].split('-', 1)[1].split('-ror-data.zip')[0]
        metadata['version'] = release_data['filename'].split('-', 1)[0]
        metadata['description'] = format_description(release_data)
        metadata['related_identifiers'] = related_ids
        updated_metadata = {'metadata': metadata}
        try:
            r = requests.put(version_url, params={'access_token': ZENODO_TOKEN}, data=json.dumps(updated_metadata), headers=HEADERS)
            r.raise_for_status()
            if r.status_code == 200:
                "Metadata updated successfully"
        except requests.exceptions.HTTPError as e:
            raise SystemExit(e)
        except requests.exceptions.RequestException as e:
            raise SystemExit(e)
    except requests.exceptions.HTTPError as e:
        raise SystemExit(e)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)


def publish_version(version_url):
    print("Publishing new version")
    try:
        r = requests.post(version_url + '/actions/publish', params={'access_token': ZENODO_TOKEN})
        r.raise_for_status()
        if r.status_code == 202:
            print("Data dump published successfully!")
            print("DOI is " + r.json()['doi'])
    except requests.exceptions.HTTPError as e:
        raise SystemExit(e)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)


def upload_new_file(version_url, release_data):
    print("Uploading new file")
    data = {'name': release_data['filename']}
    files = {'file': open(DUMP_FILE_DIR + release_data['filename'], 'rb')}
    try:
        r = requests.post(version_url + '/files', params={'access_token': ZENODO_TOKEN}, data=data, files=files)
        r.raise_for_status()
        if r.status_code == 201:
            print("File " + r.json()['filename'] + " uploaded successfully")
            return r.json()
    except requests.exceptions.HTTPError as e:
        raise SystemExit(e)


def delete_existing_files(version_url):
    print("Deleting existing files")
    try:
        r = requests.get(version_url + '/files', params={'access_token': ZENODO_TOKEN})
        r.raise_for_status()
        files = r.json()
        for file in files:
            try:
                r = requests.delete(version_url + '/files/' + file['id'], params={'access_token': ZENODO_TOKEN})
                r.raise_for_status()
                if r.status_code == 204:
                    print("File " + file['filename'] + " deleted successfully")
            except requests.exceptions.HTTPError as e:
                raise SystemExit(e)
            except requests.exceptions.RequestException as e:
                raise SystemExit(e)
        try:
            r = requests.get(version_url + '/files', params={'access_token': ZENODO_TOKEN})
            r.raise_for_status()
            return r.json()
        except requests.exceptions.HTTPError as e:
            raise SystemExit(e)
        except requests.exceptions.RequestException as e:
            raise SystemExit(e)
    except requests.exceptions.HTTPError as e:
        raise SystemExit(e)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)


def create_zenodo_version(release_data):
    print("Creating new Zenodo version")
    id = release_data['previous_version_doi'].rsplit(".", 1)[1]
    try:
        r = requests.post(ZENODO_API_URL + 'deposit/depositions/' + id + '/actions/newversion', params={'access_token': ZENODO_TOKEN})
        r.raise_for_status()
        if r.status_code == 201:
            new_version_url = r.json()['links']['latest_draft']
            print("New version created. URL is " + new_version_url)
            existing_files = delete_existing_files(new_version_url)
            if len(existing_files) == 0:
                new_file = upload_new_file(new_version_url, release_data)
                if new_file['filename'] == release_data['filename']:
                    update_metadata(new_version_url, release_data)
                    publish_version(new_version_url)
    except requests.exceptions.HTTPError as e:
        raise SystemExit(e)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)


def check_release_data(release_data):
    file_present = "ror-data.zip" in release_data['filename']
    previous_version_doi_present = "/zenodo" in release_data['previous_version_doi']
    total_present = (len(release_data['total']) is not None) and (len(release_data['total']) > 0)
    if file_present and previous_version_doi_present and total_present:
        return True
    else:
        if not file_present:
            print("Dump file not found in ror-data")
        if not previous_version_doi_present:
            print("Previous version DOI not found in Zenodo")
        if not total_present:
            print("Total orgs count not found in release notes")
        return False

def get_previous_version_doi(parent_record_id):
    "Getting DOI for previous version"
    doi = None
    try:
        r = requests.get(ZENODO_API_URL + 'records/' + parent_record_id, params={'access_token': ZENODO_TOKEN})
        r.raise_for_status()
        if r.status_code == 200:
            doi = r.json()['doi']
        return doi
    except requests.exceptions.HTTPError as e:
        raise SystemExit(e)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)


def get_release_data(release_name, parent_id):
    release_data = {}
    release_data['filename'] = get_dump_file(release_name)
    release_data['previous_version_doi'] = get_previous_version_doi(parent_id)
    notes_data = get_release_notes_data(release_name)
    release_data['total'] = notes_data['total']
    if 'added' in notes_data:
        release_data['added'] = notes_data['added']
    if 'updated' in notes_data:
        release_data['updated'] = notes_data['updated']
    return release_data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--releasename', type=str, required=True)
    parser.add_argument('-p', '--parentrecord', type=str, required=True)
    parser.add_argument('-e', '--zenodoenv', type=str, choices=['prod', 'sandbox'], required=True)
    args = parser.parse_args()

    global ZENODO_API_URL
    global ZENODO_API_URL_PROD
    global ZENODO_TOKEN

    if args.zenodoenv == 'prod':
        ZENODO_API_URL = ZENODO_API_URL_PROD
        ZENODO_TOKEN = os.environ['ZENODO_TOKEN_PROD']
    else:
        ZENODO_API_URL = ZENODO_API_URL_SANDBOX
        ZENODO_TOKEN = os.environ['ZENODO_TOKEN_SANDBOX']

    release_data = get_release_data(args.releasename, args.parentrecord)

    if check_release_data(release_data):
        print("Release data OK")
        print(release_data)
        create_zenodo_version(release_data)
    else:
        raise Exception("Dump file name, previous version record or release notes could not be found")

if __name__ == "__main__":
    main()
