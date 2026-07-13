#!/usr/bin/env python3
"""
VAT report script using the OLD VAT code scheme (2025 and earlier).

Key difference from main.py: this script determines VAT treatment from the
**existing Exact Online VAT codes** combined with a GL-account-based Margin
lookup (Margin vs non-Margin).  The newer main.py derives VAT treatment
entirely from a **GL-account → Category** mapping (FLT, NFT, PUR, …) and
counterparty geography, ignoring the legacy Exact VAT codes.

Pipeline:
1. Load raw transaction lines CSV (e.g. 20260129_transaction_lines_Q3.csv).
2. Filter out lines where VAT code is blank or "0" / "No VAT".
3. Assign Margin based on GL account (from gl_margin_lookup.csv).
4. Assign Box based on VAT code + Margin + GL type.
5. Build pivot: VAT code, VAT description, GL code, GL description, Margin, Box,
   Amount sum, Transaction count.
6. Generate ICP report (EU B2B, Box 3B) and VAT declaration summary.

Outputs XLSX files to output/ folder.
Applies to 2025 and earlier quarterly data.  For 2026+ use app/main.py.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import pandas as pd

# Columns we need from the raw transaction CSV
REQUIRED_COLUMNS = [
    "vat_code",
    "vat_code_description",
    "vat_type",
    "gl_account_code",
    "gl_account_description",
    "amount_dc",
    "account_code",
    "account_name",
]

# VAT code values and description that mean "exclude" (Blanks and 0 per manual)
VAT_CODE_BLANK_OR_ZERO = {"", "0", "0.0"}
VAT_DESCRIPTION_NO_VAT = "no vat"

CHUNK_SIZE = 20_000
DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_TMP_DIR = Path(__file__).resolve().parent.parent / "tmp"

# EU country codes (excluding NL which is domestic)
EU_COUNTRY_CODES = {
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR",
    "HU", "IE", "IT", "LV", "LT", "LU", "MT", "PL", "PT", "RO", "SK", "SI",
    "ES", "SE"
}


def _normalize_gl_code(gl_code) -> str:
    """Normalize GL code to string, stripped."""
    if pd.isna(gl_code):
        return ""
    return str(gl_code).strip()


def _normalize_vat_code(vat_code) -> str:
    """Normalize VAT code to string, stripped."""
    if pd.isna(vat_code):
        return ""
    s = str(vat_code).strip()
    # Handle float-like strings (e.g., "2.0" -> "2")
    if s.endswith(".0"):
        s = s[:-2]
    return s


def load_margin_lookup(path: Path) -> dict[str, str]:
    """Load GL code → Margin value from CSV."""
    lookup: dict[str, str] = {}
    if not path.exists():
        return lookup
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Strip keys to handle padded CSV headers (e.g. " margin" → "margin")
            trimmed = {k.strip(): v for k, v in row.items()}
            gl_code = (trimmed.get("gl_code") or "").strip()
            margin = (trimmed.get("margin") or "").strip()
            if gl_code:
                lookup[gl_code] = margin
    return lookup


def load_gl_category_lookup(path: Path) -> dict[str, str]:
    """
    Load GL code → product category from data/gl_category_lookup.csv.

    Categories: FLT (flight margin/commission), NFT (non-flight margin/
    commission), PAS (pass-through cost/turnover), PUR (purchase/expense),
    FXE (FX markup, treated as exempt), REF (refund).

    This is the source of truth for Box assignment (see get_box) - Exact's
    vat_code field is not trusted for this, since it can be inconsistent or
    stale during a VAT-scheme migration (confirmed with Dima 2026-07-13).
    """
    lookup: dict[str, str] = {}
    if not path.exists():
        return lookup
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            gl_code = (row.get("gl_account_code") or "").strip()
            category = (row.get("category") or "").strip()
            if gl_code:
                lookup[gl_code] = category
    return lookup


def load_vat_validity_lookup(path: Path) -> dict[str, dict]:
    """
    Load account_code → VAT validity info from invoicees_overview.csv.

    Returns dict mapping exact_account_code to:
        {
            "valid_eu_vat": bool,
            "vat_number": str,
            "country": str,
            "country_code": str,
            "name": str
        }
    """
    lookup: dict[str, dict] = {}
    if not path.exists():
        return lookup

    # Use pandas for easier handling of the CSV
    df = pd.read_csv(path, dtype=str)

    for _, row in df.iterrows():
        account_code = str(row.get("exact_account_code") or "").strip()
        if not account_code or account_code in ("", "null", "nan"):
            continue

        # Parse valid_eu_vat_number as boolean
        valid_str = str(row.get("valid_eu_vat_number") or "").strip().lower()
        valid_eu_vat = valid_str == "true"

        vat_number = str(row.get("vat_number") or "").strip()
        if vat_number in ("", "nan", "null", "n/a"):
            vat_number = "n/a"

        country = str(row.get("country") or "").strip()
        if country in ("", "nan", "null"):
            country = "Unknown"

        country_code = str(row.get("country_code") or "").strip().upper()
        if country_code in ("", "nan", "null"):
            country_code = ""

        name = str(row.get("name") or "").strip()

        lookup[account_code] = {
            "valid_eu_vat": valid_eu_vat,
            "vat_number": vat_number,
            "country": country,
            "country_code": country_code,
            "name": name,
        }

    # C Teleport AS is our Latvian sister company.  It doesn't appear in the
    # invoicees overview because that view only contains customers, and
    # C Teleport AS is an intercompany counterparty.  We hardcode it here so
    # its transactions get the correct EU geography (valid VAT -> Box
    # 3B/1E) instead of being dropped as unknown-country.  It's booked under
    # two account codes in Exact - "34" and "442" - confirmed with Dima
    # 2026-07-13 that both are the same Latvian entity.
    for account_code in ("34", "442"):
        if account_code not in lookup:
            lookup[account_code] = {
                "valid_eu_vat": True,
                "vat_number": "LV40203039827",
                "country": "Latvia",
                "country_code": "LV",
                "name": "C Teleport AS",
            }

    return lookup


def get_margin(gl_code: str, margin_lookup: dict[str, str]) -> str:
    """
    Determine Margin for a GL account.

    Logic (from PRD):
    - If gl_code in lookup → use lookup value
    - If gl_code starts with "4" → blank (cost account)
    - If gl_code starts with "1" → blank (balance sheet)
    - Else → blank
    """
    norm = _normalize_gl_code(gl_code)
    if not norm:
        return ""

    # Check lookup first
    if norm in margin_lookup:
        return margin_lookup[norm]

    # Cost accounts (4xxx) and balance sheet (1xxx) get blank
    if norm.startswith("4") or norm.startswith("1"):
        return ""

    # Default: blank
    return ""


def get_box(
    vat_code: str,
    margin: str,
    gl_code: str,
    vat_type: str = "",
    country_code: str = "",
    category: str = "",
) -> str:
    """
    Determine Box for a transaction.

    For any GL categorized FLT/NFT/PAS/FXE/REF in gl_category_lookup.csv, the
    box is derived from category + customer country alone - Exact's vat_code
    is NOT trusted for the sales side, since it can be inconsistent or stale
    during a VAT-scheme migration (confirmed with Dima 2026-07-13):
      - FLT (flight margin/commission): always in scope, 1E if the customer
        is NL/EU (international passenger transport is zero-rated regardless
        of B2B status - para 6.2 ruling), out of scope if outside the EU.
      - NFT (non-flight margin/commission): 1A if NL, 3B if EU (subject to
        the invalid-VAT downgrade to 1E below), out of scope if outside the EU.
      - PAS (pass-through cost/turnover), FXE (FX markup, exempt), REF
        (refund): always out of scope, regardless of vat_code or country.
    GLs categorized PUR (purchase/expense) or not found in the category
    lookup fall through to the legacy vat_code-driven logic below - that
    covers the purchase side (4A/4B/5B) and acts as a safety net for any
    margin GL not yet added to gl_category_lookup.csv.
    """
    vc = _normalize_vat_code(vat_code)
    gl = _normalize_gl_code(gl_code)
    vt = str(vat_type).strip().upper() if vat_type and pd.notna(vat_type) else ""
    cc = str(country_code).strip().upper() if country_code and pd.notna(country_code) else ""
    cat = str(category).strip().upper() if category and pd.notna(category) else ""

    is_nl_or_eu = cc == "NL" or cc in EU_COUNTRY_CODES

    if cat == "FLT":
        return "1E" if is_nl_or_eu else ""

    if cat == "NFT":
        if cc == "NL":
            return "1A"
        if cc in EU_COUNTRY_CODES:
            return "3B"  # ICP; downgraded to 1E below if VAT is invalid/unknown
        return ""

    if cat in ("PAS", "FXE", "REF"):
        return ""

    if not vc:
        return ""

    # Helper to check GL prefix
    def gl_starts_with(*prefixes: str) -> bool:
        return any(gl.startswith(p) for p in prefixes)

    # Sales VAT Codes
    if vc == "2":
        # Ticket sales 21% NL
        if margin == "Margin":
            return "1A"
        return ""

    if vc == "6":
        # Ticket sales outside EU - never taxable in NL
        return ""

    if vc == "8":
        # Ticket Sales within EU
        if margin == "Margin":
            return "3B"  # ICP
        return ""

    if vc == "20":
        # Ticket sales NL 0%
        # Margin accounts (7xxx revenue like 7212, or 8xxx) get 1E
        if margin == "Margin" and gl_starts_with("7", "8"):
            return "1E"
        return ""

    if vc == "95":
        # Ancillary services NL
        if margin == "Margin":
            return "1A"  # Q2/Q3 2025 convention
        return ""

    if vc == "100":
        # Commission 21%
        if margin == "Margin":
            return "1A"
        return ""

    if vc == "101":
        # Commission EU
        if margin == "Margin":
            return "3B"  # ICP
        return ""

    if vc == "102":
        # Commission Non EU - outside EU
        return ""

    # New 3-letter VAT codes (rolled out by Exact Online in the last weeks of
    # Q2 2026, alongside the old numeric codes above during the transition).
    # Mapping is per Dima's Airtable VAT scheme (source of truth):
    # https://airtable.com/appPG8qsc6I48lDDX/tblejwp9mhwjrCcb8/viwFWUWmFYuXytJGy
    # Unlike the old numeric codes, the new codes are category-specific by
    # construction, so the box follows from vat_code alone (no margin check).
    if vc == "NNL":
        # Domestic supplies 21% (default NL rate)
        return "1A"

    if vc in ("FEU", "NEX"):
        # 0% VAT: flight margin to EU non-NL companies (FEU, para 6.2 ruling -
        # international passenger transport is zero-rated regardless of VAT
        # status) and non-flight margin EU-no-VAT customers (NEX, pseudo-zero)
        return "1E"

    if vc == "NEU":
        # Reverse charge: intra-EU B2B non-flight services, customer self-accounts
        return "3B"  # ICP

    if vc in ("NWW", "FWW"):
        # Out of scope: non-EU margin sales - not reported on the Dutch VAT return
        return ""

    if vc == "PAS":
        # PAS = "paid on behalf of customer". The cost leg (non-Margin GL, e.g.
        # gross Turnover) is genuinely out of scope regardless of country. But
        # Exact also tags the paired commission/markup leg (Margin GL, e.g.
        # Commission Hotels) as PAS, which is wrong - a markup was earned and
        # is taxable. For a Margin GL, resolve the box from customer country
        # instead of trusting the PAS tag (confirmed with Dima 2026-07-13).
        if margin != "Margin":
            return ""  # cost leg: genuinely out of scope
        if cc == "NL":
            return "1A"
        if cc in EU_COUNTRY_CODES:
            return "3B"  # ICP; downgraded to 1E below if VAT is invalid/unknown
        return ""  # non-EU or unknown customer: out of scope, like NWW

    if vc == "FIN":
        # Exempt: payment method fees (Ecommpay, Amex). In scope for VAT but
        # exemption applied (requires explicit invoice text) - no box.
        return ""

    # Purchase VAT Codes
    # vat_type "I" = Input/purchase (actual cost/asset line, VAT deductible)
    # vat_type "O", "P" = offset/accrual entries (balance sheet, excluded)
    is_input_purchase = (vt == "I")

    # For VAT 10/12, also exclude balance sheet accounts (1xxx except 150, 160)
    def is_cost_or_asset_gl() -> bool:
        if gl in ("150", "160"):
            return True  # Fixed assets
        if gl_starts_with("4", "7"):
            return True  # Cost accounts
        return False

    if vc == "3":
        # NL VAT 9%
        if is_input_purchase:
            return "5B"
        return ""

    if vc == "4":
        # NL VAT 21%
        if is_input_purchase:
            return "5B"
        return ""

    if vc == "10":
        # Purchases EU 21%
        if is_input_purchase and is_cost_or_asset_gl():
            return "4B, 5B"
        return ""

    if vc == "12":
        # Purchases outside EU
        if is_input_purchase and is_cost_or_asset_gl():
            return "4A, 5B"
        return ""

    # New 3-letter purchase codes (see note above new sales codes)
    if vc == "UWW":
        # Reverse-charged purchases from outside the EU
        if is_input_purchase:
            return "4A, 5B"
        return ""

    if vc == "UEU":
        # Reverse-charged purchases from EU suppliers
        if is_input_purchase:
            return "4B, 5B"
        return ""

    if vc in ("UNL", "UN9"):
        # Domestic purchases, 21% (UNL) or reduced 9% (UN9) - deductible input VAT only
        if is_input_purchase:
            return "5B"
        return ""

    # Unknown VAT code
    return ""


def get_adjusted_box(original_box: str, vat_valid: bool, country_code: str) -> str:
    """
    Adjust box assignment based on VAT validity.

    If original box is 3B (EU B2B) but customer has invalid VAT,
    reclassify to 1E (0% export services).

    Rule: Box 3B should ONLY contain transactions that qualify for ICP.
    If VAT is not valid (or unknown), the turnover goes to 1E instead.
    """
    if original_box != "3B":
        return original_box

    # For 3B eligibility, customer must have valid EU VAT
    # If VAT is invalid OR unknown (not in lookup), reclassify to 1E
    if not vat_valid:
        return "1E"

    # Also reclassify if country is not EU (data quality issue in source)
    # But only if country_code is known and not EU
    if country_code and country_code not in EU_COUNTRY_CODES:
        return "1E"

    return original_box


def _is_blank_or_no_vat(row: pd.Series) -> bool:
    """True if this row should be excluded (blank VAT code or 0 / No VAT)."""
    vc = row.get("vat_code")
    if pd.isna(vc):
        return True
    vc_str = str(vc).strip()
    if vc_str in VAT_CODE_BLANK_OR_ZERO:
        return True
    vc_desc = row.get("vat_code_description")
    if pd.notna(vc_desc) and str(vc_desc).strip().lower() == VAT_DESCRIPTION_NO_VAT:
        return True
    return False


def load_and_filter(path: Path) -> pd.DataFrame:
    """Read CSV in chunks, keep only required columns, filter out blank/0/No VAT."""
    # dtype is pinned explicitly (str for text columns, float for amount_dc) to avoid
    # a pandas chunked-read bug where per-chunk dtype inference mismatches trip an
    # IndexError inside _concatenate_chunks when concatenating chunks with usecols.
    dtypes = {c: str for c in REQUIRED_COLUMNS}
    dtypes["amount_dc"] = float
    chunks = []
    for chunk in pd.read_csv(
        path, usecols=REQUIRED_COLUMNS, dtype=dtypes, chunksize=CHUNK_SIZE
    ):
        mask = ~chunk.apply(_is_blank_or_no_vat, axis=1)
        chunks.append(chunk.loc[mask])
    if not chunks:
        return pd.DataFrame(columns=REQUIRED_COLUMNS)
    return pd.concat(chunks, ignore_index=True)


def enrich_with_vat_validity(
    df: pd.DataFrame, vat_lookup: dict[str, dict]
) -> pd.DataFrame:
    """
    Enrich transactions with VAT validity info from lookup.

    Adds columns: vat_valid, vat_number_lookup, country_lookup, country_code_lookup
    """
    df = df.copy()

    def get_vat_info(account_code):
        code = str(account_code).strip() if pd.notna(account_code) else ""
        # Handle float-like codes (e.g., "123.0" -> "123")
        if code.endswith(".0"):
            code = code[:-2]
        return vat_lookup.get(code, {})

    # Extract info for each row
    vat_info = df["account_code"].apply(get_vat_info)

    df["vat_valid"] = vat_info.apply(lambda x: x.get("valid_eu_vat", False))
    df["vat_number_lookup"] = vat_info.apply(lambda x: x.get("vat_number", "n/a"))
    df["country_lookup"] = vat_info.apply(lambda x: x.get("country", "Unknown"))
    df["country_code_lookup"] = vat_info.apply(lambda x: x.get("country_code", ""))

    return df


def build_icp_report(df: pd.DataFrame, vat_lookup: dict[str, dict]) -> pd.DataFrame:
    """
    Build ICP report from transactions.

    ICP includes only:
    - Box 3B transactions (EU B2B)
    - With valid EU VAT numbers
    - Revenue accounts (GL starting with 8)

    Output columns: Code, Name, Amount, Round, Vat number, Country
    """
    output_columns = ["Code", "Name", "Amount", "Round", "Vat number", "Country"]

    if df.empty:
        return pd.DataFrame(columns=output_columns)

    # Filter for ICP-eligible transactions:
    # - Original box is 3B
    # - VAT is valid
    # - GL starts with 8 (revenue accounts)
    mask = (
        (df["original_box"] == "3B")
        & (df["vat_valid"] == True)
        & (df["GL_code"].str.startswith("8"))
    )

    icp_df = df.loc[mask].copy()

    if icp_df.empty:
        return pd.DataFrame(columns=output_columns)

    # Group by VAT number (not account_code) — ICP report must have one row per
    # VAT number.  Multiple Exact accounts can share the same VAT number (e.g.
    # related sub-entities), and the tax authority rejects duplicate VAT numbers.
    agg = (
        icp_df.groupby("vat_number_lookup", dropna=False)
        .agg(
            Name=("account_name", "first"),
            Amount=("amount_dc", "sum"),
            account_code=("account_code", "first"),
            country=("country_lookup", "first"),
        )
        .reset_index()
    )

    # Build output
    agg["Code"] = agg["account_code"].apply(
        lambda x: int(float(x)) if pd.notna(x) and str(x).replace(".", "").isdigit() else x
    )
    agg["Round"] = agg["Amount"].round(0).astype(int)
    agg["Vat number"] = agg["vat_number_lookup"]
    agg["Country"] = agg["country"]

    # Sort by Country, then Name
    agg = agg.sort_values(["Country", "Name"]).reset_index(drop=True)

    return agg[output_columns]


def build_invalid_vat_report(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build report of transactions reclassified from 3B to 1E due to invalid VAT.

    For audit purposes.
    """
    output_columns = [
        "account_code",
        "account_name",
        "vat_number",
        "country",
        "amount_sum",
        "original_box",
        "adjusted_box",
    ]

    if df.empty:
        return pd.DataFrame(columns=output_columns)

    # Filter for reclassified transactions (original 3B, now 1E)
    mask = (df["original_box"] == "3B") & (df["Box"] == "1E")

    invalid_df = df.loc[mask].copy()

    if invalid_df.empty:
        return pd.DataFrame(columns=output_columns)

    # Group by account
    agg = (
        invalid_df.groupby("account_code", dropna=False)
        .agg(
            account_name=("account_name", "first"),
            vat_number=("vat_number_lookup", "first"),
            country=("country_lookup", "first"),
            amount_sum=("amount_dc", "sum"),
        )
        .reset_index()
    )

    agg["original_box"] = "3B"
    agg["adjusted_box"] = "1E"

    # Sort by country, then account name
    agg = agg.sort_values(["country", "account_name"]).reset_index(drop=True)

    return agg[output_columns]


