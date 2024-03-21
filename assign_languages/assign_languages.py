import os
import re
import argparse
import fasttext
from iso639 import Lang
from github import Github

MODEL_PATH = "lid.176.bin"
fasttext.FastText.eprint = lambda x: None
detector = fasttext.load_model(MODEL_PATH)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Update GitHub issue with assigned languages for name and aliases.")
    parser.add_argument("-i", "--issue_number", type=int,
                        required=True, help="GitHub issue number")
    parser.add_argument("-r", "--repo_name", type=str,default='ror-community/ror-updates', help="GitHub repository name")
    return parser.parse_args()


def get_issue_body(repo, issue_number):
    issue = repo.get_issue(issue_number)
    return issue.body


def extract_name_and_aliases(issue_body):
    name_pattern = re.compile(r"Name of organization:\s*(.*)")
    aliases_pattern = re.compile(r"Aliases:\s*(.*)")
    name_match = name_pattern.search(issue_body)
    aliases_match = aliases_pattern.search(issue_body)
    name = name_match.group(1).strip() if name_match else ""
    aliases = aliases_match.group(1).strip() if aliases_match else ""
    return name, aliases


def detect_language(label):
    try:
        predictions = detector.predict(label, k=1)
        detected_lg_iso_code = predictions[0][0].split("__label__")[1]
        lg = Lang(detected_lg_iso_code)
        if lg:
            return lg.name
        return None
    except Exception as e:
        return None


def detect_languages(name, aliases):
    name_language = detect_language(name)
    updated_name = f"{name}*{name_language}" if name_language else name

    updated_aliases = []
    for alias in aliases.split(";"):
        alias = alias.strip()
        alias_language = detect_language(alias)
        updated_alias = f"{alias}*{alias_language}" if alias_language else alias
        updated_aliases.append(updated_alias)

    updated_aliases = "; ".join(updated_aliases)

    return updated_name, updated_aliases


def update_issue_body(repo, issue_number, updated_name, updated_aliases):
    issue = repo.get_issue(issue_number)
    updated_body = issue.body.replace(f"Name of organization: {updated_name.split('*')[0]}", f"Name of organization: {updated_name}")
    updated_body = updated_body.replace(f"Aliases: {updated_aliases.split('*')[0]}", f"Aliases: {updated_aliases}")
    issue.edit(body=updated_body)


def main():
    args = parse_arguments()
    github_token = os.environ["GITHUB_TOKEN"]
    github = Github(github_token)
    repo = github.get_repo(args.repo_name)
    issue_body = get_issue_body(repo, args.issue_number)
    name, aliases = extract_name_and_aliases(issue_body)
    updated_name, updated_aliases = detect_languages(name, aliases)
    update_issue_body(repo, args.issue_number, updated_name, updated_aliases)
    print("GitHub issue updated with languages.")


if __name__ == "__main__":
    main()
