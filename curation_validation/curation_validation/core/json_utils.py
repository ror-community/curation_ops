from curation_validation.core.normalize import normalize_wikipedia_url


def flatten_json(obj, parent_key="", sep="_"):
    flattened = {}

    def flatten(obj, name=""):
        if type(obj) is dict:
            for item in obj:
                flatten(obj[item], name + item + sep)
        elif type(obj) is list:
            i = 0
            for item in obj:
                flatten(item, name + str(i) + sep)
                i += 1
        else:
            flattened[name[:-len(sep)] if name else name] = obj

    flatten(obj)
    return flattened


def simplify_json(j):
    simplified = {}
    name_types = ['ror_display', 'alias', 'label', 'acronym']
    link_types = ['wikipedia', 'website']
    external_id_types = ['isni', 'fundref', 'wikidata']

    simplified['status'] = [j.get('status', [])]
    simplified['types'] = j.get('types', [])
    simplified['established'] = [j.get('established', [])]
    simplified['locations.geonames_id'] = [
        location['geonames_id'] for location in j.get('locations', [])
    ]

    for name_type in name_types:
        simplified[f'names.types.{name_type}'] = [
            name['value'] for name in j.get('names', [])
            if name_type in name.get('types', [])
        ]

    for link_type in link_types:
        values = [
            link['value'] for link in j.get('links', [])
            if link.get('type') == link_type
        ]
        if link_type == 'wikipedia':
            values = [normalize_wikipedia_url(v) for v in values]
        simplified[f'links.type.{link_type}'] = values

    for id_type in external_id_types:
        ids_of_type = [
            ext_id for ext_id in j.get('external_ids', [])
            if ext_id.get('type') == id_type
        ]
        simplified[f'external_ids.type.{id_type}.preferred'] = [
            ext_id['preferred'] for ext_id in ids_of_type
        ]
        all_id_values = [ext_id.get('all', []) for ext_id in ids_of_type]
        simplified[f'external_ids.type.{id_type}.all'] = (
            sum(all_id_values, [])
            if all(isinstance(v, list) for v in all_id_values)
            else []
        )

    all_values = []
    for key, value in simplified.items():
        all_values += value
    all_values = [value for value in all_values if value]
    simplified['all'] = all_values
    return simplified


def simplify_and_invert_json(j):
    simplified = {}
    name_types = ['ror_display', 'alias', 'label', 'acronym']
    link_types = ['wikipedia', 'website']
    external_id_types = ['isni', 'fundref', 'wikidata']

    simplified['status'] = [j.get('status', [])]
    simplified['types'] = j.get('types', [])
    simplified['established'] = [j.get('established', [])]
    simplified['locations.geonames_id'] = [
        location['geonames_id'] for location in j.get('locations', [])
    ]

    for name_type in name_types:
        simplified[f'names.types.{name_type}'] = [
            name['value'] for name in j.get('names', [])
            if name_type in name.get('types', [])
        ]

    for link_type in link_types:
        simplified[f'links.type.{link_type}'] = [
            link['value'] for link in j.get('links', [])
            if link.get('type') == link_type
        ]

    for id_type in external_id_types:
        ids_of_type = [
            ext_id for ext_id in j.get('external_ids', [])
            if ext_id.get('type') == id_type
        ]
        simplified[f'external_ids.type.{id_type}.preferred'] = [
            ext_id['preferred'] for ext_id in ids_of_type
        ]
        all_id_values = [ext_id.get('all', []) for ext_id in ids_of_type]
        simplified[f'external_ids.type.{id_type}.all'] = (
            sum(all_id_values, [])
            if all(isinstance(v, list) for v in all_id_values)
            else []
        )

    all_values = []
    inverted = {}
    for key, values in simplified.items():
        for value in values:
            if value:
                all_values.append(value)
                inverted.setdefault(value, []).append(key)
    simplified['all'] = all_values
    return simplified, inverted
