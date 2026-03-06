REQUIRED_HEADER_ALIASES = {
    "sku": {"sku", "Sku", "SKU", "model", "model_number"},
    "appliance_type": {"appliance_type", "Appliance Type", "appliance type"},
    "description": {"description", "Description", "desc"},
    "msrp": {"msrp_map", "MSRP_MAP", "MAP", "MSRP", "MSRP | MAP", "msrp", "msrp_map "},
    "your_cost": {"your_cost", "Your Cost", " Your Cost ", "cost", "your cost"},
}

OPTIONAL_HEADER_ALIASES = {
    "listed_price": {"listed_price", "Listed Price", "listed price", "listed"},
    "lowes_price": {"lowes_price", "Lowes Price", "lowes price", "lowes", "lowe's price"},
}


def normalize_header(name: str) -> str:
    raw = name.strip()
    raw_fold = raw.lower().replace(" ", "_")
    raw_fold = raw_fold.replace("'", "")
    raw_fold = raw_fold.replace("|", "_")
    raw_fold = "_".join(part for part in raw_fold.split("_") if part)
    return raw_fold


def build_header_map(fieldnames: list[str]) -> dict[str, str]:
    normalized_to_original = {}
    for original in fieldnames:
        key = normalize_header(original)
        normalized_to_original[key] = original
        
    resolved = {}
    for canonical, aliases in REQUIRED_HEADER_ALIASES.items():
        found = None
        for alias in aliases:
            alias_key = normalize_header(alias)
            if alias_key in normalized_to_original:
                found = normalized_to_original[alias_key]
                break
        if found:
            resolved[canonical] = found

    for canonical, aliases in OPTIONAL_HEADER_ALIASES.items():
        found = None
        for alias in aliases:
            alias_key = normalize_header(alias)
            if alias_key in normalized_to_original:
                found = normalized_to_original[alias_key]
                break
        if found:
            resolved[canonical] = found
            
    missing = [k for k in REQUIRED_HEADER_ALIASES if k not in resolved]
    if missing:
        raise ValueError(f"Missing required headers: {', '.join(missing)}")
    
    return resolved
