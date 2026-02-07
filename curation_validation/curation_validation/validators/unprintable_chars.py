from curation_validation.validators.base import BaseValidator, ValidatorContext
from curation_validation.core.json_utils import flatten_json
from curation_validation.core.extract import extract_fields
from curation_validation.core.io import read_csv, read_json_dir


class UnprintableCharsValidator(BaseValidator):
    name = "unprintable-chars"
    supported_formats = {"csv", "json"}
    output_filename = "unprintable_chars.csv"
    output_fields = ["record_id", "field", "value", "unprintable_chars"]

    def run(self, ctx: ValidatorContext) -> list[dict]:
        if ctx.json_dir is not None:
            return self._run_json(ctx)
        elif ctx.csv_file is not None:
            return self._run_csv(ctx)
        return []

    def _run_json(self, ctx: ValidatorContext) -> list[dict]:
        results = []
        records = read_json_dir(ctx.json_dir)
        for record in records:
            record_id = record.get("id", "")
            flattened = flatten_json(record)
            for field, value in flattened.items():
                if not isinstance(value, str) or not value:
                    continue
                bad_chars = [ch for ch in value if not ch.isprintable()]
                if bad_chars:
                    unique_chars = sorted(set(bad_chars))
                    chars_repr = ", ".join(repr(ch) for ch in unique_chars)
                    results.append({
                        "record_id": record_id,
                        "field": field,
                        "value": value,
                        "unprintable_chars": chars_repr,
                    })
        return results

    def _run_csv(self, ctx: ValidatorContext) -> list[dict]:
        results = []
        rows = read_csv(ctx.csv_file)
        for row in rows:
            record_id = row.get("id", "")
            extracted = extract_fields(row, "csv")
            for field, values in extracted.items():
                for value in values:
                    if not isinstance(value, str) or not value:
                        continue
                    bad_chars = [ch for ch in value if not ch.isprintable()]
                    if bad_chars:
                        unique_chars = sorted(set(bad_chars))
                        chars_repr = ", ".join(repr(ch) for ch in unique_chars)
                        results.append({
                            "record_id": record_id,
                            "field": field,
                            "value": value,
                            "unprintable_chars": chars_repr,
                        })
        return results
