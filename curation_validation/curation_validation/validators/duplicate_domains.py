from curation_validation.validators.base import BaseValidator, ValidatorContext
from curation_validation.core.io import read_csv, read_json_dir


def normalize_domain(domain: str) -> str | None:
    if not domain or not domain.strip():
        return None
    domain = domain.strip().lower()
    if domain.endswith("."):
        domain = domain[:-1]
    if domain.startswith("www."):
        domain = domain[4:]
    return domain if domain else None


def get_ror_display_name(record: dict) -> str:
    for name in record.get("names", []):
        if "ror_display" in name.get("types", []):
            return name.get("value", "")
    return ""


def get_domains(record: dict) -> list[str]:
    return record.get("domains", [])


def preprocess_data_source(records: list[dict]) -> dict[str, dict]:
    domain_dict = {}
    for record in records:
        domains = get_domains(record)
        for domain in domains:
            normalized = normalize_domain(domain)
            if not normalized:
                continue
            record_info = {
                "ror_id": record.get("id", ""),
                "ror_display_name": get_ror_display_name(record),
                "original_domain": domain,
            }
            domain_dict[normalized] = record_info
            if not normalized.startswith("www."):
                www_version = "www." + normalized
                domain_dict[www_version] = record_info
    return domain_dict


class DuplicateDomainsValidator(BaseValidator):
    name = "duplicate-domains"
    supported_formats = {"csv", "json"}
    output_filename = "duplicate_domains.csv"
    output_fields = [
        "issue_url",
        "ror_display_name",
        "ror_id",
        "data_dump_id",
        "data_dump_ror_display_name",
        "input_domain",
        "data_dump_domain",
    ]
    requires_data_source = True

    def run(self, ctx: ValidatorContext) -> list[dict]:
        if ctx.json_dir is not None:
            return self._run_json(ctx)
        elif ctx.csv_file is not None:
            return self._run_csv(ctx)
        return []

    def _run_json(self, ctx: ValidatorContext) -> list[dict]:
        domain_dict = preprocess_data_source(ctx.data_source.get_all_records())
        results = []
        records = read_json_dir(ctx.json_dir)
        for record in records:
            record_id = record.get("id", "")
            issue_url = record_id
            display_name = get_ror_display_name(record)
            domains = get_domains(record)
            for domain in domains:
                normalized = normalize_domain(domain)
                if not normalized:
                    continue
                match = domain_dict.get(normalized)
                if match:
                    results.append({
                        "issue_url": issue_url,
                        "ror_display_name": display_name,
                        "ror_id": record_id,
                        "data_dump_id": match["ror_id"],
                        "data_dump_ror_display_name": match["ror_display_name"],
                        "input_domain": domain,
                        "data_dump_domain": match["original_domain"],
                    })
        return results

    def _run_csv(self, ctx: ValidatorContext) -> list[dict]:
        domain_dict = preprocess_data_source(ctx.data_source.get_all_records())
        results = []
        rows = read_csv(ctx.csv_file)
        for row in rows:
            record_id = row.get("id", "").strip()
            issue_url = row.get("html_url", "")
            display_name = row.get("names.types.ror_display", "").strip()
            domains_raw = row.get("domains", "").strip()
            if not domains_raw:
                continue
            domains = [d.strip() for d in domains_raw.split(";") if d.strip()]
            for domain in domains:
                normalized = normalize_domain(domain)
                if not normalized:
                    continue
                match = domain_dict.get(normalized)
                if match:
                    results.append({
                        "issue_url": issue_url,
                        "ror_display_name": display_name,
                        "ror_id": record_id,
                        "data_dump_id": match["ror_id"],
                        "data_dump_ror_display_name": match["ror_display_name"],
                        "input_domain": domain,
                        "data_dump_domain": match["original_domain"],
                    })
        return results
