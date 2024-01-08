from constants import ACRONYMS_PATTERN, LABELS_PATTERN, URL_PATTERN, WIKIPEDIA_URL_PATTERN, ISNI_PATTERN, WIKIDATA_PATTERN, FUNDREF_PATTERN, GEONAMES_PATTERN


def validate_update_field(update_field):
    errors = []
    field_value_pairs = []
    valid_change_types = ['change', 'add', 'delete', 'replace']
    valid_field_names = ['name', 'status', 'established', 'wikipedia_url', 'links', 'types',
                         'aliases', 'acronyms', 'Wikidata', 'ISNI', 'FundRef', 'GRID',
                         'labels', 'relationships', 'Geonames']
    changes = update_field.split(';')
    for change in changes:
        if not change:
            continue
        parts = change.split('.', 1)
        if len(parts) != 2 or '==' not in parts[1]:
            errors.append(f"Invalid format in update_field: '{change}'. Expected format: 'change_type.field_name==field_value'")
            continue
        change_type, rest = parts
        field_name, field_value = rest.split('==', 1)
        change_type, field_name, field_value = change_type.strip(
        ), field_name.strip(), field_value.strip()
        if change_type != 'delete':
            field_value_pairs.append((field_name, field_value))
        if change_type not in valid_change_types:
            errors.append(f"Invalid change type: '{change_type}'. Valid types are: {valid_change_types}")
        if field_name not in valid_field_names:
            errors.append(f"Invalid field name: '{field_name}'. Valid field names are: {valid_field_names}")
        if change_type in ['add', 'delete'] and field_name in ['name', 'status', 'established', 'wikipedia_url']:
            errors.append(f"Incompatible change type '{change_type}' for field '{field_name}'. Expected fields: 'labels', links', 'types', 'aliases', 'acronyms'")
        if change_type == 'replace' and field_name not in ['links', 'types', 'aliases', 'acronyms', 'labels', 'ISNI', 'FundRef', 'Wikidata']:
            errors.append(f"Incompatible change type '{change_type}' for field '{field_name}'. Expected fields: 'links', 'types', 'aliases', 'acronyms'")
        if change_type == 'change' and field_name not in ['name', 'status', 'established', 'wikipedia_url', 'Geonames']:
            errors.append(f"Incompatible change type 'change' for field '{field_name}'. The only valid fields for 'change' are 'name', 'status', 'established', 'wikipedia_url', 'Geonames'")
    return errors, field_value_pairs


def validate_types(field_value):
    valid_types = {"Education", "Healthcare", "Company",
                   "Archive", "Nonprofit", "Government", "Facility", "Other"}
    return [] if field_value in valid_types else [f"Error in 'types': Invalid value(s). Valid values are: {valid_types}"]


def validate_acronyms(field_value):
    return [] if ACRONYMS_PATTERN.match(field_value) else [f"Warning in 'acronyms': Potential invalid value(s) - {field_value}. Expected format: uppercase letters, numbers, and spaces"]


def validate_labels(field_value):
    return [] if LABELS_PATTERN.match(field_value) else [f"Error in 'labels': Invalid value(s) - {field_value}. Expected format: '*[A-Za-z]{2,}'"]


def validate_links(field_value):
    return [] if URL_PATTERN.match(field_value) else [f"Error in 'links': Invalid URL(s) - {field_value}. Expected format: 'http://' or 'https://' followed by the address"]


def validate_established(field_value):
    try:
        year = int(field_value)
        if 1000 <= year <= 9999:
            return []
        else:
            return ["Error in 'established': Not a 4-digit year"]
    except ValueError:
        return [f"Error in 'established': {field_value} is not a valid year format. Expected a 4-digit year"]


def validate_wikipedia_url(field_value):
    return [] if WIKIPEDIA_URL_PATTERN.match(field_value) else [f"Error in 'wikipedia_url': Invalid Wikipedia URL - {field_value}. Expected format: 'http://[language_code].wikipedia.org/'"]


def validate_isni(field_value):
    return [] if ISNI_PATTERN.match(field_value) else [f"Error in 'ISNI': Invalid ISNI value(s) - {field_value}. Expected format: '0000 0000 0000 000X'"]


def validate_wikidata(field_value):
    return [] if WIKIDATA_PATTERN.match(field_value) else [f"Error in 'Wikidata': Invalid Wikidata ID(s) - {field_value}. Expected format: 'Q' followed by numbers"]


def validate_fundref(field_value):
    return [] if FUNDREF_PATTERN.match(field_value) else [f"Error in 'FundRef': Invalid FundRef ID(s) - {field_value}. Expected format: numbers"]


def validate_geonames(field_value):
    return [] if GEONAMES_PATTERN.match(field_value) else [f"Error in 'Geonames ID': Invalid or Null Geonames ID(s) - {field_value}. Expected format: numbers"]


def validate_city(field_value):
    return [] if field_value else [f"Warning in 'city': no city in record"]


def validate_country(field_value):
    return [] if field_value else [f"Warning in 'country': no country in record"]


def validate_field_value(field_name, field_value):
    validation_functions = {
        'types': validate_types,
        'acronyms': validate_acronyms,
        'labels': validate_labels,
        'links': validate_links,
        'established': validate_established,
        'wikipedia_url': validate_wikipedia_url,
        'isni': validate_isni,
        'wikidata': validate_wikidata,
        'fundref': validate_fundref,
        'geonames': validate_geonames,
        'geonames_id': validate_geonames,
        'city': validate_city,
        'country': validate_country
    }
    if field_name in validation_functions:
        return validation_functions[field_name](field_value)
    return []
