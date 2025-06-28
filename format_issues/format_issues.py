import os
import re
import json
import signal
import difflib
from contextlib import contextmanager
from google import genai
from github import Github, GithubException

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
REPO_PATH_STR = os.environ.get('GITHUB_REPOSITORY')
TARGET_REPO_PATH = os.environ.get('REPO_PATH', REPO_PATH_STR)

ISSUE_NUMBER_STR = os.environ.get('ISSUE_NUMBER')
START_ISSUE_STR = os.environ.get('START_ISSUE')
END_ISSUE_STR = os.environ.get('END_ISSUE')
DRY_RUN_STR = os.environ.get('DRY_RUN', 'false').lower()
DRY_RUN = DRY_RUN_STR in ['true', '1', 'yes']

BOT_COMMENT_SIGNATURE = "\n\n---\n*Issue body was automatically formatted by a ROR curation bot.*"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPT_FILE_PATH = os.path.join(SCRIPT_DIR, "gemini_prompt.txt")
REQUIRED_TITLE_PHRASE = 'Add a new organization to ROR'
UPDATE_TITLE_PHRASE = 'Modify the information in an existing ROR record:'


def load_prompt_template(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: Prompt template file not found at {file_path}")
        return None
    except Exception as e:
        print(f"Error reading prompt template file {file_path}: {e}")
        return None


GEMINI_PROMPT_TEMPLATE = load_prompt_template(PROMPT_FILE_PATH)


class TimeoutError(Exception):
    pass


@contextmanager
def time_limit(seconds):
    def signal_handler(signum, frame):
        raise TimeoutError(f"Process timed out after {seconds} seconds")
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)


def get_issues_to_process(repo, issue_number=None, start_issue=None, end_issue=None):
    issues_to_fetch = []
    if issue_number:
        try:
            issue = repo.get_issue(number=int(issue_number))
            if issue.state == 'open' and (REQUIRED_TITLE_PHRASE in issue.title or UPDATE_TITLE_PHRASE in issue.title):
                issues_to_fetch = [issue]
                print(f"Targeting single open issue #{issue.number} ('{issue.title}') matching title criteria.")
            else:
                print(f"Issue #{issue.number} ('{issue.title}') is either not open (state: {issue.state}) or does not contain required title phrases. Skipping.")
                return []
        except GithubException as e:
            print(f"Error fetching issue #{issue_number}: {e}")
            return []
    elif start_issue and end_issue:
        start_num = int(start_issue)
        end_num = int(end_issue)
        if start_num > end_num:
            print(f"Error: Start issue #{start_num} is greater than end issue #{end_num}.")
            return []
        print(f"Checking issue range #{start_num} to #{end_num} for open issues matching title criteria...")
        for issue_num in range(start_num, end_num + 1):
            try:
                issue = repo.get_issue(number=issue_num)
                if issue:
                    if issue.state == 'open' and (REQUIRED_TITLE_PHRASE in issue.title or UPDATE_TITLE_PHRASE in issue.title):
                        issues_to_fetch.append(issue)
                        print(f"Added open issue #{issue.number} ('{issue.title}') matching criteria to processing queue.")
                    else:
                        print(f"Skipping issue #{issue.number} ('{issue.title}'). Reason: Not open (state: {issue.state}) or title does not contain required phrases.")
            except GithubException as e:
                print(f"Error fetching issue #{issue_num}: {e}. Skipping this number.")
                continue
        if not issues_to_fetch:
            print(f"No open issues matching title criteria found in range #{start_num} to #{end_num}.")
    else:
        print("No specific issue or range provided. Processing all open issues matching title criteria.")
        open_issues = repo.get_issues(state='open')
        count = 0
        for issue in open_issues:
            if REQUIRED_TITLE_PHRASE in issue.title or UPDATE_TITLE_PHRASE in issue.title:
                issues_to_fetch.append(issue)
                count +=1
        print(f"Found {count} open issues matching title criteria.")
        if not issues_to_fetch:
             print(f"No open issues matching title criteria found in the repository.")

    return issues_to_fetch


