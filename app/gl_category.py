"""
GL account code → category lookup (FLT, NFT, FXE, PAS, REF, PUR).
Uses data/gl_category_lookup.csv. No side effects; pure lookup.
Verifies against data/GL accounts classification.csv: excludes Balance sheet and its children.
"""

import csv
from pathlib import Path


def _normalize_gl_code(gl_code: str | int | float) -> str:
    """Normalize GL code for matching: strip whitespace, coerce to string without leading zeros."""
    if gl_code is None or (isinstance(gl_code, float) and (gl_code != gl_code or gl_code == float("inf"))):
        return ""
    s = str(gl_code).strip()
    if not s:
        return ""
    try:
        return str(int(float(s)))
    except (ValueError, TypeError):
        return s


def load_lookup(csv_path: str | Path) -> dict[str, str]:
    """
    Load GL category lookup from CSV. Returns dict mapping normalized gl_account_code → category.
    Columns: gl_account_code, category (gl_name optional).
    """
    path = Path(csv_path)
    lookup: dict[str, str] = {}
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row.get("gl_account_code", "").strip()
            category = row.get("category", "").strip()
            if not code or not category:
                continue
            normalized = _normalize_gl_code(code)
            if normalized:
                lookup[normalized] = category
    return lookup


def get_category(gl_code: str | int | float, lookup: dict[str, str]) -> str | None:
    """
    Return category for the given GL code, or None if not in lookup.
    gl_code is normalized before lookup (e.g. 1300, "8021", " 4000 " all match correctly).
    """
    normalized = _normalize_gl_code(gl_code)
    return lookup.get(normalized) if normalized else None


def load_balance_sheet_codes(classification_path: str | Path) -> set[str]:
    """
    Load GL accounts classification and return the set of normalized codes that belong to
    Balance sheet: "01", "02", "03", "09" and their children — so accounts starting
    with 0 (e.g. 0905), 1, 2, 3 are treated as Balance.
    """
    path = Path(classification_path)
    balance_codes_raw: set[str] = set()
    try:
        with path.open(newline="", encoding="utf-16") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = (row.get("Code") or "").strip()
                if not code:
                    continue
                # Balance sheet: 01, 02, 03, 09 and their children (per GL accounts classification)
                if (code == "01" or code.startswith("01") or
                        code == "02" or code.startswith("02") or
                        code == "03" or code.startswith("03") or
                        code == "09" or code.startswith("09")):
                    balance_codes_raw.add(code)
    except (FileNotFoundError, KeyError, UnicodeDecodeError):
        pass
    # Also include 09xx (e.g. 0905, 0906, 0907) as Balance even if not in classification
    balance_codes_raw.add("09")
    result: set[str] = set()
    for c in balance_codes_raw:
        n = _normalize_gl_code(c)
        if n:
            result.add(n)
    return result


def is_balance_sheet_account(gl_code: str | int | float, balance_norm_codes: set[str]) -> bool:
    """
    Return True if the given GL code belongs to Balance sheet or its children (per classification).
    """
    if not balance_norm_codes:
        return False
    norm = _normalize_gl_code(gl_code)
    if not norm:
        return False
    if norm in balance_norm_codes:
        return True
    # Sub-accounts: e.g. 139.01 under 0139
    for b in balance_norm_codes:
        if b != norm and (norm.startswith(b + ".") or (len(norm) > len(b) and norm.startswith(b))):
            return True
    return False


def normalize_gl_code(gl_code: str | int | float) -> str:
    """Normalize GL code for matching (exported for use in main)."""
    return _normalize_gl_code(gl_code)


def load_gl_name_lookup(csv_path: str | Path) -> dict[str, str]:
    """
    Load GL code → description/name from the same CSV as category lookup.
    Returns dict mapping normalized gl_account_code → gl_name.
    """
    path = Path(csv_path)
    lookup: dict[str, str] = {}
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row.get("gl_account_code", "").strip()
            name = (row.get("gl_name") or "").strip()
            normalized = _normalize_gl_code(code)
            if normalized:
                lookup[normalized] = name
    return lookup


def load_ledger_descriptions(ledger_path: str | Path) -> dict[str, str]:
    """
    Load GL code → description from Account ledger CSV (Code, DescriptionDescription).
    Uses UTF-16 encoding. Returns dict mapping normalized gl_account_code → description.
    Use for GL names when not in gl_category_lookup (e.g. Balance and no-category accounts).
    """
    path = Path(ledger_path)
    lookup: dict[str, str] = {}
    try:
        with path.open(newline="", encoding="utf-16") as f:
            reader = csv.DictReader(f)
            desc_col = "DescriptionDescription"
            for row in reader:
                code = (row.get("Code") or "").strip()
                desc = (row.get(desc_col) or "").strip()
                normalized = _normalize_gl_code(code)
                if normalized:
                    lookup[normalized] = desc
    except (FileNotFoundError, UnicodeDecodeError, KeyError):
        pass
    return lookup
