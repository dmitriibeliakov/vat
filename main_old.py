#!/usr/bin/env python3
"""
Legacy VAT report script: raw transaction CSV → pivot for manual Box/Margin.

Follows docs/How to file VAT and ICP manually.md:
1. Load raw transaction lines CSV (e.g. 20260129_transaction_lines_Q3.csv).
2. Filter out lines where VAT code is blank or "0" / "No VAT".
3. Build pivot: VAT code+Description, GL code+Description, Amount DC sum,
   Account code+name, Country code, Geography.
4. Add empty columns "Box" and "Margin". Save to CSV in tmp/.

VAT codes to exclude (Exact Online export):
- Blank: vat_code is NaN or empty.
- 0 / No VAT: vat_code is 0 or 0.0, or vat_code_description is "No VAT".
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# Columns we need from the raw transaction CSV
REQUIRED_COLUMNS = [
    "vat_code",
    "vat_code_description",
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
DEFAULT_TMP_DIR = Path(__file__).resolve().parent / "tmp"


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
    chunks = []
    for chunk in pd.read_csv(path, usecols=REQUIRED_COLUMNS, chunksize=CHUNK_SIZE):
        mask = ~chunk.apply(_is_blank_or_no_vat, axis=1)
        chunks.append(chunk.loc[mask])
    if not chunks:
        return pd.DataFrame(columns=REQUIRED_COLUMNS)
    return pd.concat(chunks, ignore_index=True)


def build_pivot(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pivot: group by VAT code+Description, GL code+Description, Account code+name,
    and sum amount_dc. Add Country code, Geography (empty), Box, Margin (empty).
    """
    if df.empty:
        out = pd.DataFrame(
            columns=[
                "VAT_code_Description",
                "GL_code_Description",
                "Amount_DC_sum",
                "Account_code_name",
                "Country_code",
                "Geography",
                "Box",
                "Margin",
            ]
        )
        return out

    # Coerce amount to numeric
    df = df.copy()
    df["amount_dc"] = pd.to_numeric(df["amount_dc"], errors="coerce").fillna(0)

    # Concat columns for grouping (handle NaN)
    df["VAT_code_Description"] = (
        df["vat_code"].astype(str).str.strip()
        + " "
        + df["vat_code_description"].fillna("").astype(str).str.strip()
    ).str.strip()
    df["GL_code_Description"] = (
        df["gl_account_code"].fillna("").astype(str).str.strip()
        + " "
        + df["gl_account_description"].fillna("").astype(str).str.strip()
    ).str.strip()
    df["Account_code_name"] = (
        df["account_code"].fillna("").astype(str).str.strip()
        + " "
        + df["account_name"].fillna("").astype(str).str.strip()
    ).str.strip()
    df["Country_code"] = ""
    df["Geography"] = ""

    agg = (
        df.groupby(
            [
                "VAT_code_Description",
                "GL_code_Description",
                "Account_code_name",
                "Country_code",
                "Geography",
            ],
            dropna=False,
        )["amount_dc"]
        .sum()
        .reset_index()
    )
    agg.rename(columns={"amount_dc": "Amount_DC_sum"}, inplace=True)
    agg["Amount_DC_sum"] = agg["Amount_DC_sum"].round(2)
    agg["Box"] = ""
    agg["Margin"] = ""

    # Column order as requested
    out = agg[
        [
            "VAT_code_Description",
            "GL_code_Description",
            "Amount_DC_sum",
            "Account_code_name",
            "Country_code",
            "Geography",
            "Box",
            "Margin",
        ]
    ]
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Legacy VAT pivot: raw transaction CSV → pivot CSV in tmp (exclude blank/0/No VAT)."
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
        "--tmp-dir",
        type=Path,
        default=DEFAULT_TMP_DIR,
        help="Directory for output CSV (default: tmp/)",
    )
    args = parser.parse_args()

    input_path = args.input_csv
    if not input_path.is_file():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        return 1

    if args.output is not None:
        out_path = args.output
    else:
        args.tmp_dir.mkdir(parents=True, exist_ok=True)
        out_path = args.tmp_dir / f"vat_pivot_old_{input_path.stem}.csv"

    try:
        df = load_and_filter(input_path)
    except Exception as e:
        print(f"Error reading/filtering CSV: {e}", file=sys.stderr)
        return 1

    pivot = build_pivot(df)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pivot.to_csv(out_path, index=False)
    print(f"Filtered {len(df)} lines → pivot {len(pivot)} rows → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
