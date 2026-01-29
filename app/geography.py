"""
Geography (NL, EU, EX, XX, UNKNOWN) from counterparty country and VAT validity.
Uses invoicees overview and data/Coutnerparty country.csv (Code, Is EU).
"""

import csv
from pathlib import Path


def _parse_bool(value: str | bool) -> bool:
    """Normalize string to bool; 'true'/'TRUE' → True, else False."""
    if isinstance(value, bool):
        return value
    return str(value).strip().upper() == "TRUE"


def load_country_is_eu(csv_path: str | Path) -> dict[str, bool]:
    """
    Load country code → Is EU from counterparty country CSV.
    Columns: Code, Is EU. Returns dict mapping normalized Code (e.g. 'NL', 'DE') → bool.
    """
    path = Path(csv_path)
    result: dict[str, bool] = {}
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # Column may be "Is EU" (with space)
        for row in reader:
            code = (row.get("Code") or "").strip().upper()
            is_eu_raw = row.get("Is EU") or ""
            if code:
                result[code] = _parse_bool(is_eu_raw)
    return result


def get_geography(
    country_code: str | None,
    valid_eu_vat_number: str | bool,
    country_is_eu_map: dict[str, bool],
) -> str:
    """
    Map (country_code, valid_eu_vat_number, country_is_eu) → geography.

    Rules:
    - NL: country_code == 'NL' → NL
    - EU: country is EU (from map), not NL, valid_eu_vat_number true → EU
    - EX: EU country (not NL), valid_eu_vat_number false or missing → EX
    - XX: country in map with Is EU False → XX
    - UNKNOWN: country not in map or missing/invalid code → UNKNOWN
    """
    code = (country_code or "").strip().upper()
    if not code:
        return "UNKNOWN"
    is_eu = country_is_eu_map.get(code)
    if is_eu is None:
        return "UNKNOWN"
    valid_vat = _parse_bool(valid_eu_vat_number)

    if code == "NL":
        return "NL"
    if is_eu:
        return "EU" if valid_vat else "EX"
    return "XX"
