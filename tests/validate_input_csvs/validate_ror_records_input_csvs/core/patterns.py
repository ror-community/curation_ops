import re

ACRONYMS_PATTERN = re.compile(r'^[A-Z0-9 ]+$')
NAMES_PATTERN = re.compile(r'.*\*[A-Za-z]{2,}$')
URL_PATTERN = re.compile(r'https?://.*')
WIKIPEDIA_URL_PATTERN = re.compile(r'https?://[a-z]{2,3}.wikipedia.org/.*|delete')
ISNI_PATTERN = re.compile(r'[0]{4} [0-9]{4} [0-9]{4} [0-9]{3}[0-9X](\*preferred)?|delete')
WIKIDATA_PATTERN = re.compile(r'^(?:Q[1-9]\d*(?:\*preferred)?|delete)$')
FUNDREF_PATTERN = re.compile(r'^(?:[1-9]\d*(?:\*preferred)?|delete)$')
GEONAMES_PATTERN = re.compile(r'^(?:[1-9]\d*(?:\*preferred)?|delete)$')

VALID_STATUSES = {"active", "inactive", "withdrawn"}
VALID_TYPES = {
    "education", "healthcare", "company", "funder", "archive",
    "nonprofit", "government", "facility", "other"
}
