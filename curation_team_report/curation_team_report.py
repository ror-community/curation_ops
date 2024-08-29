import os
import sys
import csv
import argparse
import requests


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Generate a curation team report using GitHub GraphQL API")
    parser.add_argument('-t', '--token', default=os.environ.get('GITHUB_TOKEN_PERSONAL'),
                        help='GitHub Personal Access Token')
    parser.add_argument('-o', '--output_dir', default=os.getcwd(),
                        help='Output directory for CSV files')
    parser.add_argument('-r', '--repo', default='ror-community/ror-updates',
                        help='Repository name in the format owner/repo')
    parser.add_argument('-p', '--project_number', type=int,
                        default=19, help='Project number (default: 19)')
    return parser.parse_args()


def run_graphql_query(query, variables, token):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    response = requests.post('https://api.github.com/graphql',
                             json={'query': query, 'variables': variables}, headers=headers)
    response.raise_for_status()
    return response.json()


def get_project_columns(repo, project_number, token):
    query = """
    query($owner: String!, $name: String!, $number: Int!) {
      repository(owner: $owner, name: $name) {
        projectV2(number: $number) {
          fields(first: 20) {
            nodes {
              ... on ProjectV2SingleSelectField {
                id
                name
                options {
                  id
                  name
                }
              }
            }
          }
        }
      }
    }
    """
    owner, name = repo.split('/')
    variables = {'owner': owner, 'name': name, 'number': project_number}
    result = run_graphql_query(query, variables, token)

    status_field = next(
        (field for field in result['data']['repository']['projectV2']['fields']['nodes']
         if field and field.get('name') == 'Status'),
        None
    )

    if not status_field:
        raise Exception("Status field not found in the project")

    return {option['name']: option['id'] for option in status_field['options']}


def get_column_issues(repo, project_number, column_id, token):
    query = """
    query($owner: String!, $name: String!, $number: Int!, $after: String) {
      repository(owner: $owner, name: $name) {
        projectV2(number: $number) {
          items(first: 100, after: $after) {
            pageInfo {
              hasNextPage
              endCursor
            }
            nodes {
              fieldValues(first: 10) {
                nodes {
                  ... on ProjectV2ItemFieldSingleSelectValue {
                    name
                    field {
                      ... on ProjectV2SingleSelectField {
                        name
                      }
                    }
                  }
                }
              }
              content {
                ... on Issue {
                  number
                  url
                  title
                  labels(first: 10) {
                    nodes {
                      name
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    owner, name = repo.split('/')
    variables = {'owner': owner, 'name': name, 'number': project_number}
    issues = []
    has_next_page = True
    after_cursor = None
    while has_next_page:
        variables['after'] = after_cursor
        result = run_graphql_query(query, variables, token)
        items = result['data']['repository']['projectV2']['items']['nodes']
        for item in items:
            is_in_column = any(
                field_value.get('field', {}).get('name') == 'Status' and
                field_value.get('name') == column_id
                for field_value in item['fieldValues']['nodes']
            )
            if is_in_column and item['content']:
                issue = item['content']
                issues.append({
                    'number': issue['number'],
                    'url': issue['url'],
                    'title': issue['title'],
                    'labels': '; '.join([label['name'] for label in issue['labels']['nodes']])
                })
        page_info = result['data']['repository']['projectV2']['items']['pageInfo']
        has_next_page = page_info['hasNextPage']
        after_cursor = page_info['endCursor']

    return issues


def write_issues_to_csv(issues, column_name, output_dir):
    output_file = os.path.join(output_dir, f"{column_name}.csv")
    header = ['column_name', 'issue_number', 'html_url', 'labels', 'title']
    with open(output_file, 'w', newline='') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(header)
        for issue in issues:
            writer.writerow([
                column_name,
                issue['number'],
                issue['url'],
                issue['labels'],
                issue['title']
            ])


def main():
    args = parse_arguments()
    columns = get_project_columns(args.repo, args.project_number, args.token)
    curator_column_names = ['Second review', 'Needs discussion']
    for column_name in curator_column_names:
        if column_name not in columns:
            print(f"Warning: Column '{column_name}' not found in the project.")
            continue
        column_id = columns[column_name]
        issues = get_column_issues(
            args.repo, args.project_number, column_name, args.token)
        write_issues_to_csv(issues, column_name, args.output_dir)
        print(f"Generated report for column: {column_name}")


if __name__ == '__main__':
    main()
