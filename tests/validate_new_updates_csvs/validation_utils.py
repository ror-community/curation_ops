from constants import ACRONYMS_PATTERN, NAMES_PATTERN, URL_PATTERN, WIKIPEDIA_URL_PATTERN, ISNI_PATTERN, WIKIDATA_PATTERN, FUNDREF_PATTERN, GEONAMES_PATTERN


def parse_update_field(update_str):
    updates = {}
    parts = update_str.split(';')
    for part in parts:
        subparts = part.split('==', 1)
        if len(subparts) == 2:
            change_type, value = subparts[0].strip(), subparts[1].strip()
            if change_type in updates:
                updates[change_type].append(value)
            else:
                updates[change_type] = [value]
        else:
            updates.setdefault('replace', []).append(subparts[0].strip())
    return updates


def parse_row_updates(row):
    row_updates = {}
    for field, update_str in row.items():
        row_updates[field] = parse_update_field(update_str)
    return row_updates


def validate_updates(row):
    valid_fields = [
        'status', 
        'types', 
        'names.types.acronym', 
        'names.types.alias', 
        'names.types.label', 
        'names.types.ror_display', 
        'links.type.website', 
        'established', 
        'links.type.wikipedia', 
        'external_ids.type.isni.preferred',
        'external_ids.type.isni.all',
        'external_ids.type.wikidata.preferred',
        'external_ids.type.wikidata.all',
        'external_ids.type.fundref.preferred',
        'external_ids.type.fundref.all',
        'locations.geonames_id'
    ]
    row_updates = parse_row_updates(row)
    errors = []
    field_value_pairs = []
    for field, updates in row_updates.items():
        if field in valid_fields:
            for change_type, values in updates.items():
                if change_type not in ['add', 'delete', 'replace']:
                    errors.append(f"Invalid change type: '{change_type}' in field '{field}'. Valid types are: ['add', 'delete', 'replace'].")
                    continue
                for value in values:
                    if value:
                        if change_type == 'delete':
                            # Skip delete operations because they do not require field validation
                            continue
                        field_value_pairs.append((field, value))
    print(field_value_pairs)
    return errors, field_value_pairs


def validate_status(field_value):
    valid_types = ["active", "inactive", "withdrawn"]
    return [] if field_value and field_value in valid_types else [f"Error in 'status': Invalid value - {field_value}. Valid values are: {valid_types}"]


def validate_types(field_value):
    valid_types = ["education", "healthcare", "company",
                   "archive", "nonprofit", "government", "facility", "other"]
    field_value = field_value.split('(')[0].strip().lower()
    return [] if field_value and field_value in valid_types else [f"Error in 'types': Invalid value(s). Valid values are: {valid_types}"]


def validate_acronyms(field_value):
    return [] if field_value and ACRONYMS_PATTERN.match(field_value) else [f"Warning in '{field_value}': Potential invalid value(s) - {field_value}. Expected format: uppercase letters, numbers, and spaces"]


def validate_names(field_value):
    return [] if field_value and NAMES_PATTERN.match(field_value) else [f"Warning in '{field_value}':  Expected format: Include language tagging - 'name*language'"]


def validate_links(field_value):
    return [] if field_value and URL_PATTERN.match(field_value) else [f"Error in 'links': Invalid URL(s) - {field_value}. Expected format: 'http://' or 'https://' followed by the address"]


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
    return [] if field_value and WIKIPEDIA_URL_PATTERN.match(field_value) else [f"Error in 'wikipedia_url': Invalid Wikipedia URL - {field_value}. Expected format: 'http://[language_code].wikipedia.org/'"]


def validate_isni(field_value):
    return [] if field_value and ISNI_PATTERN.match(field_value) else [f"Error in 'ISNI': Invalid ISNI value(s) - {field_value}. Expected format: '[0]{4} [0-9]{4} [0-9]{4} [0-9]{3}[0-9X]' or 'delete'"]


def validate_wikidata(field_value):
    return [] if field_value and WIKIDATA_PATTERN.match(field_value) else [f"Error in 'Wikidata': Invalid Wikidata ID(s) - {field_value}. Expected format: 'Q[1-9]\d*' or 'delete'"]


def validate_fundref(field_value):
    return [] if field_value and FUNDREF_PATTERN.match(field_value) else [f"Error in 'FundRef': Invalid FundRef ID(s) - {field_value}. Expected format: '[1-9]\d+' or 'delete'"]


def validate_geonames(field_value):
    return [] if field_value and GEONAMES_PATTERN.match(field_value) else [f"Error in 'Geonames ID': Invalid or Null Geonames ID(s) - {field_value}. Expected format: '[1-9]\d+'"]


def validate_city(field_value):
    return [] if field_value else [f"Warning in 'city': no city in record"]


def validate_country(field_value):
    return [] if field_value else [f"Warning in 'country': no country in record"]


def validate_field_value(field_name, field_value):
    validation_functions = {
        'types': [validate_types],
        'status': [validate_status],
        'names.types.acronym': [validate_acronyms, validate_names],
        'names.types.alias': [validate_names],
        'names.types.label': [validate_names],
        'names.types.ror_display': [validate_names],
        'links.type.website': [validate_links],
        'established': [validate_established],
        'links.type.wikipedia': [validate_wikipedia_url],
        'external_ids.type.isni.preferred': [validate_isni],
        'external_ids.type.isni.all': [validate_isni],
        'external_ids.type.wikidata.preferred': [validate_wikidata],
        'external_ids.type.wikidata.all': [validate_wikidata],
        'external_ids.type.fundref.preferred': [validate_fundref],
        'external_ids.type.fundref.all': [validate_fundref],
        'geonames': [validate_geonames],
        'locations.geonames_id': [validate_geonames],
        'city': [validate_city],
        'country': [validate_country]
    }
    if field_name in validation_functions:
        for validation_function in validation_functions[field_name]:
            return validation_function(field_value)
    return []
