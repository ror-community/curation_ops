import os
import re
import json
import signal
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

BOT_COMMENT_SIGNATURE = "\n\n---\n*This issue body was automatically formatted by the ROR Curator Bot.*"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPT_FILE_PATH = os.path.join(SCRIPT_DIR, "gemini_prompt.txt")


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
            if issue.state == 'open' and 'Add a new organization to ROR' in issue.title:
                issues_to_fetch = [issue]
                print(f"Targeting single open issue #{issue.number} ('{issue.title}') matching title criteria.")
            else:
                print(f"Issue #{issue.number} ('{issue.title}') is either not open (state: {issue.state}) or does not contain '{REQUIRED_TITLE_PHRASE}' in its title. Skipping.")
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
        print(f"Checking issue range #{start_num} to #{end_num} for open issues matching title criteria ('{REQUIRED_TITLE_PHRASE}')...")
        for issue_num in range(start_num, end_num + 1):
            try:
                issue = repo.get_issue(number=issue_num)
                if issue:
                    if issue.state == 'open' and REQUIRED_TITLE_PHRASE in issue.title:
                        issues_to_fetch.append(issue)
                        print(f"Added open issue #{issue.number} ('{issue.title}') matching criteria to processing queue.")
                    else:
                        print(f"Skipping issue #{issue.number} ('{issue.title}'). Reason: Not open (state: {issue.state}) or title does not contain '{REQUIRED_TITLE_PHRASE}'.")
            except GithubException as e:
                print(f"Error fetching issue #{issue_num}: {e}. Skipping this number.")
                continue
    else:
        print("No specific issue or range provided. Exiting.")
        return []


def update_github_issue_body(issue_object, new_body_content, add_comment=True):
    try:
        issue_object.edit(body=new_body_content)
        print(f"Successfully updated body for issue #{issue_object.number}.")
        if add_comment:
            try:
                has_bot_signature = False
                for comment in issue_object.get_comments():
                    if BOT_COMMENT_SIGNATURE.strip() in comment.body:
                        has_bot_signature = True
                        print(f"Bot signature comment already exists on issue #{issue_object.number}.")
                        break
                if not has_bot_signature:
                    issue_object.create_comment(BOT_COMMENT_SIGNATURE)
                    print(f"Added bot signature comment to issue #{issue_object.number}.")
            except GithubException as e:
                print(f"Failed to add comment to issue #{issue_object.number}: {e}")

    except GithubException as e:
        print(f"Failed to update body for issue #{issue_object.number}: {e}")


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
                model='gemini-2.5-flash',
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
        print(f"Issue #{issue_object.number} has an empty body. Skipping Gemini processing.")
        return

    if BOT_COMMENT_SIGNATURE in original_body:
        print(f"Issue #{issue_object.number} body already contains bot signature. Skipping re-formatting.")

    formatted_body = call_gemini_to_format_issue(
        issue_object.title, original_body)

    if formatted_body:
        if formatted_body.strip() == original_body.strip():
            print(f"Gemini proposed no changes to the body of issue #{issue_object.number}.")
        else:
            print(f"Gemini proposed changes for issue #{issue_object.number}.")
            if DRY_RUN:
                print(f"DRY RUN: Would update issue #{issue_object.number} with new body:")
                print("---------- Proposed New Body ----------")
                print(formatted_body)
                print("--------------------------------------")
            else:
                final_body_to_update = formatted_body
                update_github_issue_body(
                    issue_object, final_body_to_update, add_comment=True)
    else:
        print(f"Failed to get formatted body from Gemini for issue #{issue_object.number}.")


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
    if not ISSUE_NUMBER_STR and not (START_ISSUE_STR and END_ISSUE_STR):
        print("Error: Must specify either ISSUE_NUMBER or both START_ISSUE and END_ISSUE.")
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
