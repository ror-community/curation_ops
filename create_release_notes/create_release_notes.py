import os
import json
import requests
import argparse


def get_ror_display_name(record):
    return [name['value'] for name in record.get('names', []) if 'ror_display' in name.get('types', [])][0]


def parse_arguments():
    parser = argparse.ArgumentParser(description="Generate ROR release text")
    parser.add_argument('-r', '--release', required=True,
                        help="Release number")
    parser.add_argument('-m', '--milestone', required=True,
                        help="Milestone number")
    parser.add_argument('-d', '--directory', required=True,
                        help="Directory path")
    parser.add_argument('-o', '--output', default="release_notes.md",
                        help="Output file name (default: release_notes.md)")
    parser.add_argument('-p', '--print', action='store_true',
                        help="Print to console instead of writing to file")
    return parser.parse_args()


def create_release_text(release_number, milestone_number, directory):
    base_url = "https://api.ror.org/organizations?all_status"
    new_dir = os.path.join(directory, "new")
    updates_dir = os.path.join(directory, "updates")
    response = requests.get(base_url)
    data = response.json()
    total_organizations = data["number_of_results"]
    new_records = [f for f in os.listdir(new_dir) if f.endswith(".json")]
    count_added = len(new_records)
    updated_records = [f for f in os.listdir(
        updates_dir) if f.endswith(".json")]
    count_updated = len(updated_records)
    total_organizations += count_added

    def parse_records(directory, records):
        result = ""
        for record in records:
            with open(os.path.join(directory, record), "r") as f:
                record_data = json.load(f)
                record_name = get_ror_display_name(record_data)
                result += f"{record_data['id']}|{record_name}\n"
        return result

    added_text = parse_records(new_dir, new_records)
    updated_text = parse_records(updates_dir, updated_records)

    text = f"""# **ROR Release {release_number}**
- **Total organizations**: {total_organizations}
- **Records added**: {count_added}
- **Records updated**: {count_updated}

Access data in this release via the [ROR API](https://api.ror.org/organizations) ([documentation](https://ror.readme.io/docs/rest-api)), [ROR search](https://ror.org/search) ([documentation](https://ror.readme.io/docs/web-search-interface)), and [ROR data dump](https://zenodo.org/communities/ror-data) ([documentation](https://ror.readme.io/docs/data-dump)).

All changes were processed by ROR's [curation advisory board](https://ror.org/governance/#curation-advisory-board) and ROR's core team in accordance with [ROR's curation policies and workflows](https://github.com/ror-community/ror-updates#readme). For more information about the changes in this release, see the issues in [this milestone](https://github.com/ror-community/ror-updates/milestone/{milestone_number}).

# **Records added** 
ROR ID | Organization name
-- | --
{added_text}

# **Records updated** 
ROR ID | Organization name
-- | --
{updated_text}
"""
    return text


if __name__ == '__main__':
    args = parse_arguments()
    release_text = create_release_text(
        args.release, args.milestone, args.directory)

    if args.print:
        print(release_text)
    else:
        with open(args.output, 'w') as f:
            f.write(release_text)
        print(f"Release notes written to {args.output}")
