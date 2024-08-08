import re

ACRONYMS_PATTERN = re.compile(r'^[A-Z0-9 ]+$')
LABELS_PATTERN = re.compile(r'.*\*[A-Za-z]{2,}$')
URL_PATTERN = re.compile(r'https?://.*')
WIKIPEDIA_URL_PATTERN = re.compile(r'https?://[a-z]{2,3}.wikipedia.org/.*')
ISNI_PATTERN = re.compile(r'[0]{4} [0-9]{4} [0-9]{4} [0-9]{3}[0-9X](\*preferred)?')
WIKIDATA_PATTERN = re.compile(r'Q[1-9]\d*(\*preferred)?')
FUNDREF_PATTERN = re.compile(r'[1-9]\d+(\*preferred)?')
GEONAMES_PATTERN = re.compile(r'[1-9]\d+')