def update_github_issue_body(issue_object, new_body_content, comment_to_add=None):
    try:
        issue_object.edit(body=new_body_content)
        print(f"Successfully updated body for issue #{issue_object.number}.")

        if comment_to_add:
            try:
                has_bot_signature_comment = False
                for comment in issue_object.get_comments():
                    if BOT_COMMENT_SIGNATURE.strip() in comment.body:
                        has_bot_signature_comment = True
                        print(f"Bot signature comment already exists on issue #{issue_object.number}. New diff comment will not be added.")
                        break
                
                if not has_bot_signature_comment:
                    issue_object.create_comment(comment_to_add)
                    print(f"Added comment with changes and bot signature to issue #{issue_object.number}.")
            except GithubException as e:
                print(f"Failed to add comment to issue #{issue_object.number}: {e}")

    except GithubException as e:
        print(f"Failed to update body for issue #{issue_object.number}: {e}")


def procedural_clean_issue_body(issue_body):
    if not issue_body:
        return issue_body
    
    lines = issue_body.split('\n')
    cleaned_lines = []
    
    for line in lines:
        stripped_line = line.strip()
        
        if not stripped_line:
            cleaned_lines.append(line)
            continue
        
        field_patterns = [
            'Name of organization:',
            'ROR ID:',
            'Which part of the record needs to be changed?',
            'Description of change:',
            'Organizations affected by this change:',
            'ROR ID(s) of organization(s) affected by this change:',
            'How should the record(s) be changed?',
            'Website:',
            'Domains:',
            'Link to publications:',
            'Organization type:',
            'Wikipedia page:',
            'Wikidata ID:',
            'ISNI ID:',
            'GRID ID:',
            'Crossref Funder ID:',
            'Aliases:',
            'Labels:',
            'Acronym/abbreviation:',
            'Related organizations:',
            'City:',
            'Country:',
            'Geonames ID:',
            'Year established:',
            'How will a ROR ID for this organization be used?',
            'Other information about this request:'
        ]
        
        is_empty_field = False
        for pattern in field_patterns:
            if stripped_line == pattern or stripped_line == pattern + ' ':
                is_empty_field = True
                break
        
        if not is_empty_field:
            cleaned_lines.append(line)
    
    cleaned_body = '\n'.join(cleaned_lines)
    
    section_headers = [
        'New record request:',
        'Update record:',
        'Merge/split/deprecate records:',
        'Add record:'
    ]
    
    for header in section_headers:
        pattern = f'\n{header}\n\n'
        if pattern in cleaned_body:
            next_section_start = len(cleaned_body)
            for other_header in section_headers:
                if other_header != header:
                    other_pattern = f'\n{other_header}\n'
                    pos = cleaned_body.find(other_pattern, cleaned_body.find(pattern) + len(pattern))
                    if pos != -1 and pos < next_section_start:
                        next_section_start = pos
            
            section_content = cleaned_body[cleaned_body.find(pattern) + len(pattern):next_section_start]
            if not section_content.strip():
                cleaned_body = cleaned_body.replace(pattern, '\n')
    
    cleaned_body = re.sub(r'\n{3,}', '\n\n', cleaned_body)
    return cleaned_body.strip()


def call_gemini_to_format_issue(issue_title, issue_body):
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY is not set. Cannot format issue.")
        return None
    if not GEMINI_PROMPT_TEMPLATE:
        print("Error: Gemini prompt template is not loaded. Cannot format issue.")
        return None

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"Error creating Gemini client: {e}")
        return None

    prompt = GEMINI_PROMPT_TEMPLATE.format(
        issue_title=issue_title, issue_body=issue_body)

    print(f"Sending request to Gemini API for issue: '{issue_title}'...")
    try:
        with time_limit(120):
            response = client.models.generate_content(
                model='gemini-2.5-flash-preview-05-20',
                contents=prompt
            )
            formatted_body = response.text
            if formatted_body.startswith("```markdown\n"):
                formatted_body = formatted_body[len("```markdown\n"):]
            if formatted_body.startswith("```\n"):
                formatted_body = formatted_body[len("```\n"):]
            if formatted_body.endswith("\n```"):
                formatted_body = formatted_body[:-len("\n```")]
            print("Successfully received response from Gemini API.")
            return formatted_body.strip()
    except TimeoutError as e:
        print(f"Gemini API call timed out: {e}")
        return None
    except Exception as e:
        print(f"An error occurred with the Gemini API: {e}")
        return None


