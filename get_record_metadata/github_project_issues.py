import os
import asyncio
import logging
from typing import Optional

import aiohttp

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

GITHUB_CONFIG = {
    'TOKEN': os.environ.get('GITHUB_TOKEN'),
    'GRAPHQL_URL': 'https://api.github.com/graphql'
}

RETRY_CONFIG = {
    'max_retries': 3,
    'base_delay': 1.0,
    'max_delay': 30.0,
    'retryable_status_codes': [429, 500, 502, 503, 504]
}


async def run_graphql_query_async(
    session: aiohttp.ClientSession,
    query: str,
    variables: Optional[dict] = None
) -> dict:
    """Execute a GraphQL query with retry logic for transient failures."""
    headers = {
        'Authorization': f'Bearer {GITHUB_CONFIG["TOKEN"]}',
        'Content-Type': 'application/json',
    }
    payload = {'query': query, 'variables': variables}

    last_exception = None
    for attempt in range(RETRY_CONFIG['max_retries']):
        try:
            async with session.post(
                GITHUB_CONFIG['GRAPHQL_URL'],
                json=payload,
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if 'errors' in result:
                        error_msg = result['errors'][0].get('message', 'Unknown GraphQL error')
                        raise Exception(f"GraphQL error: {error_msg}")
                    return result

                if response.status in RETRY_CONFIG['retryable_status_codes']:
                    delay = min(
                        RETRY_CONFIG['base_delay'] * (2 ** attempt),
                        RETRY_CONFIG['max_delay']
                    )
                    if response.status == 429:
                        retry_after = response.headers.get('Retry-After')
                        if retry_after:
                            delay = float(retry_after)
                    logger.warning(
                        f"Request failed with {response.status}, "
                        f"retrying in {delay}s (attempt {attempt + 1}/{RETRY_CONFIG['max_retries']})"
                    )
                    await asyncio.sleep(delay)
                    continue

                text = await response.text()
                raise Exception(f"Query failed with status {response.status}: {text}")

        except aiohttp.ClientError as e:
            last_exception = e
            delay = min(
                RETRY_CONFIG['base_delay'] * (2 ** attempt),
                RETRY_CONFIG['max_delay']
            )
            logger.warning(
                f"Network error: {e}, retrying in {delay}s "
                f"(attempt {attempt + 1}/{RETRY_CONFIG['max_retries']})"
            )
            await asyncio.sleep(delay)

    raise last_exception or Exception("Max retries exceeded")


async def get_column_issues(
    repo: str,
    project_number: int,
    column_name: str,
    label_filter: Optional[str] = None
) -> list[dict]:
    """Fetch all issues from a project column with their full content."""
    project_items_query = """
    query($org: String!, $projectNumber: Int!, $after: String) {
      organization(login: $org) {
        projectV2(number: $projectNumber) {
          items(first: 100, after: $after) {
            pageInfo { hasNextPage endCursor }
            nodes {
              fieldValues(first: 10) {
                nodes {
                  ... on ProjectV2ItemFieldSingleSelectValue {
                    name
                    field { ... on ProjectV2SingleSelectField { name } }
                  }
                }
              }
              content {
                ... on Issue {
                  id
                  number
                  body
                  url
                  labels(first: 20) { nodes { name } }
                }
              }
            }
          }
        }
      }
    }
    """

    owner = repo.split('/')[0]

    issues = []
    has_next_page = True
    after_cursor = None
    pages = 0

    async with aiohttp.ClientSession() as session:
        while has_next_page:
            pages += 1
            variables = {
                "org": owner,
                "projectNumber": project_number,
                "after": after_cursor
            }

            result = await run_graphql_query_async(session, project_items_query, variables)
            items_data = result['data']['organization']['projectV2']['items']

            for item in items_data['nodes']:
                content = item.get('content')
                if not content or 'number' not in content:
                    continue

                for field_value in item.get('fieldValues', {}).get('nodes', []):
                    if (field_value.get('field', {}).get('name') == 'Status' and
                            field_value.get('name') == column_name):
                        labels = [
                            label['name']
                            for label in content.get('labels', {}).get('nodes', [])
                        ]
                        if label_filter and label_filter not in labels:
                            break
                        issues.append({
                            'number': content['number'],
                            'body': content.get('body', ''),
                            'url': content.get('url', ''),
                            'labels': labels
                        })
                        break

            page_info = items_data['pageInfo']
            has_next_page = page_info['hasNextPage']
            after_cursor = page_info['endCursor']

    logger.info(f"Found {len(issues)} issues in column '{column_name}'"
                + (f" with label '{label_filter}'" if label_filter else "")
                + f" (searched {pages} pages)")

    return issues
