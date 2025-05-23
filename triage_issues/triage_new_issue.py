import os
import re
import signal
from github import Github, GithubException
from triage import triage 
from encode_updates import encode_update
from validate_encoding import validate_encoding
from contextlib import contextmanager

TOKEN = os.environ.get('GITHUB_TOKEN')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
BOT_NAME = "ror-curator-bot"


def timeout_handler(signum, frame):
    raise TimeoutError("Process timed out")


@contextmanager
def time_limit(seconds):
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)


def get_matched_value(pattern, text):
    if text is None:
        return None
    match = re.search(pattern, text)
    if match:
        return match.group(1).strip()
    else:
        match = re.search(pattern, text, re.DOTALL)
        return match.group(1).strip() if match else None


def issue_has_bot_comment(issue, bot_name=BOT_NAME):
    try:
        for comment in issue.get_comments():
            if comment.user and comment.user.login == bot_name:
                print(f"Bot comment found from {bot_name} on issue #{issue.number}")
                return True
    except GithubException as e:
        print(f"Error fetching comments for issue #{issue.number}: {e}")
    return False


def get_section_content(issue_body, section_name):
    section_header = f"{section_name}:"
    pattern = re.compile(
        rf"^{re.escape(section_header)}\s*([\s\S]*?)"
        rf"(?=(?:\n^\s*(?:Name of organization|ROR ID|Which part of the record needs to be changed|Description of change|Merge\/split\/deprecate records|Organizations affected by this change|How should the record\(s\) be changed|Add record|Website|Domains|Link to publications|Organization type|Wikipedia page|Wikidata ID|ISNI ID|GRID ID|Crossref Funder ID|Aliases|Labels|Acronym\/abbreviation|Related organizations|City|Country|Geonames ID|Year established|How will a ROR ID|Other information about this request):\s*)|$)",
        re.MULTILINE | re.IGNORECASE
    )
    match = pattern.search(issue_body)
    if match:
        return match.group(1).strip()
    return None


