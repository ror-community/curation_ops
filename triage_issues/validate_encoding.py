def validate_encoding(encoding):
    valid_fields = ['status', 'established', 'geonames', 'domains', 'fundref.all', 'fundref.preferred', 'grid.all', 'grid.preferred', 'isni.all', 'isni.preferred', 'wikidata.all', 'wikidata.preferred', 'website', 'wikipedia', 'acronym', 'alias', 'label', 'ror_display', 'types']
    non_repeating_fields = ['status', 'established', 'geonames']
    repeating_fields = ['domains', 'fundref.all', 'fundref.preferred', 'grid.all', 'grid.preferred', 'isni.all', 'isni.preferred', 'wikidata.all', 'wikidata.preferred', 'website', 'wikipedia', 'acronym', 'alias', 'label', 'ror_display', 'types']
    valid_operations = ['.add', '.delete', '.replace']
    remove = ["Update: ", "$"]
    for r in remove:
        encoding = encoding.replace(r, "")
    input_parts = encoding.split('|')
    valid_parts = ["Update:"]
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
            elif operation in ['add', 'delete'] and field not in repeating_fields:
                continue
            valid_parts.append(f"{field}{operation}=={value}")
    result = " | ".join(valid_parts) + "$"
    if result == "Update:$" or result == "Update: $":
        return None
    return result
