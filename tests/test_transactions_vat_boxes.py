"""
Tests for VAT box assignment on transactions_with_vat_code.csv.

Per docs/scheme/vat_code_scheme_temporary.md, PUR (purchases, 4xxx) must appear in box 5B.
"""

import pandas as pd
import pytest
from pathlib import Path


# Path to transactions file relative to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRANSACTIONS_CSV = PROJECT_ROOT / "tmp" / "transactions_with_vat_code.csv"


def _load_transactions():
    """Load transactions CSV; use only required columns to support large files."""
    cols = ["gl_account_code", "gl_account_code_norm", "Box"]
    return pd.read_csv(TRANSACTIONS_CSV, usecols=cols, dtype=str)


def _normalize_account_code(series: pd.Series) -> pd.Series:
    """Normalize GL account code for comparison (strip whitespace)."""
    return series.astype(str).str.strip()


@pytest.fixture(scope="module")
def transactions():
    """Load transactions once per test module."""
    if not TRANSACTIONS_CSV.exists():
        pytest.skip(f"Transactions file not found: {TRANSACTIONS_CSV}")
    return _load_transactions()


def test_account_4020_in_box_5b(transactions):
    """
    All transactions with GL account 4020 must be assigned to box 5B.

    Per docs/scheme/vat_code_scheme_temporary.md: PUR (4xxx) → box 5B.
    """
    gl = _normalize_account_code(transactions["gl_account_code"])
    gl_norm = _normalize_account_code(transactions["gl_account_code_norm"])
    is_4020 = (gl == "4020") | (gl_norm == "4020")
    rows_4020 = transactions.loc[is_4020]

    assert len(rows_4020) > 0, "Expected at least one transaction with account 4020"

    box = rows_4020["Box"].fillna("").astype(str).str.strip()
    not_5b = box[~box.str.contains("5B", na=False)]
    assert len(not_5b) == 0, (
        f"Account 4020 must be in box 5B; {len(not_5b)} row(s) have Box not containing 5B: {not_5b.tolist()}"
    )
