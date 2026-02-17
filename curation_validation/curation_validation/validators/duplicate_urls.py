from curation_validation.validators.base import BaseValidator, ValidatorContext
from curation_validation.core.io import read_csv, read_json_dir
from curation_validation.core.normalize import normalize_url


def get_ror_display_name(record: dict) -> str:
    for name in record.get("names", []):
        if "ror_display" in name.get("types", []):
            return name.get("value", "")
    return ""


def get_website_url(record: dict) -> str | None:
    for link in record.get("links", []):
        if link.get("type") == "website":
            return link.get("value")
    return None


def preprocess_data_source(records: list[dict]) -> dict[str, dict]:
    url_dict = {}
    for record in records:
        website_url = get_website_url(record)
        if not website_url:
            continue
        normalized = normalize_url(website_url)
        if not normalized:
            continue
        record_info = {
            "ror_id": record.get("id", ""),
            "ror_display_name": get_ror_display_name(record),
            "original_url": website_url,
        }
        url_dict[normalized] = record_info
        if normalized.startswith("//") and not normalized.startswith("//www."):
            www_version = "//www." + normalized[2:]
            url_dict[www_version] = record_info
    return url_dict


class DuplicateUrlsValidator(BaseValidator):
    name = "duplicate-urls"
    supported_formats = {"csv", "json"}
    output_filename = "duplicate_urls.csv"
    output_fields = [
        "issue_url",
        "ror_display_name",
        "ror_id",
        "data_dump_id",
        "data_dump_ror_display_name",
        "csv_url",
        "data_dump_url",
    ]
    requires_data_source = True

    def run(self, ctx: ValidatorContext) -> list[dict]:
        if ctx.json_dir is not None:
            return self._run_json(ctx)
        elif ctx.csv_file is not None:
            return self._run_csv(ctx)
        return []

    def _run_json(self, ctx: ValidatorContext) -> list[dict]:
        url_dict = preprocess_data_source(ctx.data_source.get_all_records())
        results = []
        records = read_json_dir(ctx.json_dir)
        for record in records:
            record_id = record.get("id", "")
            issue_url = record_id
            display_name = get_ror_display_name(record)
            website_url = get_website_url(record)
            if not website_url:
                continue
            normalized = normalize_url(website_url)
            if not normalized:
                continue
            match = url_dict.get(normalized)
            if match:
                results.append({
                    "issue_url": issue_url,
                    "ror_display_name": display_name,
                    "ror_id": record_id,
                    "data_dump_id": match["ror_id"],
                    "data_dump_ror_display_name": match["ror_display_name"],
                    "csv_url": website_url,
                    "data_dump_url": match["original_url"],
                })
        return results

    def _run_csv(self, ctx: ValidatorContext) -> list[dict]:
        url_dict = preprocess_data_source(ctx.data_source.get_all_records())
        results = []
        rows = read_csv(ctx.csv_file)
        for row in rows:
            record_id = row.get("id", "").strip()
            issue_url = row.get("html_url", "")
            display_name = row.get("names.types.ror_display", "").strip()
            website_url = row.get("links.type.website", "").strip()
            if not website_url:
                continue
            normalized = normalize_url(website_url)
            if not normalized:
                continue
            match = url_dict.get(normalized)
            if match:
                results.append({
                    "issue_url": issue_url,
                    "ror_display_name": display_name,
                    "ror_id": record_id,
                    "data_dump_id": match["ror_id"],
                    "data_dump_ror_display_name": match["ror_display_name"],
                    "csv_url": website_url,
                    "data_dump_url": match["original_url"],
                })
        return results
