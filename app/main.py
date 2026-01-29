"""
VAT code assignment pipeline: read transaction CSV, assign GL category and
counterparty geography, write temporary CSVs under tmp/ (including VAT and ICP pivots).
"""

import argparse
import csv
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd

from app.geography import get_geography, load_country_is_eu


def _load_country_full_names(csv_path: Path) -> dict[str, str]:
    """Load country code → Full name from counterparty country CSV (Code, Full name)."""
    result: dict[str, str] = {}
    if not csv_path.exists():
        return result
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = (row.get("Code") or "").strip()
            name = (row.get("Full name") or "").strip()
            if code:
                result[code] = name or code
    return result


def _load_vat_code_box_icp_lookup(csv_path: Path) -> tuple[dict[str, list[str]], dict[str, bool]]:
    """
    Load Vat code → VAT box / ICP from data/vat_code_box_icp_lookup.csv.
    Columns: Vat code, VAT box, ICP (boolean: TRUE/FALSE).
    Returns (vat_code → list of boxes, vat_code → ICP boolean).
    Codes with no box have an empty list; codes with multiple boxes (e.g. PUR-EU-RC → 4B, 5B) appear in multiple rows.
    """
    boxes: dict[str, list[str]] = {}
    icp: dict[str, bool] = {}
    if not csv_path.exists():
        return boxes, icp
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = (row.get("Vat code") or "").strip()
            box = (row.get("VAT box") or "").strip()
            icp_raw = (row.get("ICP") or "").strip().upper()
            if not code:
                continue
            if code not in boxes:
                boxes[code] = []
            if box:
                boxes[code].append(box)
            icp[code] = icp.get(code, False) or (icp_raw in ("TRUE", "1", "YES"))
    return boxes, icp


from app.gl_category import (
    get_category,
    is_balance_sheet_account,
    load_balance_sheet_codes,
    load_gl_name_lookup,
    load_ledger_descriptions,
    load_lookup,
    normalize_gl_code,
)
from app.vat_code import CATEGORIES_REQUIRING_GEOGRAPHY, get_vat_code_and_treatment


def _trim_account_code(value) -> str:
    return str(value).strip() if value is not None and pd.notna(value) else ""


def _write_missing_counterparties_log(
    tmp_dir: Path,
    missing: list[str],
    categories_requiring_geography: list[str],
    acc_to_categories: dict[str, list[str]],
    acc_to_name: dict[str, str] | None = None,
) -> None:
    """Write a log file when counterparties are missing: missing account codes, company names, and VAT categories that require geography."""
    acc_to_name = acc_to_name or {}
    tmp_dir.mkdir(parents=True, exist_ok=True)
    log_path = tmp_dir / "missing_counterparties.log"
    with log_path.open("w", encoding="utf-8") as f:
        f.write("Missing counterparties error log\n")
        f.write("=" * 60 + "\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")
        f.write("VAT categories that require counterparty in invoicees (geography-dependent):\n")
        f.write("  " + ", ".join(categories_requiring_geography) + "\n\n")
        f.write("Missing account_code(s) (not found in invoicees overview):\n")
        for acc in missing:
            name = acc_to_name.get(acc, "").strip() or "(no name)"
            cats = acc_to_categories.get(acc, [])
            cat_str = " (categories: " + ", ".join(cats) + ")" if cats else ""
            f.write(f"  {acc!r}  {name}{cat_str}\n")
        f.write(f"\nTotal missing: {len(missing)}\n")
    print(f"Log written to {log_path}", file=sys.stderr)


