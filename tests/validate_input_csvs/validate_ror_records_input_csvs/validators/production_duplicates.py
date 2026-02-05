"""Validator to check for duplicate records against ROR production API."""

from typing import Optional


def get_country_code_from_result(result: dict) -> Optional[str]:
    """Extract country code from ROR API result."""
    locations = result.get("locations", [])
    if not locations:
        return None

    geonames_details = locations[0].get("geonames_details", {})
    return geonames_details.get("country_code")


def get_all_names_from_result(result: dict) -> list[str]:
    """Extract all names (ror_display, alias, label) from ROR API result."""
    names = []
    name_types = ["ror_display", "alias", "label"]

    for name_entry in result.get("names", []):
        entry_types = name_entry.get("types", [])
        if any(t in entry_types for t in name_types):
            value = name_entry.get("value", "")
            if value:
                names.append(value)

    return names


def parse_csv_names(row: dict) -> list[str]:
    """Extract names from CSV row (display, aliases, labels)."""
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
