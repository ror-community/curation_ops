import os
import requests

GITHUB_CONFIG = {
    'TOKEN': os.environ.get('GITHUB_TOKEN_PERSONAL'),
    'GRAPHQL_URL': 'https://api.github.com/graphql'
}


def run_graphql_query(query, variables=None):
    headers = {
        'Authorization': f'Bearer {GITHUB_CONFIG["TOKEN"]}',
        'Content-Type': 'application/json',
    }
    response = requests.post(GITHUB_CONFIG['GRAPHQL_URL'],
                             json={'query': query, 'variables': variables},
                             headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Query failed with status code: {response.status_code}")
        print(f"Response content: {response.text}")
        raise Exception(f"Query failed with status code: {response.status_code}")


def get_project_info(repo, project_number):
    query = """
    query($owner: String!, $name: String!, $number: Int!) {
      repository(owner: $owner, name: $name) {
        projectV2(number: $number) {
          id
          title
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
    variables = {"owner": owner, "name": name, "number": project_number}
    result = run_graphql_query(query, variables)
    project = result['data']['repository']['projectV2']
    if not project:
        raise Exception(f"Project with number '{project_number}' not found in repository '{repo}'")
    status_field = next(
        (field for field in project['fields']['nodes']
         if field and field.get('name') == 'Status'),
        None
    )
    if not status_field:
        raise Exception("Status field not found in the project")
    columns = {option['name']: option['id']
               for option in status_field['options']}
    return project['id'], columns


def get_column_issue_numbers(repo, project_number, column_name):
    project_id, columns = get_project_info(repo, project_number)
    if column_name not in columns:
        raise Exception(f"Column '{column_name}' not found in project with number '{project_number}' in repository '{repo}'")
    column_id = columns[column_name]
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
                }
              }
            }
          }
        }
      }
    }
    """
    issue_numbers = []
    has_next_page = True
    after_cursor = None
    while has_next_page:
        variables = {
            "project_id": project_id,
            "after": after_cursor
        }
        result = run_graphql_query(query, variables)
        items = result['data']['node']['items']['nodes']
        for item in items:
            is_in_column = False
            for field_value in item['fieldValues']['nodes']:
                if field_value.get('field', {}).get('name') == 'Status' and field_value.get('name') == column_name:
                    is_in_column = True
                    break
            if is_in_column and item['content'] and 'number' in item['content']:
                issue_numbers.append(item['content']['number'])
        page_info = result['data']['node']['items']['pageInfo']
        has_next_page = page_info['hasNextPage']
        after_cursor = page_info['endCursor']
    return issue_numbers