def process_issue_details(issue):
    processed_issue = None
    issue_body = issue.body if issue.body else ""

    name_pattern = r"Name of organization:[ \t]*([^\n]*)"
    aliases_pattern = r"Aliases:[ \t]*([^\n]*)"
    website_pattern = r"Website:[ \t]*([^\n]*)"
    city_pattern = r"City:[ \t]*([^\n]*)"
    country_pattern = r"Country:[ \t]*([^\n]*)"

    ror_id_field_pattern = r"ROR ID:[ \t]*(https://ror\.org/(0[a-z0-9]{6}[0-9]{2})|(0[a-z0-9]{6}[0-9]{2}))"
    ror_id_general_pattern = r"(https://ror\.org/0[a-z0-9]{6}[0-9]{2})\b|\b(0[a-z0-9]{6}[0-9]{2})\b"

    description_of_change_section_pattern = r"Description of change:\s*([\s\S]*?)(?=\n(?:Merge\/split\/deprecate records:|Additional information:)|$)"

    if 'Add a new' in issue.title:
        active_section_content = get_section_content(issue_body, "Add record")
        if not active_section_content:
            print(f"Warning: Could not isolate 'Add record:' section for issue #{issue.number}. Attempting to parse from full body as fallback.")
            active_section_content = issue_body 

        if active_section_content:
            organization_name = get_matched_value(name_pattern, active_section_content)
            aliases = get_matched_value(aliases_pattern, active_section_content)
            website = get_matched_value(website_pattern, active_section_content)
            city = get_matched_value(city_pattern, active_section_content)
            country = get_matched_value(country_pattern, active_section_content)

            if organization_name: 
                processed_issue = {'issue_number': issue.number, 'body': issue_body,
                                   'name': organization_name, 'aliases': aliases, 'url': website,
                                   'city': city, 'country': country, 'type': 'new', 'issue_object': issue}
            else:
                print(f"Issue #{issue.number} (Add new): 'Name of organization' not found in the relevant section.")
        else:
            print(f"Issue #{issue.number} (Add new): Could not find or parse 'Add record:' section.")

    elif 'Modify the information' in issue.title:
        update_record_section_content = get_section_content(issue_body, "Update record")
        other_info_section_content = get_section_content(issue_body, "Other information about this request")

        if not update_record_section_content:
            print(f"Warning: Could not isolate 'Update record:' section for issue #{issue.number}. Attempting to parse from full body as fallback.")
            parsing_content_for_update_fields = issue_body
        else:
            parsing_content_for_update_fields = update_record_section_content

        organization_name = get_matched_value(name_pattern, parsing_content_for_update_fields)

        ror_id = None
        ror_id_field_match = re.search(ror_id_field_pattern, parsing_content_for_update_fields, re.IGNORECASE)
        if ror_id_field_match:
            ror_id_value = ror_id_field_match.group(2) or ror_id_field_match.group(3)
            if ror_id_value:
                ror_id = "https://ror.org/" + ror_id_value
        else:
            ror_id_general_match = re.search(ror_id_general_pattern, issue_body, re.IGNORECASE | re.MULTILINE)
            if ror_id_general_match:
                if ror_id_general_match.group(1): 
                    ror_id = ror_id_general_match.group(1)
                elif ror_id_general_match.group(2): 
                    ror_id = "https://ror.org/" + ror_id_general_match.group(2)
        
        if ror_id:
            ror_id = ror_id.strip()

        description_of_change = None
        desc_match = re.search(description_of_change_section_pattern, parsing_content_for_update_fields)
        if desc_match:
            description_of_change = desc_match.group(1).strip()

        if other_info_section_content:
            if not description_of_change or len(description_of_change) < 20: 
                full_description = other_info_section_content
                if description_of_change: 
                    full_description = description_of_change + "\n\n--- Additional Information ---\n" + other_info_section_content
                description_of_change = full_description.strip()
            elif description_of_change: 
                description_of_change += "\n\n--- Additional Information ---\n" + other_info_section_content
                description_of_change = description_of_change.strip()


        if ror_id and description_of_change:
            processed_issue = {'issue_number': issue.number, 'ror_id': ror_id,
                               'name': organization_name, 
                               'change': description_of_change,
                               'type': 'update', 'issue_object': issue}
        else:
            print(f"Could not extract required ROR ID or full description of change for update issue #{issue.number}.")
            if not ror_id:
                print(f"ROR ID missing or malformed for issue #{issue.number}.")
            if not description_of_change:
                print(f"Description of change missing or empty for issue #{issue.number} (even after checking 'Other information').")
    else:
        print(f"Issue #{issue.number} title '{issue.title}' does not match 'Add a new' or 'Modify the information'. Skipping detailed parsing.")

    return processed_issue


def convert_dict_to_comment(d):
    comment_parts = []
    preferred_order = [
        "Wikidata Name", "Wikidata ID", "Wikidata name match ratio", "wikipedia_url",
        "Wikidata Established", "Wikidata Admin territory name", "Wikidata Admin territory Geonames ID",
        "Wikidata City", "Wikidata City Geonames ID", "Wikidata Country", "Wikidata links",
        "Wikidata GRID ID", "Wikidata ROR ID", "Wikidata ISNI ID", "ISNI", "Funder ID",
        "Publication affiliation usage", "Potential aliases", "ORCID affiliation usage",
        "Possible ROR matches", "Previous requests", "Geonames match"
    ]

    temp_dict = d.copy() 
    if 'issue_object' in temp_dict:
        del temp_dict['issue_object']


    for key in preferred_order:
        if key in temp_dict and temp_dict[key]: 
            value = temp_dict[key]
            if isinstance(value, list):
                value_str = '; '.join(map(str, value))
            elif isinstance(value, dict):
                value_str = '; '.join([f"{sub_k}: {sub_v}" for sub_k, sub_v in value.items()])
            else:
                value_str = str(value)
            comment_parts.append(f'**{key}**: {value_str}')
            del temp_dict[key] 

    for key, value in temp_dict.items():
        if value: 
            if isinstance(value, list):
                value_str = '; '.join(map(str, value))
            elif isinstance(value, dict):
                value_str = '; '.join([f"{sub_k}: {sub_v}" for sub_k, sub_v in value.items()])
            else:
                value_str = str(value)
            comment_parts.append(f'**{key}**: {value_str}')
            
    return '\n'.join(comment_parts).strip()


def add_comment_to_issue_object(issue_object, comment_text):
    try:
        issue_object.create_comment(comment_text)
        print(f'Added comment to issue #{issue_object.number}')
    except GithubException as e:
        print(f"Failed to add comment to issue #{issue_object.number}: {e}")


