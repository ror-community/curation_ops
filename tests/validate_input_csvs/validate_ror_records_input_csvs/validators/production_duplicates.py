"""Validator to check for duplicate records against ROR production API."""

from typing import Optional

from validate_ror_records_input_csvs.validators.base import BaseValidator, ValidatorContext


class ProductionDuplicatesValidator(BaseValidator):
    """
    Validator to check for potential duplicates against ROR production API.

    Searches the live ROR API using organization names from the input CSV,
    then applies fuzzy matching (85% threshold) to find potential duplicates.
    Results are filtered to only include matches with the same country code.
    """

    name = "production-duplicates"
    output_filename = "production_duplicates.csv"
    output_fields = [
        "name",
        "display_name",
        "matched_ror_id",
        "matched_name",
        "match_ratio",
    ]
    requires_data_source = False
    requires_geonames = True
    new_records_only = True

    def run(self, ctx: ValidatorContext) -> list[dict]:
        # Placeholder - implemented in next task
        return []


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
