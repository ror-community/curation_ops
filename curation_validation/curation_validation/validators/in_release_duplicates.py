from thefuzz import fuzz

from curation_validation.validators.base import BaseValidator, ValidatorContext
from curation_validation.core.io import read_csv, read_json_dir
from curation_validation.core.normalize import normalize_url, normalize_text

FUZZY_THRESHOLD = 85


def clean_name(name: str) -> str:
    return name.split("*")[0].strip()


def parse_csv_record(row: dict, index: int) -> dict:
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
    url = row.get("links.type.website", "")
    urls = [url] if url else []
    issue_url = row.get("html_url", "")
    return {
        "index": index,
        "display_name": display_name,
        "names": names,
        "url": url,
        "urls": urls,
        "issue_url": issue_url,
    }


def parse_json_record(record: dict, index: int) -> dict:
    names = []
    display_name = ""
    for name_entry in record.get("names", []):
        types = name_entry.get("types", [])
        value = name_entry.get("value", "")
        if not value:
            continue
        if "ror_display" in types:
            if not display_name:
                display_name = value
            names.append(value)
        elif "alias" in types:
            names.append(value)
        elif "label" in types:
            names.append(value)
    url = ""
    urls = []
    for link in record.get("links", []):
        if link.get("type") == "website":
            url = link.get("value", "")
            if url:
                urls.append(url)
            break
    issue_url = record.get("id", "")
    return {
        "index": index,
        "display_name": display_name,
        "names": names,
        "url": url,
        "urls": urls,
        "issue_url": issue_url,
    }


def check_url_matches(
    urls1: list[str], urls2: list[str]
) -> tuple[bool, str | None, str | None]:
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


def check_name_matches(
    names1: list[str], names2: list[str]
) -> list[tuple[str, str, int]]:
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


def find_duplicates(parsed_records: list[dict]) -> list[dict]:
    findings = []
    seen_pairs = set()
    seen_name_pairs = set()

    for i, record1 in enumerate(parsed_records):
        for j, record2 in enumerate(parsed_records):
            if i >= j:
                continue
            pair_key = (i, j)
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            url_matched, url1, url2 = check_url_matches(
                record1["urls"], record2["urls"]
            )
            if url_matched:
                findings.append({
                    "record1_issue_url": record1.get("issue_url", ""),
                    "record2_issue_url": record2.get("issue_url", ""),
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
                    "record1_issue_url": record1.get("issue_url", ""),
                    "record2_issue_url": record2.get("issue_url", ""),
                    "record1_display_name": record1["display_name"],
                    "record1_url": record1["url"],
                    "record2_display_name": record2["display_name"],
                    "record2_url": record2["url"],
                    "match_type": match_type,
                    "similarity_score": similarity,
                })

    return findings


class InReleaseDuplicatesValidator(BaseValidator):
    name = "in-release-duplicates"
    supported_formats = {"csv", "json"}
    output_filename = "in_release_duplicates.csv"
    output_fields = [
        "record1_issue_url",
        "record2_issue_url",
        "record1_display_name",
        "record1_url",
        "record2_display_name",
        "record2_url",
        "match_type",
        "similarity_score",
    ]
    requires_data_source = False

    def run(self, ctx: ValidatorContext) -> list[dict]:
        if ctx.json_dir is not None:
            return self._run_json(ctx)
        elif ctx.csv_file is not None:
            return self._run_csv(ctx)
        return []

    def _run_json(self, ctx: ValidatorContext) -> list[dict]:
        records = read_json_dir(ctx.json_dir)
        parsed = [parse_json_record(rec, i) for i, rec in enumerate(records)]
        return find_duplicates(parsed)

    def _run_csv(self, ctx: ValidatorContext) -> list[dict]:
        rows = read_csv(ctx.csv_file)
        parsed = [parse_csv_record(row, i) for i, row in enumerate(rows)]
        return find_duplicates(parsed)
