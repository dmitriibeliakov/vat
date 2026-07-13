"""
VAT code and treatment from Category + Geography.
Implements the scheme matrix (docs/scheme/vat_code_scheme_temporary.md). VAT code format: two dashes
(category-geography-treatment), e.g. FLT-NL-0, FXE--EXM, PUR-EX-RC.
"""

# Geography-independent categories: no geography in code; geography param ignored.
_NO_GEOGRAPHY_CATEGORIES = {"FXE", "PAS", "REF"}

# Categories that require counterparty in invoicees to derive geography (NL, EU, EX, XX).
# PUR is excluded: for non-NL it is RC anyway, so we do not raise if counterparty is missing.
CATEGORIES_REQUIRING_GEOGRAPHY = {"FLT", "NFT"}

# (category, geography) → (treatment for matrix lookup). UNKNOWN treated as XX.
_MATRIX: dict[tuple[str, str], str] = {
    ("FLT", "NL"): "0",
    ("FLT", "EU"): "0",
    ("FLT", "EX"): "0",
    ("FLT", "XX"): "OOS",
    ("FLT", "UNKNOWN"): "OOS",
    ("NFT", "NL"): "21",
    ("NFT", "EU"): "RC",
    ("NFT", "EX"): "RC",
    ("NFT", "XX"): "OOS",
    ("NFT", "UNKNOWN"): "OOS",
    ("PUR", "NL"): "21",
    ("PUR", "EU"): "RC",
    ("PUR", "EX"): "RC",
    ("PUR", "XX"): "RC",
    ("PUR", "UNKNOWN"): "RC",
}

# Geography-independent: category → (vat_code_two_dashes, treatment)
_NO_GEO_CODES: dict[str, tuple[str, str]] = {
    "FXE": ("FXE--EXM", "EXM"),
    "PAS": ("PAS--OOS", "OOS"),
    "REF": ("REF--OOS", "OOS"),
}


def get_vat_code_and_treatment(category: str, geography: str) -> tuple[str, str]:
    """
    Return (vat_code, treatment) for the given Category and Geography.

    VAT code uses exactly two dashes: category-geography-treatment (e.g. FLT-NL-0,
    PUR-EX-RC). For FXE, PAS, REF geography is ignored and middle part is empty
    (e.g. FXE--EXM, PAS--OOS, REF--OOS).

    UNKNOWN geography is mapped to the same treatment as XX.
    """
    cat = (category or "").strip().upper()
    geo_raw = (geography or "").strip().upper()
    geo = "UNKNOWN" if geo_raw == "UNKNOWN" else (geo_raw if geo_raw else "XX")

    if cat in _NO_GEOGRAPHY_CATEGORIES:
        pair = _NO_GEO_CODES.get(cat)
        if pair:
            return pair
        # Fallback (should not happen)
        return (f"{cat}--OOS", "OOS")

    treatment = _MATRIX.get((cat, geo)) or _MATRIX.get((cat, "XX")) or "OOS"
    # Build two-dash code: category-geography-treatment
    vat_code = f"{cat}-{geo}-{treatment}"
    return (vat_code, treatment)
