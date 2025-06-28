import os
import re
import signal
from github import Github, GithubException
from triage import triage
from encode_updates import encode_update
from validate_encoding import validate_encoding
from contextlib import contextmanager

TOKEN = os.environ.get('GITHUB_TOKEN')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
BOT_NAME = "ror-curator-bot"

ALL_MAJOR_SECTION_HEADERS = [
    "Summary of request:",
    "Update record:",
    "Merge/split/deprecate records:",
    "Add record:",
    "Other information about this request:"
]


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


def get_section_content(issue_body, current_section_header_literal):
    print(f"DEBUG_GET_SECTION: Called with current_section_header_literal: '{current_section_header_literal}'")

    start_pattern = rf"^{re.escape(current_section_header_literal)}\s*"
    lookahead_terms = []
    for h in ALL_MAJOR_SECTION_HEADERS:
        if h.lower() != current_section_header_literal.lower():
            lookahead_terms.append(rf"\n^\s*{re.escape(h)}\s*")

    if not lookahead_terms:
        end_lookahead_pattern_str = r"$"
    else:
        end_lookahead_pattern_str = rf"(?:{'|'.join(lookahead_terms)})|$"
    
    full_regex_str = rf"{start_pattern}([\s\S]*)(?={end_lookahead_pattern_str})"

    if current_section_header_literal == "Update record:":
        print(f"DEBUG_GET_SECTION (Update record): Compiling regex: '{full_regex_str}'")
        print(f"DEBUG_GET_SECTION (Update record): ALL_MAJOR_SECTION_HEADERS was: {ALL_MAJOR_SECTION_HEADERS}")
        print(f"DEBUG_GET_SECTION (Update record): Lookahead terms generated: {lookahead_terms}")

    try:
        pattern = re.compile(full_regex_str, re.MULTILINE | re.IGNORECASE)
    except Exception as e:
        print(f"DEBUG_GET_SECTION: ERROR COMPILING REGEX: {e}")
        print(f"DEBUG_GET_SECTION: Faulty regex string was: {full_regex_str}")
        return None

    match = pattern.search(issue_body)

    if match:
        if current_section_header_literal == "Update record:":
            print(f"DEBUG_GET_SECTION (Update record): Match found!")
            try:
                print(f"DEBUG_GET_SECTION (Update record): match.group(0) (whole match):\n>>>\n{match.group(0)}\n<<<")
                print(f"DEBUG_GET_SECTION (Update record): match.group(1) (captured content before strip):\n>>>\n{match.group(1)}\n<<<")
            except IndexError:
                print(f"DEBUG_GET_SECTION (Update record): Match found, but error accessing groups.")
        
        return match.group(1).strip()
    else:
        if current_section_header_literal == "Update record:":
            print(f"DEBUG_GET_SECTION (Update record): No match found by pattern.search().")
    return None


