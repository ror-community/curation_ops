from collections import defaultdict

def validate_encoding(encoding):
    valid_fields = ['status', 'established', 'geonames', 'domains', 'fundref.all', 'fundref.preferred', 'grid.all', 'grid.preferred', 'isni.all', 'isni.preferred', 'wikidata.all', 'wikidata.preferred', 'website', 'wikipedia', 'acronym', 'alias', 'label', 'ror_display', 'types']
    non_repeating_fields = ['status', 'established', 'geonames']
    repeating_fields = ['domains', 'fundref.all', 'fundref.preferred', 'grid.all', 'grid.preferred', 'isni.all', 'isni.preferred', 'wikidata.all', 'wikidata.preferred', 'website', 'wikipedia', 'acronym', 'alias', 'label', 'ror_display', 'types']
    valid_operations = ['.add', '.delete', '.replace']
    remove = ["Update: ", "$"]
    for r in remove:
        encoding = encoding.replace(r, "")
    input_parts = encoding.split('|')
    field_values = defaultdict(list)
    for part in input_parts:
        part = part.strip()
        operation = None
        for op in valid_operations:
            if op in part:
                operation = op
                break
        if operation is None:
            continue
        field_and_value = part.split('==')
        if len(field_and_value) != 2:
            continue
        else:
            field, value = field_and_value
            field = field.replace(operation, "")

            if field not in valid_fields:
                continue
            elif operation in ['.add', '.delete'] and field not in repeating_fields:
                continue
            field_values[field + operation].append(value)
    valid_parts = []
    for field_operation, values in field_values.items():
        concatenated_values = "; ".join(values)
        valid_parts.append(f"{field_operation}=={concatenated_values}")
    result = "Update: " + " | ".join(valid_parts) + "$"
    if result == "Update:$" or result == "Update: $":
        return None
    return result
