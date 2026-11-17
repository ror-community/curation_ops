from collections import defaultdict
from collections.abc import Callable
from functools import cache
from itertools import combinations
from typing import Optional

from thefuzz import fuzz

from curation_validation.validators.base import BaseValidator, ValidatorContext
from curation_validation.core.fuzzy import ratio_self_matches
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
    return _first_url_match(urls1, urls2, normalize_url)


def _first_url_match(
    urls1: list[str],
    urls2: list[str],
    normalize: Callable[[str], Optional[str]],
) -> tuple[bool, str | None, str | None]:
    for url1 in urls1:
        if not url1:
            continue
        normalized1 = normalize(url1)
        if not normalized1:
            continue
        for url2 in urls2:
            if not url2:
                continue
            normalized2 = normalize(url2)
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


def _url_match_pairs(
    parsed_records: list[dict],
) -> dict[tuple[int, int], tuple[str, str]]:
    normalize = cache(normalize_url)
    positions_by_url: dict[str, list[int]] = defaultdict(list)
    for position, record in enumerate(parsed_records):
        for normalized in {normalize(url) for url in record["urls"] if url}:
            if normalized:
                positions_by_url[normalized].append(position)

    pairs = {}
    for positions in positions_by_url.values():
        for i, j in combinations(positions, 2):
            if (i, j) not in pairs:
                _, url1, url2 = _first_url_match(
                    parsed_records[i]["urls"], parsed_records[j]["urls"], normalize
                )
                pairs[(i, j)] = (url1, url2)
    return pairs


def _name_match_pairs(
    parsed_records: list[dict],
) -> dict[tuple[int, int], list[tuple[int, int, int]]]:
    """Map each record pair (i, j), i < j, to its (name_index_i, name_index_j, score) matches."""
    owners: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for position, record in enumerate(parsed_records):
        for name_index, name in enumerate(record["names"]):
            cleaned = clean_name(name)
            if cleaned:
                owners[normalize_text(cleaned)].append((position, name_index))

    pairs: dict[tuple[int, int], list[tuple[int, int, int]]] = defaultdict(list)

    def add(entry1: tuple[int, int], entry2: tuple[int, int], score: int) -> None:
        if entry1[0] == entry2[0]:
            return
        (i, a), (j, b) = sorted((entry1, entry2))
        pairs[(i, j)].append((a, b, score))

    # Identical normalized names always score 100, including two empty ones.
    for entries in owners.values():
        for entry1, entry2 in combinations(entries, 2):
            add(entry1, entry2, 100)

    distinct = [name for name in owners if name]
    for u, v, score in ratio_self_matches(distinct, FUZZY_THRESHOLD):
        for entry1 in owners[distinct[u]]:
            for entry2 in owners[distinct[v]]:
                add(entry1, entry2, score)

    return pairs


def find_duplicates(parsed_records: list[dict]) -> list[dict]:
    """Report every record pair (i < j) sharing a website or a name scoring >= FUZZY_THRESHOLD.

    Equivalent to comparing all pairs in order (URL match first, then names in list
    order), with a raw name pair reported only the first time it is seen, but it only
    visits pairs that actually match.
    """
    url_pairs = _url_match_pairs(parsed_records)
    name_pairs = _name_match_pairs(parsed_records)

    findings = []
    seen_name_pairs = set()

    for i, j in sorted(url_pairs.keys() | name_pairs.keys()):
        record1 = parsed_records[i]
        record2 = parsed_records[j]

        if (i, j) in url_pairs:
            url1, url2 = url_pairs[(i, j)]
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

        for a, b, similarity in sorted(name_pairs.get((i, j), ())):
            name1 = record1["names"][a]
            name2 = record2["names"][b]
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
