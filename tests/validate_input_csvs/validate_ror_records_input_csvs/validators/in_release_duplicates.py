"""Validator to detect duplicate records within a CSV file."""

from thefuzz import fuzz

from validate_ror_records_input_csvs.core.io import read_csv
from validate_ror_records_input_csvs.core.normalize import normalize_url, normalize_text
from validate_ror_records_input_csvs.validators.base import BaseValidator, ValidatorContext


FUZZY_THRESHOLD = 85


def parse_csv_names(row: dict) -> list[str]:
    """Collects display name, aliases, and labels."""
    names = []
    display_name = row.get("names.types.ror_display", "")
    if display_name:
        names.append(display_name)

    aliases = row.get("names.types.alias", "")
    if aliases:
        for alias in aliases.split("; "):
            alias = alias.strip()
            if alias:
                names.append(alias)

    labels = row.get("names.types.label", "")
    if labels:
        for label in labels.split("; "):
            label = label.strip()
            if label:
                names.append(label)

    return names


def clean_name(name: str) -> str:
    """Removes language marker (e.g., 'Name*en' -> 'Name')."""
    return name.split("*")[0].strip()


def check_url_matches(urls1: list[str], urls2: list[str]) -> tuple[bool, str | None, str | None]:
    """Returns (matched, url1, url2) - matched is True if any pair matches."""
    for url1 in urls1:
        if not url1:
            continue
        normalized1 = normalize_url(url1)
        if not normalized1:
            continue

        for url2 in urls2:
            if not url2:
                continue
            normalized2 = normalize_url(url2)
            if not normalized2:
                continue

            if normalized1 == normalized2:
                return True, url1, url2

    return False, None, None


def check_name_matches(names1: list[str], names2: list[str]) -> list[tuple[str, str, int]]:
    """Returns list of (name1, name2, similarity_score) for matches >= threshold."""
    matches = []

    for name1 in names1:
        cleaned1 = clean_name(name1)
        if not cleaned1:
            continue

        for name2 in names2:
            cleaned2 = clean_name(name2)
            if not cleaned2:
                continue

            normalized1 = normalize_text(cleaned1)
            normalized2 = normalize_text(cleaned2)

            similarity = fuzz.ratio(normalized1, normalized2)

            if similarity >= FUZZY_THRESHOLD:
                matches.append((name1, name2, similarity))

    return matches


def find_duplicates(records: list[dict]) -> list[dict]:
    findings = []
    seen_pairs = set()
    seen_name_pairs = set()

    parsed_records = []
    for i, row in enumerate(records):
        parsed_records.append({
            "index": i,
            "display_name": row.get("names.types.ror_display", ""),
            "names": parse_csv_names(row),
            "url": row.get("links.type.website", ""),
            "urls": [row.get("links.type.website", "")] if row.get("links.type.website") else [],
        })

    for i, record1 in enumerate(parsed_records):
        for j, record2 in enumerate(parsed_records):
            if i >= j:
                continue

            pair_key = (i, j)
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            url_matched, url1, url2 = check_url_matches(record1["urls"], record2["urls"])
            if url_matched:
                findings.append({
                    "record1_display_name": record1["display_name"],
                    "record1_url": url1 or "",
                    "record2_display_name": record2["display_name"],
                    "record2_url": url2 or "",
                    "match_type": "url",
                    "similarity_score": 100,
                })

            name_matches = check_name_matches(record1["names"], record2["names"])
            for name1, name2, similarity in name_matches:
                name_pair_key = tuple(sorted([name1, name2]))
                if name_pair_key in seen_name_pairs:
                    continue
                seen_name_pairs.add(name_pair_key)

                match_type = "name_exact" if similarity == 100 else "name_fuzzy"
                findings.append({
                    "record1_display_name": record1["display_name"],
                    "record1_url": record1["url"],
                    "record2_display_name": record2["display_name"],
                    "record2_url": record2["url"],
                    "match_type": match_type,
                    "similarity_score": similarity,
                })

    return findings


class InReleaseDuplicatesValidator(BaseValidator):
    """
    Validator to detect potential duplicates within a CSV file.

    This validator checks for duplicates WITHIN the CSV file (not against
    a data source). It helps catch cases where the same organization might
    be submitted twice under different names or slightly different URLs.

    Matching rules:
    - URL match: Normalized URLs are compared (strips scheme, www, path, query)
    - Name match: Uses fuzzy matching with 85% threshold
    - Names are normalized (lowercase, remove punctuation) before comparison
    - Language markers (*en, *de, etc.) are stripped from names
    """

    name = "in-release-duplicates"
    output_filename = "in_release_duplicates.csv"
    output_fields = [
        "record1_display_name",
        "record1_url",
        "record2_display_name",
        "record2_url",
        "match_type",
        "similarity_score",
    ]
    requires_data_source = False
    requires_geonames = False

    def run(self, ctx: ValidatorContext) -> list[dict]:
        records = read_csv(ctx.input_file)
        findings = find_duplicates(records)

        return findings
