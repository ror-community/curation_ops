EXTRACTED_FIELDS = [
    "id",
    "status",
    "types",
    "names.types.ror_display",
    "names.types.acronym",
    "names.types.alias",
    "names.types.label",
    "links.type.website",
    "links.type.wikipedia",
    "established",
    "external_ids.type.isni.all",
    "external_ids.type.isni.preferred",
    "external_ids.type.wikidata.all",
    "external_ids.type.wikidata.preferred",
    "external_ids.type.fundref.all",
    "external_ids.type.fundref.preferred",
    "locations.geonames_id",
    "domains",
]


def extract_fields(source: dict, format: str) -> dict[str, list[str]]:
    if format == "json":
        return _extract_from_json(source)
    elif format == "csv":
        return _extract_from_csv(source)
    else:
        raise ValueError(f"Unknown format: {format}")


def _extract_from_json(record: dict) -> dict[str, list[str]]:
    result = {field: [] for field in EXTRACTED_FIELDS}

    result["id"] = [record.get("id", "")]
    result["status"] = [record.get("status", "")] if record.get("status") else []
    result["types"] = [str(t) for t in record.get("types", [])]
    result["established"] = (
        [str(record["established"])] if record.get("established") is not None else []
    )
    result["domains"] = list(record.get("domains", []))

    name_type_map = {"ror_display": [], "acronym": [], "alias": [], "label": []}
    for name in record.get("names", []):
        for ntype in name.get("types", []):
            if ntype in name_type_map:
                name_type_map[ntype].append(name.get("value", ""))
    result["names.types.ror_display"] = name_type_map["ror_display"]
    result["names.types.acronym"] = name_type_map["acronym"]
    result["names.types.alias"] = name_type_map["alias"]
    result["names.types.label"] = name_type_map["label"]

    for link in record.get("links", []):
        link_type = link.get("type")
        if link_type == "website":
            result["links.type.website"].append(link.get("value", ""))
        elif link_type == "wikipedia":
            result["links.type.wikipedia"].append(link.get("value", ""))

    for location in record.get("locations", []):
        gid = location.get("geonames_id")
        if gid is not None:
            result["locations.geonames_id"].append(str(gid))

    for ext_id in record.get("external_ids", []):
        id_type = ext_id.get("type")
        if id_type in ("isni", "wikidata", "fundref"):
            preferred = ext_id.get("preferred", "")
            all_ids = ext_id.get("all", [])
            if preferred:
                result[f"external_ids.type.{id_type}.preferred"].append(str(preferred))
            for aid in all_ids:
                result[f"external_ids.type.{id_type}.all"].append(str(aid))

    return result


def _extract_from_csv(row: dict) -> dict[str, list[str]]:
    result = {field: [] for field in EXTRACTED_FIELDS}

    for field in ["id", "status"]:
        value = row.get(field, "").strip()
        result[field] = [value] if value else []

    semicolon_fields = [
        "types",
        "names.types.ror_display",
        "names.types.acronym",
        "names.types.alias",
        "names.types.label",
        "links.type.website",
        "links.type.wikipedia",
        "external_ids.type.isni.all",
        "external_ids.type.isni.preferred",
        "external_ids.type.wikidata.all",
        "external_ids.type.wikidata.preferred",
        "external_ids.type.fundref.all",
        "external_ids.type.fundref.preferred",
        "locations.geonames_id",
        "domains",
    ]

    for field in semicolon_fields:
        raw = row.get(field, "")
        if raw and raw.strip():
            result[field] = [v.strip() for v in raw.split(";") if v.strip()]
        else:
            result[field] = []

    established = row.get("established", "").strip()
    result["established"] = [established] if established else []

    return result