def process_single_issue(issue_object, repo_path_str): 
    if issue_has_bot_comment(issue_object):
        print(f"Skipping issue #{issue_object.number} as it already has a bot comment from {BOT_NAME}")
        return

    processed_details = process_issue_details(issue_object)
    if not processed_details:
        print(f"Could not process details for issue #{issue_object.number} into a structured format, skipping automated comment.")
        return

    try:
        if processed_details['type'] == 'new':
            with time_limit(300): 
                print(f'Triaging new record request - issue #{processed_details["issue_number"]}...')
                triage_input_data = {k: v for k, v in processed_details.items() if k != 'issue_object'}
                
                if 'body' not in triage_input_data and 'body' in processed_details:
                        triage_input_data['body'] = processed_details['body']

                triaged_record = triage(triage_input_data) 
                if triaged_record:
                    triaged_comment = convert_dict_to_comment(triaged_record)
                    if triaged_comment:
                        add_comment_to_issue_object(
                            issue_object, triaged_comment)
                    else:
                        print(f"No comment generated from triage data for new record on issue #{issue_object.number}")
                else:
                    print(f"Triage returned no data for new record issue #{issue_object.number}")

        elif processed_details['type'] == 'update':
            with time_limit(300): 
                print(f'Triaging update record request - issue #{processed_details["issue_number"]}...')
                if not OPENAI_API_KEY:
                    print("Error: OPENAI_API_KEY is not set. Cannot encode update.")
                    add_comment_to_issue_object(
                        issue_object, "Error: System configuration issue (OPENAI_API_KEY not set). Cannot process update encoding.")
                    return

                update_encoding = encode_update(
                    processed_details['ror_id'], processed_details['change'])
                if update_encoding:
                    validated_update = validate_encoding(update_encoding)
                    if validated_update:
                        add_comment_to_issue_object(
                            issue_object, validated_update)
                    else:
                        print(f"Invalid encoding generated for issue #{issue_object.number}. Original: {update_encoding}")
                        add_comment_to_issue_object(issue_object, f"Error: Generated encoding was invalid and could not be corrected. Original attempt: `{update_encoding}`. Needs manual review.")
                else:
                    print(f"No encoding generated for update on issue #{issue_object.number}")
                    add_comment_to_issue_object(
                        issue_object, "Error: Could not generate an update encoding. Needs manual review.")

    except TimeoutError:
        print(f'Timed out while processing issue #{processed_details["issue_number"]}')
        add_comment_to_issue_object(
            issue_object, "Error: Processing timed out. Needs manual review.")
    except Exception as e:
        print(f'An unexpected error occurred while processing issue #{processed_details["issue_number"]}: {e}')
        import traceback
        traceback.print_exc()
        add_comment_to_issue_object(issue_object, f"An unexpected error occurred: {str(e)}. Needs manual review.")


def main():
    issue_number_str = os.environ.get('ISSUE_NUMBER')
    repo_path_str = os.environ.get('GITHUB_REPOSITORY')
    github_token = os.environ.get('GITHUB_TOKEN')

    if not issue_number_str or not repo_path_str or not github_token:
        print("Error: Missing required environment variables (ISSUE_NUMBER, GITHUB_REPOSITORY, GITHUB_TOKEN).")
        return

    global TOKEN 
    TOKEN = github_token

    global OPENAI_API_KEY 
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    if not OPENAI_API_KEY:
        print("Warning: OPENAI_API_KEY environment variable is not set. Update encoding will likely fail.")

    try:
        issue_number = int(issue_number_str)
    except ValueError:
        print(f"Error: Invalid ISSUE_NUMBER: {issue_number_str}. Must be an integer.")
        return

    print(f"Initializing GitHub client for repository: {repo_path_str}, issue: {issue_number}")
    g = Github(github_token)

    try:
        repo = g.get_repo(repo_path_str)
        issue = repo.get_issue(number=issue_number)
        print(f"Successfully fetched issue #{issue.number}: {issue.title}")
    except Exception as e:
        print(f"Error fetching repository or issue: {e}")
        return

    process_single_issue(issue, repo_path_str)


if __name__ == '__main__':
    print("Starting issue triage process via GitHub Action trigger...")
    main()
    print("Issue triage process finished.")