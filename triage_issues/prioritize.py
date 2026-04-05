import re
import httpx
from github import GithubException

OPENALEX_BASE_URL = "https://api.openalex.org"
OPENALEX_MAILTO = "support@ror.org"

P1_THRESHOLD = 100
P2_THRESHOLD = 1

AUTO_P1_ORG_TYPES = ["government", "funder"]

PRIORITY_LABELS = {
    "P1": {"color": "b60205", "description": "Extensive affiliation usage"},
    "P2": {"color": "fbca04", "description": "Moderate affiliation usage"},
    "P3": {"color": "c5def5", "description": "No affiliation usage"},
}

TYPE_LABELS = {
    "new": {"color": "0e8a16", "description": "New record request"},
    "update": {"color": "1d76db", "description": "Update to existing record"},
}

RELATIONSHIP_MARKERS = ["Related organizations:", "Related organization:"]
ROR_ID_PATTERN = re.compile(
    r"https://ror\.org/0[a-z0-9]{6}[0-9]{2}|0[a-z0-9]{6}[0-9]{2}"
)


def sanitize_search_name(name):
    name = re.sub(r'\s*\([^)]*\)', '', name)
    name = re.sub(r'[*|"\',:;/\\&!?#@\[\]{}()<>]', ' ', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip()


def get_openalex_params(extra_params, api_key=None):
    params = {"per_page": "1"}
    params.update(extra_params)
    if api_key:
        params["api_key"] = api_key
    else:
        params["mailto"] = OPENALEX_MAILTO
    return params


def get_affiliation_count_by_name(client, name, api_key=None):
    search_name = sanitize_search_name(name)
    if not search_name:
        return 0
    url = f"{OPENALEX_BASE_URL}/works"
    params = get_openalex_params(
        {"filter": f"raw_affiliation_strings.search:{search_name}"}, api_key
    )
    try:
        response = client.get(url, params=params)
        if response.status_code == 200:
            return response.json().get("meta", {}).get("count", 0)
        return 0
    except Exception as e:
        print(f"OpenAlex name query failed for '{name}': {e}")
        return 0


def get_affiliation_count_by_ror(client, ror_id, api_key=None):
    id_part = ror_id.split("/")[-1]
    url = f"{OPENALEX_BASE_URL}/works"
    params = get_openalex_params(
        {"filter": f"institutions.ror:{id_part}"}, api_key
    )
    try:
        response = client.get(url, params=params)
        if response.status_code == 200:
            return response.json().get("meta", {}).get("count", 0)
        return 0
    except Exception as e:
        print(f"OpenAlex ROR query failed for '{ror_id}': {e}")
        return 0


def extract_all_ror_ids(text):
    matches = ROR_ID_PATTERN.findall(text)
    ror_ids = []
    for match in matches:
        ror_id = match if match.startswith("https://") else f"https://ror.org/{match}"
        if ror_id not in ror_ids:
            ror_ids.append(ror_id)
    return ror_ids


def extract_relationship_ror_ids(body):
    for marker in RELATIONSHIP_MARKERS:
        try:
            start = body.index(marker) + len(marker)
            end = body.index('\n', start)
            text = body[start:end].strip()
            if text:
                return extract_all_ror_ids(text)
        except ValueError:
            continue
    if 'Related' in body:
        related_section = body[body.find('Related'):]
        return extract_all_ror_ids(related_section)
    return []


def parse_organization_type(body):
    match = re.search(r'Organization type:\s*(.+?)(?:\n|$)', body)
    return match.group(1).strip() if match else ''


def is_auto_p1_org_type(org_type):
    if not org_type:
        return False
    org_type_lower = org_type.lower()
    return any(org_type_lower.startswith(t) for t in AUTO_P1_ORG_TYPES)


def classify_priority(affiliation_count):
    if affiliation_count >= P1_THRESHOLD:
        return "P1"
    elif affiliation_count >= P2_THRESHOLD:
        return "P2"
    return "P3"


def get_total_affiliation_count(client, issue_type, name, ror_id, relationship_ror_ids, api_key):
    total = 0
    if issue_type == "new" and name:
        total += get_affiliation_count_by_name(client, name, api_key)
    elif issue_type == "new":
        print("Warning: No organization name available for affiliation lookup")
    elif issue_type == "update" and ror_id:
        total += get_affiliation_count_by_ror(client, ror_id, api_key)
    elif issue_type == "update":
        print("Warning: No ROR ID available for affiliation lookup")
    for rel_ror_id in relationship_ror_ids:
        total += get_affiliation_count_by_ror(client, rel_ror_id, api_key)
    return total


def issue_has_priority_label(issue):
    existing = {label.name for label in issue.get_labels()}
    return bool(existing & set(PRIORITY_LABELS.keys()))


def ensure_labels_exist(repo):
    all_labels = {**PRIORITY_LABELS, **TYPE_LABELS}
    for label_name, props in all_labels.items():
        try:
            repo.create_label(
                label_name, props["color"], props["description"]
            )
            print(f"Created label '{label_name}'")
        except GithubException as e:
            if e.status == 422:
                pass
            else:
                print(f"Warning: Could not create label '{label_name}': {e}")


def apply_priority_and_type_labels(issue, priority, issue_type):
    labels_to_add = [priority]
    if issue_type in TYPE_LABELS:
        labels_to_add.append(issue_type)
    try:
        issue.add_to_labels(*labels_to_add)
        print(f"Applied labels {labels_to_add} to issue #{issue.number}")
    except GithubException as e:
        print(f"Failed to apply labels to issue #{issue.number}: {e}")


def prioritize_issue(issue, issue_type, name, ror_id, issue_body, api_key):
    if issue_has_priority_label(issue):
        print(f"Issue #{issue.number} already has a priority label, skipping")
        return None

    org_type = parse_organization_type(issue_body)
    if is_auto_p1_org_type(org_type):
        print(f"Issue #{issue.number}: org type '{org_type}' is auto-P1")
        apply_priority_and_type_labels(issue, "P1", issue_type)
        return "P1"

    relationship_ror_ids = extract_relationship_ror_ids(issue_body)

    with httpx.Client(timeout=30.0) as client:
        total_count = get_total_affiliation_count(
            client, issue_type, name, ror_id, relationship_ror_ids, api_key
        )

    priority = classify_priority(total_count)
    if issue_type == "update" and priority == "P3":
        priority = "P2"

    print(f"Issue #{issue.number}: affiliation count={total_count}, priority={priority}")
    apply_priority_and_type_labels(issue, priority, issue_type)
    return priority