def process_single_issue(issue_object):
    print(f"\n--- Processing Issue #{issue_object.number}: {issue_object.title} ---")
    original_body = issue_object.body if issue_object.body else ""

    if not original_body.strip():
        print(f"Issue #{issue_object.number} has an empty body. Skipping processing.")
        return

    if BOT_COMMENT_SIGNATURE in original_body:
        print(f"Issue #{issue_object.number} body already contains bot signature. Skipping re-formatting.")
        return

    is_update_request = UPDATE_TITLE_PHRASE in issue_object.title
    
    if is_update_request:
        print(f"Processing update request issue #{issue_object.number} with procedural cleaning...")
        formatted_body = procedural_clean_issue_body(original_body)
        processing_method = "procedural cleaning"
    else:
        print(f"Processing new record request issue #{issue_object.number} with Gemini API...")
        formatted_body = call_gemini_to_format_issue(issue_object.title, original_body)
        processing_method = "Gemini API"

    if formatted_body:
        if formatted_body.strip() == original_body.strip():
            print(f"{processing_method.title()} proposed no changes to the body of issue #{issue_object.number}.")
        else:
            print(f"{processing_method.title()} proposed changes for issue #{issue_object.number}.")

            diff_lines = difflib.unified_diff(
                original_body.splitlines(keepends=True),
                formatted_body.splitlines(keepends=True),
                fromfile='Original Body',
                tofile='Formatted Body',
                lineterm=''
            )
            diff_text = "".join(diff_lines)
            
            comment_with_diff = None
            if diff_text:
                comment_intro = (
                    f"Review the issue updates below:\n\n"
                )
                diff_markdown_block = f"```diff\n{diff_text}\n```"
                comment_with_diff = f"{comment_intro}{diff_markdown_block}\n{BOT_COMMENT_SIGNATURE}"

            if DRY_RUN:
                print(f"DRY RUN: Would update issue #{issue_object.number} with new body:")
                print("---------- Proposed New Body ----------")
                print(formatted_body)
                print("--------------------------------------")
                if comment_with_diff:
                    print("---------- Proposed Comment with Diff ----------")
                    print(comment_with_diff)
                    print("---------------------------------------------")
                elif diff_text:
                    print("DRY RUN: Diff was generated but comment was not formed. Diff:")
                    print(diff_text)
            else:
                update_github_issue_body(
                    issue_object, formatted_body, comment_to_add=comment_with_diff
                )
    else:
        print(f"Failed to get formatted body using {processing_method} for issue #{issue_object.number}.")


def main():
    print("Starting ROR Issue Formatting Action...")
    print(f"Target Repository: {TARGET_REPO_PATH}")
    print(f"Dry Run: {DRY_RUN}")

    if not GEMINI_PROMPT_TEMPLATE:
        print("Critical Error: Gemini prompt template could not be loaded. Exiting.")
        return

    if not GITHUB_TOKEN:
        print("Error: GITHUB_TOKEN environment variable not set.")
        return
    if not GEMINI_API_KEY:
        print("Warning: GEMINI_API_KEY environment variable not set. Formatting will be skipped.")
    if not TARGET_REPO_PATH:
        print("Error: Target repository (REPO_PATH or GITHUB_REPOSITORY) not specified.")
        return
    
    if ISSUE_NUMBER_STR and (START_ISSUE_STR or END_ISSUE_STR):
        print("Error: Cannot specify both single issue (ISSUE_NUMBER) and issue range (START_ISSUE, END_ISSUE).")
        return

    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(TARGET_REPO_PATH)
    except Exception as e:
        print(f"Error connecting to GitHub or repository {TARGET_REPO_PATH}: {e}")
        return

    issues = get_issues_to_process(
        repo,
        issue_number=ISSUE_NUMBER_STR,
        start_issue=START_ISSUE_STR,
        end_issue=END_ISSUE_STR
    )

    if not issues:
        print("No issues found to process.")
        return

    print(f"Found {len(issues)} issue(s) to process.")
    for issue in issues:
        process_single_issue(issue)

    print("\nROR Issue Formatting Action finished.")


if __name__ == '__main__':
    main()