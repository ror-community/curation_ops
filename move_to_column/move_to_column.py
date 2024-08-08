import os
import re
import csv
import sys
import requests
import argparse

GITHUB = {}
GITHUB['TOKEN'] = os.environ.get('GITHUB_TOKEN')
GITHUB_GRAPHQL_URL = 'https://api.github.com/graphql'


def run_graphql_query(query, variables=None):
    headers = {
        'Authorization': f'Bearer {GITHUB["TOKEN"]}',
        'Content-Type': 'application/json',
    }
    response = requests.post(GITHUB_GRAPHQL_URL, json={
                             'query': query, 'variables': variables}, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Query failed with status code: {response.status_code}")
        print(f"Response content: {response.text}")
        raise Exception(f"Query failed with status code: {response.status_code}")


def get_project_info():
    query = """
    query {
      organization(login: "ror-community") {
        projectsV2(first: 20) {
          nodes {
            id
            title
            number
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
    }
    """
    result = run_graphql_query(query)
    projects = result['data']['organization']['projectsV2']['nodes']
    project = next(
        (p for p in projects if p['title'] == 'ROR Updates'), None)
    if not project:
        raise Exception("'ROR Updates' project not found")

    status_field = next(
        (field for field in project['fields']['nodes']
         if field and field.get('name') == 'Status'),
        None
    )
    if not status_field:
        raise Exception("Status field not found in the project")
    return project['id'], status_field['id'], status_field['options']


def get_items_to_move(project_id, status_field_id, target_option_id, issue_numbers):
    def get_items_page(project_id, after_cursor=None):
        query = """
        query($project_id: ID!, $after: String) {
          node(id: $project_id) {
            ... on ProjectV2 {
              items(first: 100, after: $after) {
                pageInfo {
                  hasNextPage
                  endCursor
                }
                nodes {
                  id
                  fieldValues(first: 100) {
                    nodes {
                      ... on ProjectV2ItemFieldSingleSelectValue {
                        field {
                          ... on ProjectV2SingleSelectField {
                            id
                            name
                          }
                        }
                        optionId
                      }
                    }
                  }
                  content {
                    ... on Issue {
                      number
                    }
                  }
                }
              }
            }
          }
        }
        """
        variables = {
            "project_id": project_id,
        }
        if after_cursor:
            variables["after"] = after_cursor
        return run_graphql_query(query, variables)
    all_items = []
    has_next_page = True
    after_cursor = None
    while has_next_page:
        result = get_items_page(project_id, after_cursor)
        if 'data' not in result or 'node' not in result['data'] or 'items' not in result['data']['node']:
            print("Unexpected API response:")
            print(result)
            raise Exception("API response structure is not as expected")
        
        page_info = result['data']['node']['items']['pageInfo']
        has_next_page = page_info['hasNextPage']
        after_cursor = page_info['endCursor']
        
        all_items.extend(result['data']['node']['items']['nodes'])
    return [
        item for item in all_items
        if item['content'] and item['content']['number'] in issue_numbers
        and not any(
            field_value['field']['id'] == status_field_id
            and field_value['optionId'] == target_option_id
            for field_value in item['fieldValues']['nodes']
            if isinstance(field_value, dict) and 'field' in field_value
        )
    ]


def move_to_project_column(project_id, item_id, field_id, option_id):
    mutation = """
    mutation($project_id: ID!, $item_id: ID!, $field_id: ID!, $option_id: String!) {
      updateProjectV2ItemFieldValue(input: {
        projectId: $project_id
        itemId: $item_id
        fieldId: $field_id
        value: { 
          singleSelectOptionId: $option_id
        }
      }) {
        projectV2Item {
          id
        }
      }
    }
    """
    variables = {
        "project_id": project_id,
        "item_id": item_id,
        "field_id": field_id,
        "option_id": option_id
    }
    run_graphql_query(mutation, variables)


def extract_issue_numbers(csv_file):
    issue_numbers = []
    with open(csv_file, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            html_url = row['html_url']
            match = re.search(r'/issues/(\d+)$', html_url)
            if match:
                issue_numbers.append(int(match.group(1)))
    return issue_numbers


def move_to_column(csv_file, target_column):
    project_id, status_field_id, status_options = get_project_info()
    target_option = next(
        (option for option in status_options if option['name'] == target_column), None)
    if not target_option:
        raise Exception(f"Target column '{target_column}' not found in project")
    issue_numbers = extract_issue_numbers(csv_file)
    items_to_move = get_items_to_move(
        project_id, status_field_id, target_option['id'], issue_numbers)
    for item in items_to_move:
        move_to_project_column(
            project_id, item['id'], status_field_id, target_option['id'])
        print(f"Moved issue {item['content']['number']} to '{target_column}'")


def main():
    parser = argparse.ArgumentParser(
        description='Move GitHub issues to a specified project column')
    parser.add_argument(
        '-i', '--input_file', required=True, help='Path to the CSV new or update records CSV file')
    parser.add_argument(
        '-c', '--target_column', required=True, help='Name of the target column where issues should be moved')
    args = parser.parse_args()
    move_to_column(args.input_file, args.target_column)


if __name__ == '__main__':
    main()