def build_pivot(
    df: pd.DataFrame,
    margin_lookup: dict[str, str],
    vat_lookup: dict[str, dict] | None = None,
    category_lookup: dict[str, str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Build VAT pivot with Margin and Box assigned, handling VAT validity.

    If vat_lookup is provided, adjusts Box for invalid VAT (3B → 1E).

    Returns:
        (pivot_df, enriched_df) - pivot for output, enriched df for ICP generation
    """
    output_columns = [
        "VAT_code",
        "VAT_description",
        "GL_code",
        "GL_description",
        "Margin",
        "Box",
        "Amount_sum",
        "Transaction_count",
    ]

    if df.empty:
        return pd.DataFrame(columns=output_columns), df

    df = df.copy()

    # Normalize columns
    df["VAT_code"] = df["vat_code"].apply(_normalize_vat_code)
    df["VAT_description"] = df["vat_code_description"].fillna("").astype(str).str.strip()
    df["GL_code"] = df["gl_account_code"].apply(_normalize_gl_code)
    df["GL_description"] = df["gl_account_description"].fillna("").astype(str).str.strip()
    df["amount_dc"] = pd.to_numeric(df["amount_dc"], errors="coerce").fillna(0)

    # Assign Margin
    df["Margin"] = df["GL_code"].apply(lambda gl: get_margin(gl, margin_lookup))

    # Assign Category (FLT/NFT/PAS/PUR/FXE/REF) - source of truth for Box on
    # the sales side, see get_box docstring
    category_lookup = category_lookup or {}
    df["Category"] = df["GL_code"].apply(lambda gl: category_lookup.get(gl, ""))

    # Normalize vat_type
    df["vat_type_norm"] = df["vat_type"].fillna("").astype(str).str.strip().str.upper()

    # Enrich with VAT validity/country if lookup provided. Done before Box
    # assignment because get_box() needs customer country to resolve PAS on a
    # Margin GL (see get_box docstring).
    if vat_lookup:
        df = enrich_with_vat_validity(df, vat_lookup)
    else:
        df["vat_valid"] = True
        df["vat_number_lookup"] = "n/a"
        df["country_lookup"] = "Unknown"
        df["country_code_lookup"] = ""

    # Assign original Box (before VAT validity adjustment)
    df["original_box"] = df.apply(
        lambda row: get_box(
            row["VAT_code"], row["Margin"], row["GL_code"], row["vat_type_norm"],
            row["country_code_lookup"], row["Category"],
        ),
        axis=1
    )

    # Adjust box for invalid VAT (3B -> 1E)
    df["Box"] = df.apply(
        lambda row: get_adjusted_box(
            row["original_box"],
            row["vat_valid"],
            row["country_code_lookup"]
        ),
        axis=1
    )

    # Group by VAT code, VAT description, GL code, GL description, Margin, Box
    agg = (
        df.groupby(
            ["VAT_code", "VAT_description", "GL_code", "GL_description", "Margin", "Box"],
            dropna=False,
        )
        .agg(
            Amount_sum=("amount_dc", "sum"),
            Transaction_count=("amount_dc", "count"),
        )
        .reset_index()
    )

    # Round amounts
    agg["Amount_sum"] = agg["Amount_sum"].round(2)

    # Sort by VAT code, GL code
    agg = agg.sort_values(["VAT_code", "GL_code"]).reset_index(drop=True)

    return agg[output_columns], df


def build_vat_declaration(pivot: pd.DataFrame) -> pd.DataFrame:
    """
    Build VAT declaration summary from pivot.

    Aggregates by Box for VAT return filing.
    """
    BOX_DESCRIPTIONS = {
        "1A": "Domestic services at 21% VAT (hotel commissions, SaaS, ancillary markups to NL customers)",
        "1E": "Zero-rated services (flight intermediation margins; EU services to customers with invalid VAT)",
        "3B": "EU B2B reverse charge (margins on flights, hotels, ancillaries to EU customers with valid VAT)",
        "4A, 5B": "Non-EU purchases (reverse charge on imports)",
        "4B, 5B": "EU purchases (reverse charge on intra-community acquisitions)",
        "5B": "Domestic purchases (deductible input VAT at 21% or 9%)",
        "5B Pre-tax": "Total pre-tax base for deductible input VAT (sum of 4A, 4B, 5B)",
    }

    output_columns = ["Box", "Description", "Turnover", "VAT_amount"]

    if pivot.empty:
        return pd.DataFrame(columns=output_columns)

    # Filter to rows with a Box
    pivot_with_box = pivot[pivot["Box"].notna() & (pivot["Box"] != "")].copy()

    if pivot_with_box.empty:
        return pd.DataFrame(columns=output_columns)

    # Group by Box
    agg = (
        pivot_with_box.groupby("Box", dropna=False)
        .agg(Turnover=("Amount_sum", "sum"))
        .reset_index()
    )

    # Calculate VAT amount (21% for all boxes ending in A or B)
    def calc_vat(row):
        box = row["Box"]
        turnover = row["Turnover"]
        # Check if box ends with 'A' or 'B'
        if box and (box.endswith("A") or box.endswith("B")):
            return round(abs(turnover) * 0.21)
        return 0

    agg["VAT_amount"] = agg.apply(calc_vat, axis=1).astype(int)

    # Round turnover
    agg["Turnover"] = agg["Turnover"].round(0).astype(int)

    # Negate signs for revenue boxes (1A, 1E, 3B) to show positive amounts
    revenue_boxes = ["1A", "1E", "3B"]
    agg.loc[agg["Box"].isin(revenue_boxes), "Turnover"] = -agg.loc[agg["Box"].isin(revenue_boxes), "Turnover"]

    # Add 5B Pre-tax row: sum of all boxes containing 4A, 4B, or 5B (including combinations)
    # This captures "4A", "4B", "5B", "4A, 5B", "4B, 5B", etc.
    pretax_rows = agg[agg["Box"].str.contains("4A|4B|5B", regex=True, na=False)]
    if not pretax_rows.empty:
        pretax_turnover = pretax_rows["Turnover"].sum()
        pretax_vat = round(abs(pretax_turnover) * 0.21)
        pretax_row = pd.DataFrame([{
            "Box": "5B Pre-tax",
            "Turnover": pretax_turnover,
            "VAT_amount": pretax_vat
        }])
        agg = pd.concat([agg, pretax_row], ignore_index=True)

    # Add human-readable descriptions
    agg["Description"] = agg["Box"].map(BOX_DESCRIPTIONS).fillna("")

    # Sort by Box
    agg = agg.sort_values("Box").reset_index(drop=True)

    return agg[output_columns]


def extract_quarter_year(filename: str, year_override: str | None = None) -> tuple[str, str]:
    """
    Extract quarter from filename and determine the data year.

    Expects format like: 20260415_transaction_lines_Q1.csv
    Returns: (quarter, year) e.g., ("Q1", "26")

    The quarter is extracted from the Q{N} in the filename.
    The year is determined by --year CLI override, or by reading the financial_year
    from the actual CSV data (done in main()).  Falls back to the filename date prefix
    minus 1 only for files dated in January (legacy exports created in early Jan for
    the previous year's Q4).
    """
    import re

    # Try to find Q1, Q2, Q3, Q4 in filename
    quarter_match = re.search(r'[_\s]Q([1-4])', filename, re.IGNORECASE)
    if quarter_match:
        quarter = f"Q{quarter_match.group(1)}"
    else:
        quarter = "Q1"  # Default

    if year_override:
        year = year_override[-2:]  # Accept "2026" or "26"
        return quarter, year

    # Fallback: use date prefix from filename
    year_match = re.match(r'(\d{4})(\d{2})', filename)
    if year_match:
        full_year = year_match.group(1)
        month = year_match.group(2)
        # If exported in January, likely contains previous year's data
        if month == "01":
            year = str(int(full_year) - 1)[-2:]
        else:
            year = full_year[-2:]
    else:
        year = "26"  # Default

    return quarter, year


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Legacy VAT pivot: raw transaction CSV → pivot CSV with Margin/Box assigned, ICP report."
    )
    parser.add_argument(
        "input_csv",
        type=Path,
        nargs="?",
        default=Path("20260129_transaction_lines_Q3.csv"),
        help="Raw transaction lines CSV (default: 20260129_transaction_lines_Q3.csv)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output CSV path (default: tmp/vat_pivot_old_<input_stem>.csv)",
    )
    parser.add_argument(
        "--invoicees",
        type=Path,
        default=None,
        help="Invoicees overview CSV for VAT validity lookup (auto-detected in data/)",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Data directory for lookups (default: data/)",
    )
    parser.add_argument(
        "--tmp-dir",
        type=Path,
        default=DEFAULT_TMP_DIR,
        help="Directory for output CSV (default: tmp/)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Directory for final XLSX reports (default: output/)",
    )
    parser.add_argument(
        "--year",
        type=str,
        default=None,
        help="Override data year (e.g. 2026 or 26). If omitted, inferred from filename.",
    )
    parser.add_argument(
        "--legacy-vat-code-box",
        action="store_true",
        help=(
            "Use the old vat_code-driven Box logic for the sales side (same "
            "methodology as Q1 2026 and earlier - trusts Exact's vat_code), "
            "instead of the GL-category-based logic used from Q2 2026 onward. "
            "Use this to file a quarter under the old treatment for filing "
            "consistency, even though the category-based logic is more correct."
        ),
    )
    args = parser.parse_args()

    input_path = args.input_csv
    if not input_path.is_file():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        return 1

    # Load margin lookup
    margin_lookup_path = args.data_dir / "gl_margin_lookup.csv"
    if not margin_lookup_path.exists():
        print(f"Warning: margin lookup not found: {margin_lookup_path}", file=sys.stderr)
        margin_lookup = {}
    else:
        margin_lookup = load_margin_lookup(margin_lookup_path)
        print(f"Loaded {len(margin_lookup)} GL codes from margin lookup")

    # Load GL category lookup (source of truth for sales-side Box assignment,
    # unless --legacy-vat-code-box asks to trust Exact's vat_code instead)
    category_lookup: dict[str, str] = {}
    if args.legacy_vat_code_box:
        print("Using legacy vat_code-driven Box logic (--legacy-vat-code-box)")
    else:
        category_lookup_path = args.data_dir / "gl_category_lookup.csv"
        if not category_lookup_path.exists():
            print(f"Warning: GL category lookup not found: {category_lookup_path}", file=sys.stderr)
        else:
            category_lookup = load_gl_category_lookup(category_lookup_path)
            print(f"Loaded {len(category_lookup)} GL codes from category lookup")

    # Load VAT validity lookup
    vat_lookup: dict[str, dict] = {}
    invoicees_path = args.invoicees
    if invoicees_path is None:
        # Auto-detect invoicees file in data directory
        invoicees_files = list(args.data_dir.glob("*invoicees_overview*.csv"))
        if invoicees_files:
            invoicees_path = invoicees_files[0]

    if invoicees_path and invoicees_path.exists():
        vat_lookup = load_vat_validity_lookup(invoicees_path)
        print(f"Loaded {len(vat_lookup)} accounts from VAT validity lookup: {invoicees_path.name}")
    else:
        print("Warning: No invoicees file found, VAT validity check disabled", file=sys.stderr)

    # Setup output paths
    args.tmp_dir.mkdir(parents=True, exist_ok=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = input_path.stem

    # Extract quarter and year from filename
    quarter, year = extract_quarter_year(input_path.name, year_override=args.year)

    if args.output is not None:
        pivot_path = args.output
    else:
        pivot_path = args.output_dir / f"VAT transaction lines {quarter}'{year}.xlsx"

    icp_path = args.output_dir / f"ICP {quarter}'{year}.xlsx"
    invalid_vat_path = args.tmp_dir / f"invalid_vat_old_{stem}.csv"
    declaration_path = args.output_dir / f"VAT final report {quarter}'{year}.xlsx"

    # Load and filter transactions
    try:
        df = load_and_filter(input_path)
    except Exception as e:
        print(f"Error reading/filtering CSV: {e}", file=sys.stderr)
        return 1

    print(f"Loaded {len(df)} filtered transaction lines")

    # Build pivot with VAT validity handling
    pivot, enriched_df = build_pivot(df, margin_lookup, vat_lookup, category_lookup)

    # Safety net: warn about Margin-classified GLs missing from the category
    # lookup - they fall through to the legacy vat_code-driven Box logic
    # instead of the category+geography rule, which may be wrong. Skipped
    # under --legacy-vat-code-box, where that fallback is the whole point.
    if not args.legacy_vat_code_box:
        uncategorized_mask = (enriched_df["Margin"] == "Margin") & (enriched_df["Category"] == "")
        uncategorized_margin_gls = sorted(
            set(zip(enriched_df.loc[uncategorized_mask, "GL_code"], enriched_df.loc[uncategorized_mask, "GL_description"]))
        )
        if uncategorized_margin_gls:
            print(
                f"Warning: {len(uncategorized_margin_gls)} Margin-classified GL(s) missing from "
                f"gl_category_lookup.csv, falling back to legacy vat_code Box logic: "
                f"{uncategorized_margin_gls}",
                file=sys.stderr,
            )

    # Save pivot as XLSX
    pivot.to_excel(pivot_path, index=False, engine='openpyxl')
    print(f"VAT pivot: {len(pivot)} rows → {pivot_path}")

    # Build and save ICP report as XLSX
    icp_report = build_icp_report(enriched_df, vat_lookup)
    icp_report.to_excel(icp_path, index=False, engine='openpyxl')
    print(f"ICP report: {len(icp_report)} customers → {icp_path}")

    # Build and save invalid VAT report
    invalid_report = build_invalid_vat_report(enriched_df)
    invalid_report.to_csv(invalid_vat_path, index=False)
    if len(invalid_report) > 0:
        invalid_total = invalid_report["amount_sum"].sum()
        print(f"Invalid VAT report: {len(invalid_report)} accounts, {invalid_total:.2f} EUR reclassified 3B→1E → {invalid_vat_path}")
    else:
        print(f"Invalid VAT report: no reclassifications → {invalid_vat_path}")

    # Build and save VAT declaration as XLSX
    declaration = build_vat_declaration(pivot)
    declaration.to_excel(declaration_path, index=False, engine='openpyxl')
    print(f"VAT declaration: {len(declaration)} boxes → {declaration_path}")

    # Validation: ICP total should match Box 3B
    # Note: ICP amounts are negative (revenue), Box 3B turnover is now positive (negated for display)
    icp_total = icp_report["Amount"].sum() if not icp_report.empty else 0
    box_3b_row = declaration[declaration["Box"] == "3B"]
    box_3b_total = box_3b_row["Turnover"].iloc[0] if not box_3b_row.empty else 0

    print(f"\n=== Validation ===")
    print(f"ICP total (sum of Amount): {icp_total:.2f}")
    print(f"Box 3B turnover: {box_3b_total}")
    # Compare absolute values since signs were negated in declaration
    if abs(abs(round(icp_total)) - abs(box_3b_total)) <= 1:
        print("✓ ICP matches Box 3B")
    else:
        print(f"⚠ ICP vs Box 3B difference: {abs(round(icp_total)) - abs(box_3b_total)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