def run(
    transaction_csv_path: Path,
    data_dir: Path,
    tmp_dir: Path,
    invoicees_path: Path,
    country_path: Path,
    gl_lookup_path: Path,
    vat_box_icp_lookup_path: Path,
) -> None:
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # Load lookups
    vat_code_to_boxes, vat_code_to_icp = _load_vat_code_box_icp_lookup(vat_box_icp_lookup_path)
    gl_lookup = load_lookup(gl_lookup_path)
    gl_name_lookup = load_gl_name_lookup(gl_lookup_path)
    ledger_path = data_dir / "Acount ledger.csv"
    ledger_descriptions = load_ledger_descriptions(ledger_path) if ledger_path.exists() else {}
    classification_path = data_dir / "GL accounts classification.csv"
    balance_sheet_codes = load_balance_sheet_codes(classification_path) if classification_path.exists() else set()
    country_is_eu = load_country_is_eu(country_path)
    invoicees = pd.read_csv(invoicees_path, dtype={"exact_account_code": str})
    invoicees["exact_account_code_trimmed"] = invoicees["exact_account_code"].map(_trim_account_code)
    # Normalize to string so lookup matches transaction account_code (which may be str or read as int)
    invoicees["exact_account_code_trimmed"] = invoicees["exact_account_code_trimmed"].astype(str).str.strip()
    # Drop rows with empty account code; keep first per account so index is unique
    invoicees = invoicees[invoicees["exact_account_code_trimmed"].str.len() > 0]
    invoicees = invoicees.drop_duplicates(subset=["exact_account_code_trimmed"], keep="first")
    # Use string keys so lookup matches transaction account_code (pandas may read codes as int or str)
    indexed = invoicees.set_index("exact_account_code_trimmed")
    invoicees_by_account = {str(k).strip(): v for k, v in indexed.to_dict("index").items()}

    # Read transactions (chunked for large files). Detect encoding by BOM.
    with open(transaction_csv_path, "rb") as f:
        bom = f.read(2)
    encoding = "utf-16" if bom in (b"\xff\xfe", b"\xfe\xff") else "utf-8"
    chunks = pd.read_csv(
        transaction_csv_path,
        encoding=encoding,
        chunksize=10000,
        dtype={"gl_account_code": str, "account_code": str},
        low_memory=False,
    )
    all_rows: list[pd.DataFrame] = []
    for chunk in chunks:
        chunk["account_code_trimmed"] = chunk["account_code"].map(_trim_account_code)
        chunk["gl_account_code_norm"] = chunk["gl_account_code"].apply(
            lambda x: str(x).strip() if pd.notna(x) else ""
        )
        chunk["category"] = chunk["gl_account_code_norm"].map(lambda c: get_category(c, gl_lookup))
        # Exclude balance sheet accounts (01/02/03/09 per GL accounts classification) from VAT categories
        if balance_sheet_codes:
            balance_mask = chunk["gl_account_code_norm"].apply(
                lambda c: is_balance_sheet_account(c, balance_sheet_codes)
            )
            chunk.loc[balance_mask, "category"] = None
        all_rows.append(chunk)
    transactions = pd.concat(all_rows, ignore_index=True)

    # Only FLT and NFT require counterparty in invoicees to derive geography.
    # FXE, PAS, REF do not use geography. PUR (non-NL) is RC anyway, so we do not raise for PUR.
    cat_str = transactions["category"].astype(str).str.strip().str.upper()
    with_geo_category = transactions[
        transactions["category"].notna()
        & (cat_str.str.len() > 0)
        & cat_str.isin(CATEGORIES_REQUIRING_GEOGRAPHY)
    ]
    # Normalize to string so we match invoicees index (avoid int "1015" vs str "1015" mismatch)
    distinct_accounts_for_vat = set(
        str(x).strip() if x is not None and pd.notna(x) else ""
        for x in with_geo_category["account_code_trimmed"].unique()
    )

    # Step 3: log missing counterparties (FLT/NFT) but do not raise; continue to produce outputs
    missing = [a for a in distinct_accounts_for_vat if a not in invoicees_by_account]
    if missing:
        missing_df = with_geo_category[with_geo_category["account_code_trimmed"].fillna("").isin(missing)]
        acc_to_categories = (
            missing_df.groupby("account_code_trimmed", dropna=False)["category"]
            .apply(lambda s: sorted(set(str(c).strip().upper() for c in s.unique())))
            .to_dict()
        )
        if "account_name" in missing_df.columns:
            acc_to_name = (
                missing_df.groupby("account_code_trimmed", dropna=False)["account_name"]
                .apply(lambda s: next((str(x).strip() for x in s if pd.notna(x) and str(x).strip()), ""))
                .to_dict()
            )
        else:
            acc_to_name = {}
        _write_missing_counterparties_log(
            tmp_dir=tmp_dir,
            missing=sorted(missing),
            categories_requiring_geography=sorted(CATEGORIES_REQUIRING_GEOGRAPHY),
            acc_to_categories=acc_to_categories,
            acc_to_name=acc_to_name,
        )
        print(f"Warning: {len(missing)} counterparty(ies) not in invoicees (see {tmp_dir / 'missing_counterparties.log'}). Continuing.", file=sys.stderr)

    # Step 3: build counterparty → geography for ALL accounts that appear in transactions with a category
    with_category_any = transactions[
        transactions["category"].notna() & (transactions["category"].astype(str).str.strip().str.len() > 0)
    ]
    distinct_accounts_all = set(
        str(x).strip() if x is not None and pd.notna(x) else ""
        for x in with_category_any["account_code_trimmed"].unique()
    )
    counterparties = []
    for acc in sorted(distinct_accounts_all):
        row = invoicees_by_account.get(acc, {})
        if row:
            country_code = row.get("country_code") or ""
            valid_vat = row.get("valid_eu_vat_number")
            geo = get_geography(country_code, valid_vat, country_is_eu)
            vat_number = row.get("vat_number") or "n/a"
            if pd.isna(vat_number):
                vat_number = "n/a"
            company_name = (row.get("name") or "").strip() or ""
        else:
            country_code = ""
            vat_number = "n/a"
            geo = "UNKNOWN"
            company_name = ""
        counterparties.append({
            "company": acc,
            "company_name": company_name,
            "country": country_code,
            "vat_number": vat_number,
            "geography": geo,
        })
    counterparties_df = pd.DataFrame(counterparties)
    counterparties_df.to_csv(tmp_dir / "counterparties_geography.csv", index=False)
    geo_by_account = {r["company"]: r["geography"] for _, r in counterparties_df.iterrows()}

    # Step 2: aggregate by GL
    amount_dc = pd.to_numeric(transactions["amount_dc"], errors="coerce").fillna(0)
    transactions = transactions.assign(amount_dc_numeric=amount_dc)
    with_cat = transactions[transactions["category"].notna()].copy()
    # no_cat: only truly uncategorized (no VAT category and not balance sheet)
    is_balance = (
        transactions["gl_account_code_norm"].apply(
            lambda c: is_balance_sheet_account(c, balance_sheet_codes)
        )
        if balance_sheet_codes
        else pd.Series(False, index=transactions.index)
    )
    no_cat = transactions[transactions["category"].isna() & ~is_balance].copy()

    def agg_gl(df: pd.DataFrame, use_category: bool) -> pd.DataFrame:
        g = df.groupby("gl_account_code_norm", dropna=False)
        out = g.agg(
            transaction_count=("id", "count"),
            sum_amount_dc=("amount_dc_numeric", "sum"),
        ).reset_index()
        out = out.rename(columns={"gl_account_code_norm": "gl_account_code"})
        if use_category:
            out["category"] = out["gl_account_code"].map(g["category"].first())
        def _gl_name(c):
            norm = normalize_gl_code(c)
            return gl_name_lookup.get(norm, "") or ledger_descriptions.get(norm, "")
        out["gl_account_name"] = out["gl_account_code"].map(_gl_name)
        out = out.sort_values("gl_account_code")
        return out

    gl_with = agg_gl(with_cat, use_category=True)
    gl_no = agg_gl(no_cat, use_category=False)
    gl_with.to_csv(tmp_dir / "gl_accounts_with_category.csv", index=False)
    gl_no.to_csv(tmp_dir / "gl_accounts_no_category.csv", index=False)

    # Step 4: transactions with category → add Geography, derived_vat_code, treatment, gl_account_name, company_name
    # Original vat_code from source is never overwritten; our assignment is written to derived_vat_code.
    company_name_by_account = {r["company"]: r["company_name"] for _, r in counterparties_df.iterrows()}
    out_rows = []
    for _, row in transactions.iterrows():
        base = row.to_dict()
        cat = base.get("category")
        if pd.isna(cat) or cat is None or cat == "":
            continue
        acc = base.get("account_code_trimmed") or _trim_account_code(base.get("account_code"))
        geo = geo_by_account.get(acc, "UNKNOWN")
        derived_vat_code, treatment = get_vat_code_and_treatment(str(cat), str(geo))
        base["Category"] = cat
        base["Geography"] = "" if str(cat) in ("FXE", "PAS", "REF") else geo
        base["derived_vat_code"] = derived_vat_code
        base["treatment"] = treatment
        base["Box"] = ", ".join(vat_code_to_boxes.get((derived_vat_code or "").strip(), []))
        norm_gl = normalize_gl_code(base.get("gl_account_code_norm") or "")
        gl_name = gl_name_lookup.get(norm_gl, "") or ledger_descriptions.get(norm_gl, "")
        base["gl_account_name"] = gl_name if gl_name else (
            base.get("gl_account_description") if pd.notna(base.get("gl_account_description")) else ""
        )
        cname = company_name_by_account.get(acc, "")
        base["company_name"] = cname if cname else (
            base.get("account_name") if pd.notna(base.get("account_name")) else ""
        )
        out_rows.append(base)
    if out_rows:
        out_df = pd.DataFrame(out_rows)
        out_df.to_csv(tmp_dir / "transactions_with_vat_code.csv", index=False)
    else:
        out_df = pd.DataFrame(
            columns=list(transactions.columns) + ["Category", "Geography", "derived_vat_code", "treatment", "Box"]
        )
        out_df.to_csv(tmp_dir / "transactions_with_vat_code.csv", index=False)

    # ICP report pivot: filter by lookup ICP=TRUE (Box 3B counterparties)
    country_full_names = _load_country_full_names(country_path)
    icp_mask = out_df["derived_vat_code"].map(lambda c: vat_code_to_icp.get((c or "").strip(), False))
    icp_tx = out_df.loc[icp_mask]
    if (
        not icp_tx.empty
        and "amount_dc_numeric" in out_df.columns
    ):
        icp_agg = (
            icp_tx.groupby("account_code_trimmed", dropna=False)
            .agg(
                Amount=("amount_dc_numeric", "sum"),
                company_name=("company_name", "first"),
            )
            .reset_index()
            .rename(columns={"account_code_trimmed": "Code", "company_name": "Name"})
        )
        # Enrich with vat_number and country from counterparties
        acc_to_vat = counterparties_df.set_index("company")["vat_number"].to_dict()
        acc_to_country_code = counterparties_df.set_index("company")["country"].to_dict()
        icp_agg["Vat number"] = icp_agg["Code"].map(
            lambda c: acc_to_vat.get(c, "n/a") if pd.notna(c) else "n/a"
        )
        icp_agg["Vat number"] = icp_agg["Vat number"].fillna("n/a").astype(str)
        icp_agg["Country"] = icp_agg["Code"].map(
            lambda c: country_full_names.get(
                (acc_to_country_code.get(c) or "").strip(), (acc_to_country_code.get(c) or "")
            )
            if pd.notna(c)
            else ""
        )
        icp_agg["Round"] = icp_agg["Amount"].round(0).astype("int64")
        icp_agg["Name"] = icp_agg["Name"].fillna("")
        icp_agg["Country"] = icp_agg["Country"].fillna("")
        icp_agg = icp_agg[["Code", "Name", "Amount", "Round", "Vat number", "Country"]]
        icp_agg = icp_agg.sort_values(by=["Country", "Name"], na_position="last")
        icp_agg.to_csv(tmp_dir / "icp_report_pivot.csv", index=False)
    else:
        pd.DataFrame(
            columns=["Code", "Name", "Amount", "Round", "Vat number", "Country"]
        ).to_csv(tmp_dir / "icp_report_pivot.csv", index=False)

    # VAT report pivot: group by Box, Vat code, GL account (code + name concatenated)
    if not out_df.empty and "amount_dc_numeric" in out_df.columns:
        box_code_gl_amounts: list[tuple[str, str, str, float]] = []
        for _, row in out_df.iterrows():
            code = (row.get("derived_vat_code") or "").strip()
            amount = float(row.get("amount_dc_numeric", 0) or 0)
            gl_code = (row.get("gl_account_code_norm") or row.get("gl_account_code") or "").strip()
            gl_name = (row.get("gl_account_name") or "").strip()
            gl_display = f"{gl_code} - {gl_name}" if gl_code and gl_name else (gl_code or gl_name or "")
            for box in vat_code_to_boxes.get(code, []):
                box_code_gl_amounts.append((box, code, gl_display, amount))
        if box_code_gl_amounts:
            vat_pivot_df = pd.DataFrame(
                box_code_gl_amounts,
                columns=["Box", "Vat code", "GL_account", "amount"],
            )
            vat_pivot_df = (
                vat_pivot_df.groupby(["Box", "Vat code", "GL_account"], as_index=False)
                .agg(Sum_amount=("amount", "sum"), transaction_count=("amount", "count"))
            )
            vat_pivot_df = vat_pivot_df.sort_values(["Box", "Vat code", "GL_account"])
            vat_pivot_df.to_csv(tmp_dir / "vat_report_pivot.csv", index=False)
        else:
            pd.DataFrame(
                columns=["Box", "Vat code", "GL_account", "Sum_amount", "transaction_count"]
            ).to_csv(tmp_dir / "vat_report_pivot.csv", index=False)
    else:
        pd.DataFrame(
            columns=["Box", "Vat code", "GL_account", "Sum_amount", "transaction_count"]
        ).to_csv(tmp_dir / "vat_report_pivot.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="VAT code assignment: assign GL category and geography, write tmp CSVs.")
    parser.add_argument("transaction_csv", type=Path, help="Path to transaction lines CSV")
    parser.add_argument("--data-dir", type=Path, default=Path("data"), help="Data directory (default: data)")
    parser.add_argument("--tmp-dir", type=Path, default=Path("tmp"), help="Output directory for temporary CSVs (default: tmp)")
    args = parser.parse_args()

    data_dir = args.data_dir
    tmp_dir = args.tmp_dir
    invoicees_path = data_dir / "20260129_invoicees_overview.csv"
    country_path = data_dir / "Coutnerparty country.csv"
    gl_lookup_path = data_dir / "gl_category_lookup.csv"
    vat_box_icp_lookup_path = data_dir / "vat_code_box_icp_lookup.csv"

    if not args.transaction_csv.exists():
        print(f"Error: transaction CSV not found: {args.transaction_csv}", file=sys.stderr)
        sys.exit(1)
    if not invoicees_path.exists():
        print(f"Error: invoicees overview not found: {invoicees_path}", file=sys.stderr)
        sys.exit(1)
    if not country_path.exists():
        print(f"Error: counterparty country file not found: {country_path}", file=sys.stderr)
        sys.exit(1)
    if not gl_lookup_path.exists():
        print(f"Error: GL category lookup not found: {gl_lookup_path}", file=sys.stderr)
        sys.exit(1)
    if not vat_box_icp_lookup_path.exists():
        print(f"Error: VAT code / box / ICP lookup not found: {vat_box_icp_lookup_path}", file=sys.stderr)
        sys.exit(1)

    try:
        run(
            transaction_csv_path=args.transaction_csv,
            data_dir=data_dir,
            tmp_dir=tmp_dir,
            invoicees_path=invoicees_path,
            country_path=country_path,
            gl_lookup_path=gl_lookup_path,
            vat_box_icp_lookup_path=vat_box_icp_lookup_path,
        )
        print(f"Done. Outputs written to {tmp_dir}")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
