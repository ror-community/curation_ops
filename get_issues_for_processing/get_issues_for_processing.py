import os
import sys
import asyncio
import argparse
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

DEFAULT_MIN_ISSUE_NUMBER = 30114


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


async def get_issues_needing_processing(
    repo: str,
    required_label: str,
    exclusion_label: str,
    min_issue_number: int = DEFAULT_MIN_ISSUE_NUMBER
) -> list[int]:
    """
    Fetch issue numbers that:
    - Are open
    - Have the required_label
    - Do NOT have the exclusion_label
    - Have issue number >= min_issue_number
    """
    search_query = """
    query($searchQuery: String!, $after: String) {
      search(query: $searchQuery, type: ISSUE, first: 100, after: $after) {
        pageInfo { hasNextPage endCursor }
        nodes {
          ... on Issue {
            number
            labels(first: 20) { nodes { name } }
          }
        }
      }
    }
    """

    owner, name = repo.split('/')
    search_str = f'repo:{owner}/{name} is:issue is:open label:"{required_label}"'

    issue_numbers = []
    has_next_page = True
    after_cursor = None
    pages = 0

    async with aiohttp.ClientSession() as session:
        while has_next_page:
            pages += 1
            variables = {
                "searchQuery": search_str,
                "after": after_cursor
            }

            result = await run_graphql_query_async(session, search_query, variables)
            search_result = result['data']['search']

            for node in search_result['nodes']:
                if not node:
                    continue

                issue_num = node['number']

                # Skip issues below minimum
                if issue_num < min_issue_number:
                    continue

                # Check for exclusion label
                labels = [
                    label['name']
                    for label in node.get('labels', {}).get('nodes', [])
                ]

                if exclusion_label not in labels:
                    issue_numbers.append(issue_num)

            page_info = search_result['pageInfo']
            has_next_page = page_info['hasNextPage']
            after_cursor = page_info['endCursor']

    # Sort by issue number for consistent processing order
    issue_numbers.sort()

    logger.info(
        f"Found {len(issue_numbers)} issues with label '{required_label}' "
        f"without label '{exclusion_label}' (>= #{min_issue_number}) "
        f"(searched {pages} pages)"
    )

    return issue_numbers


def main():
    parser = argparse.ArgumentParser(
        description='Get GitHub issue numbers needing processing based on labels'
    )
    parser.add_argument(
        '--repo',
        required=True,
        help='Repository in owner/name format (e.g., ror-community/ror-updates)'
    )
    parser.add_argument(
        '--required-label',
        required=True,
        help='Label that issues must have (e.g., triage-needed)'
    )
    parser.add_argument(
        '--exclude-label',
        required=True,
        help='Label that issues must NOT have (e.g., auto-formatted)'
    )
    parser.add_argument(
        '--min-issue',
        type=int,
        default=DEFAULT_MIN_ISSUE_NUMBER,
        help=f'Minimum issue number to process (default: {DEFAULT_MIN_ISSUE_NUMBER})'
    )

    args = parser.parse_args()

    if not GITHUB_CONFIG['TOKEN']:
        logger.error("GITHUB_TOKEN environment variable is not set")
        sys.exit(1)

    try:
        issue_numbers = asyncio.run(
            get_issues_needing_processing(
                repo=args.repo,
                required_label=args.required_label,
                exclusion_label=args.exclude_label,
                min_issue_number=args.min_issue
            )
        )
    except Exception as e:
        logger.error(f"Failed to fetch issues: {e}")
        sys.exit(1)

    # Output space-separated issue numbers for shell consumption
    print(' '.join(str(n) for n in issue_numbers))


if __name__ == '__main__':
    main()