def process_issue_details(issue):
    processed_issue = None
    issue_body = issue.body if issue.body else ""
    labels = [label.name for label in issue.labels if label.name]
    excluded_labels = ['bug', 'enhancement', 'question', 'help', 'duplicate', 'wontfix', 'invalid', 'good first issue']
    org_labels = [label for label in labels if not label.lower() in excluded_labels]
    print(f"DEBUG: Extracted labels from issue #{issue.number}: {labels}")
    print(f"DEBUG: Filtered organization labels: {org_labels}")

    name_pattern = r"Name of organization:[ \t]*([^\n]*)"
    aliases_pattern = r"Aliases:[ \t]*([^\n]*)"
    labels_pattern = r"Labels:[ \t]*([^\n]*)"
    website_pattern = r"Website:[ \t]*([^\n]*)"
    city_pattern = r"City:[ \t]*([^\n]*)"
    country_pattern = r"Country:[ \t]*([^\n]*)"
    ror_id_field_pattern = r"ROR ID:[ \t]*(https://ror\.org/(0[a-z0-9]{6}[0-9]{2})|(0[a-z0-9]{6}[0-9]{2}))"
    ror_id_general_pattern = r"(https://ror\.org/0[a-z0-9]{6}[0-9]{2})\b|\b(0[a-z0-9]{6}[0-9]{2})\b"
    description_of_change_section_pattern = r"Description of change:\s*([\s\S]*?)(?=\n(?:Merge\/split\/deprecate records:|Additional information:)|$)"

    if 'Add a new' in issue.title:
        active_section_content = get_section_content(issue_body, "Add record:")
        if not active_section_content:
            print(f"Warning: Could not isolate 'Add record:' section for issue #{issue.number}. Fallback may occur or parsing may fail.")
            active_section_content = issue_body

        if active_section_content:
            organization_name = get_matched_value(
                name_pattern, active_section_content)
            aliases = get_matched_value(
                aliases_pattern, active_section_content)
            labels_from_body = get_matched_value(
                labels_pattern, active_section_content)
            website = get_matched_value(
                website_pattern, active_section_content)
            city = get_matched_value(city_pattern, active_section_content)
            country = get_matched_value(
                country_pattern, active_section_content)

            all_labels = org_labels.copy() if org_labels else []
            if labels_from_body:
                body_labels = [label.strip() for label in re.split(r'[;,]', labels_from_body) if label.strip()]
                all_labels.extend(body_labels)

            if organization_name:
                processed_issue = {'issue_number': issue.number, 'body': issue_body,
                                   'name': organization_name, 'aliases': aliases, 'labels': all_labels, 'url': website,
                                   'city': city, 'country': country, 'type': 'new', 'issue_object': issue}
            else:
                print(f"Issue #{issue.number} (Add new): 'Name of organization' not found in the relevant section.")
        else:
            print(f"Issue #{issue.number} (Add new): Could not find or parse 'Add record:' section.")

    elif 'Modify the information' in issue.title:
        print("DEBUG: Entered 'Modify the information' block.")
        print(f"DEBUG: Raw issue_body received by process_issue_details:\n>>>\n{issue_body}\n<<<")

        update_record_section_content = get_section_content(issue_body, "Update record:")
        print(f"DEBUG: update_record_section_content from get_section_content:\n>>>\n{update_record_section_content}\n<<<")

        other_info_section_content = get_section_content(issue_body, "Other information about this request:")
        print(f"DEBUG: other_info_section_content from get_section_content:\n>>>\n{other_info_section_content}\n<<<")

        if not update_record_section_content:
            print(f"DEBUG: update_record_section_content is None or empty. Falling back to full issue_body for parsing_content_for_update_fields.")
            parsing_content_for_update_fields = issue_body
        else:
            parsing_content_for_update_fields = update_record_section_content
        
        print(f"DEBUG: parsing_content_for_update_fields:\n>>>\n{parsing_content_for_update_fields}\n<<<")
        
        organization_name = get_matched_value(name_pattern, parsing_content_for_update_fields)
        print(f"DEBUG: Extracted organization_name: '{organization_name}'")

        ror_id = None
        ror_id_field_match = re.search(ror_id_field_pattern, parsing_content_for_update_fields, re.IGNORECASE)
        if ror_id_field_match:
            ror_id_value = ror_id_field_match.group(2) or ror_id_field_match.group(3)
            if ror_id_value:
                 ror_id = "https://ror.org/" + ror_id_value
            print(f"DEBUG: ROR ID from field_match: '{ror_id}' (value: '{ror_id_value}')")
        else:
            print(f"DEBUG: ROR ID field_match failed. Trying general pattern.")
            ror_id_general_match = re.search(ror_id_general_pattern, issue_body, re.IGNORECASE | re.MULTILINE)
            if ror_id_general_match:
                if ror_id_general_match.group(1):
                    ror_id = ror_id_general_match.group(1)
                elif ror_id_general_match.group(2):
                    ror_id = "https://ror.org/" + ror_id_general_match.group(2)
                print(f"DEBUG: ROR ID from general_match: '{ror_id}'")
            else:
                print(f"DEBUG: ROR ID general_match also failed.")
        
        if ror_id:
            ror_id = ror_id.strip()
        print(f"DEBUG: Final ROR ID after strip: '{ror_id}'")

        description_of_change = None
        print(f"DEBUG: About to search for description. Pattern: '{description_of_change_section_pattern}' on parsing_content_for_update_fields")
        desc_match = re.search(description_of_change_section_pattern, parsing_content_for_update_fields)
        if desc_match:
            print(f"DEBUG: desc_match for description found.")
            print(f"DEBUG: desc_match.group(0):\n>>>\n{desc_match.group(0)}\n<<<")
            print(f"DEBUG: desc_match.group(1) (before strip):\n>>>\n{desc_match.group(1)}\n<<<")
            description_of_change = desc_match.group(1).strip()
            print(f"DEBUG: description_of_change from pattern (after strip): '{description_of_change}'")
        else:
            print("DEBUG: desc_match for description NOT found.")
            description_of_change = None 

        if other_info_section_content:
            print(f"DEBUG: other_info_section_content is not empty ('{other_info_section_content}'). Considering for description.")
            if not description_of_change or len(description_of_change) < 20:
                print(f"DEBUG: description_of_change is short or empty. Appending other_info.")
                full_description = other_info_section_content
                if description_of_change:
                    full_description = description_of_change + "\n\n--- Additional Information ---\n" + other_info_section_content
                description_of_change = full_description.strip()
            elif description_of_change: 
                 print(f"DEBUG: description_of_change is not short. Appending other_info.")
                 description_of_change += "\n\n--- Additional Information ---\n" + other_info_section_content
                 description_of_change = description_of_change.strip()
        else:
            print(f"DEBUG: other_info_section_content is empty. Not appending to description.")
        
        print(f"DEBUG: Final description_of_change before check: '{description_of_change}'")

        if ror_id and description_of_change:
            processed_issue = {'issue_number': issue.number, 'ror_id': ror_id,
                               'name': organization_name, 'labels': org_labels,
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
        "Publication affiliation usage", "Author count by affiliation",
        "Potential aliases", "ORCID affiliation usage", "Possible ROR matches", 
        "Previous requests", "Geonames match"
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


def process_single_issue(issue_object, repo_path_str, skip_commented=True):
    if skip_commented and issue_has_bot_comment(issue_object):
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
                triage_input_data = {
                    k: v for k, v in processed_details.items() if k != 'issue_object'}

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
                if not GEMINI_API_KEY:
                    print("Error: GEMINI_API_KEY is not set. Cannot encode update.")
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
                else:
                    print(f"No encoding generated for update on issue #{issue_object.number}")

    except TimeoutError:
        print(f'Timed out while processing issue #{processed_details["issue_number"]}')
    except Exception as e:
        print(f'An unexpected error occurred while processing issue #{processed_details["issue_number"]}: {e}')
        import traceback
        traceback.print_exc()


def get_issues_to_process(repo, issue_number=None, start_issue=None, end_issue=None):
    """Get list of issues to process based on parameters"""
    issues = []
    
    if issue_number:
        try:
            issue = repo.get_issue(number=int(issue_number))
            issues = [issue]
            print(f"Processing single issue #{issue.number}: {issue.title}")
        except Exception as e:
            print(f"Error fetching issue #{issue_number}: {e}")
            return []
    
    elif start_issue and end_issue:
        start_num = int(start_issue)
        end_num = int(end_issue)
        print(f"Processing issue range #{start_num} to #{end_num}")
        
        for issue_num in range(start_num, end_num + 1):
            try:
                issue = repo.get_issue(number=issue_num)
                if issue.state == 'open' and ('Add a new' in issue.title or 'Modify the information' in issue.title):
                    issues.append(issue)
                    print(f"Added issue #{issue.number} to processing queue")
                else:
                    print(f"Skipping issue #{issue.number} - not open or doesn't match criteria")
            except Exception as e:
                print(f"Error fetching issue #{issue_num}: {e}")
                continue
    
    return issues


def main():
    issue_number_str = os.environ.get('ISSUE_NUMBER')
    start_issue_str = os.environ.get('START_ISSUE')
    end_issue_str = os.environ.get('END_ISSUE')
    skip_commented_str = os.environ.get('SKIP_COMMENTED', 'true').lower()
    repo_path_str = os.environ.get('GITHUB_REPOSITORY')
    github_token = os.environ.get('GITHUB_TOKEN')
    skip_commented = skip_commented_str in ['true', '1', 'yes']

    if not repo_path_str or not github_token:
        print("Error: Missing required environment variables (GITHUB_REPOSITORY, GITHUB_TOKEN).")
        return
    if issue_number_str and (start_issue_str or end_issue_str):
        print("Error: Cannot specify both single issue and issue range")
        return
    
    if not issue_number_str and (not start_issue_str or not end_issue_str):
        print("Error: Must specify either ISSUE_NUMBER or both START_ISSUE and END_ISSUE")
        return

    global TOKEN, GEMINI_API_KEY
    TOKEN = github_token
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    
    if not GEMINI_API_KEY:
        print("Warning: GEMINI_API_KEY environment variable is not set. Update encoding will likely fail.")

    print(f"Initializing GitHub client for repository: {repo_path_str}")
    print(f"Skip commented issues: {skip_commented}")
    
    g = Github(github_token)

    try:
        repo = g.get_repo(repo_path_str)
        issues = get_issues_to_process(
            repo, 
            issue_number=issue_number_str,
            start_issue=start_issue_str, 
            end_issue=end_issue_str
        )
        
        if not issues:
            print("No issues found to process")
            return
            
        print(f"Found {len(issues)} issue(s) to process")
        
        for issue in issues:
            print(f"\n--- Processing issue #{issue.number}: {issue.title} ---")
            process_single_issue(issue, repo_path_str, skip_commented)
            
        print(f"\nCompleted processing {len(issues)} issue(s)")
        
    except Exception as e:
        print(f"Error accessing repository or processing issues: {e}")
        return


if __name__ == '__main__':
    print("Starting enhanced issue triage process...")
    main()
    print("Enhanced issue triage process finished.")