from curation_validation.validators.base import BaseValidator, ValidatorContext
from curation_validation.core.json_utils import flatten_json
from curation_validation.core.extract import extract_fields
from curation_validation.core.io import read_csv, read_json_dir

WHITESPACE_AND_PUNCTUATION = set('!#$%&*+, -./:;<=>?@\\^_`{|}~\t\n\v\f\r')


def _check_value(issue_url, record_id, field, value, results):
    if not isinstance(value, str) or not value:
        return
    if value[0] in WHITESPACE_AND_PUNCTUATION:
        results.append({
            "issue_url": issue_url,
            "record_id": record_id,
            "field": field,
            "value": value,
            "issue": "leading",
        })
    if value[-1] in WHITESPACE_AND_PUNCTUATION:
        results.append({
            "issue_url": issue_url,
            "record_id": record_id,
            "field": field,
            "value": value,
            "issue": "trailing",
        })


class LeadingTrailingValidator(BaseValidator):
    name = "leading_trailing"
    supported_formats = {"csv", "json"}
    output_filename = "leading_trailing.csv"
    output_fields = ["issue_url", "record_id", "field", "value", "issue"]

    def run(self, ctx: ValidatorContext) -> list[dict]:
        results = []

        if ctx.json_dir is not None:
            results.extend(self._run_json(ctx))
        elif ctx.csv_file is not None:
            results.extend(self._run_csv(ctx))

        return results

    def _run_json(self, ctx: ValidatorContext) -> list[dict]:
        results = []
        records = read_json_dir(ctx.json_dir)
        for record in records:
            record_id = record.get("id", "")
            issue_url = record_id
            flattened = flatten_json(record)
            for field, value in flattened.items():
                _check_value(issue_url, record_id, field, value, results)
        return results

    def _run_csv(self, ctx: ValidatorContext) -> list[dict]:
        results = []
        rows = read_csv(ctx.csv_file)
        for row in rows:
            extracted = extract_fields(row, "csv")
            record_id = ""
            id_values = extracted.get("id", [])
            if id_values:
                record_id = id_values[0]
            issue_url = row.get("html_url", "")
            for field, values in extracted.items():
                for value in values:
                    _check_value(issue_url, record_id, field, value, results)
        return results
