# PRD: VAT Code Assignment Script

**Version:** 1.0  
**Status:** Draft  
**Scope:** Script in `app/` that reads transaction lines CSV, assigns GL categories and counterparty geography, and outputs transactions with VAT codes.

---

## 1. Overview

The script performs four main steps:

1. Read a given transaction lines CSV and use a GL→category lookup to assign a GL account category per transaction.
2. Produce temporary summaries: GL accounts with category (count, sum amount DC) and GL accounts without category, sorted by account number.
3. Build a counterparty→geography mapping from invoicees + country data; keep only companies present in the raw transactions; output a temporary CSV.
4. For transactions that have a category, use counterparty geography to assign the VAT code; output a temporary file with transactions + Category + Geography + VAT code (and Treatment).

All temporary files are written to the `tmp/` directory. The script does not connect to any database; it operates only on local CSV files.

---

## 2. Inputs

| Input | Description | Location |
|-------|-------------|----------|
| Transaction lines CSV | Raw export from Redshift `transaction_lines` (e.g. quarter export). | Passed as argument (e.g. `YYYYMMDD_transaction_lines_Q4.csv`). |
| GL category lookup | One row per GL code → category (FLT, NFT, FXE, PAS, REF, PUR). | `data/gl_category_lookup.csv` (created once from `docs/vat_code_scheme.md`). |
| Invoicees overview | Customers with country, VAT number, validity. | `data/20260129_invoicees_overview.csv` (or dated equivalent). |
| Counterparty country | Country code → Is EU. | `data/Coutnerparty country.csv` |

**Key transaction CSV columns (assumed):**

- `gl_account_code` — GL account code (used for category lookup).
- `amount_dc` — Amount in default currency (for sums).
- `account_code` — Counterparty/customer identifier (may have leading/trailing spaces); matched to invoicees after trimming.

**Key invoicees columns:** `exact_account_code`, `country_code`, `vat_number`, `valid_eu_vat_number`.

**Key country file columns:** `Code` (ISO country code), `Is EU` (TRUE/FALSE).

---

## 3. Step 1: Read Transaction Lines and GL Category Lookup

- Read the transaction lines CSV (support large files via streaming/chunking if needed).
- Load the GL category lookup from `data/gl_category_lookup.csv` (columns: at least `gl_account_code`, `category`).
- For each transaction row, resolve category by matching `gl_account_code` to the lookup.
- **No change to transaction rows in this step**; category is used in Steps 2 and 4.

---

## 4. Step 2: GL Account Summaries (Temporary CSVs)

Produce two temporary CSVs, both sorted by GL account number.

### 4.1 With category

- **File:** `tmp/gl_accounts_with_category.csv`
- **Rows:** One per distinct GL account that has at least one transaction with an assigned category.
- **Columns:** GL account, count of transactions, sum of `amount_dc` (algebraic: positives increase, negatives decrease), assigned category.
- **Sort:** By account number (ascending).

### 4.2 Without category

- **File:** `tmp/gl_accounts_no_category.csv`
- **Rows:** One per distinct GL account that has at least one transaction with **no** assigned category (missing from lookup).
- **Columns:** GL account, count of transactions, sum of `amount_dc` (same rule).
- **Sort:** By account number (ascending).

**Rules:**

- Count = one row per transaction line (no netting).
- Sum = normal algebraic sum of `amount_dc`.

---

## 5. Step 3: Counterparty → Geography (Temporary CSV)

- **Source of customers:** `data/20260129_invoicees_overview.csv` (or equivalent).
- **Source of EU flag:** `data/Coutnerparty country.csv` (match `country_code` from invoicees to `Code` in country file; use `Is EU`).
- **Geography rules:**
  - **NL** — `country_code` = NL (Netherlands).
  - **EU** — Country is EU (from country file) and **not** NL, and `valid_eu_vat_number` = true.
  - **EX** — Country is EU and **not** NL, and `valid_eu_vat_number` = false (or missing/invalid).
  - **XX** — Country is not EU (from country file).
  - **UNKNOWN** — Counterparty not found in invoicees, or country not found in country file (e.g. missing or invalid code). Use UNKNOWN so such customers are easy to spot.

- **Filter:** Only include companies that appear in the **raw transaction file** (i.e. whose trimmed `account_code` appears as `exact_account_code` in invoicees and occurs in at least one transaction).
- **Output:** `tmp/counterparties_geography.csv`
- **Columns:** company (or identifier used in transactions), country, VAT code (e.g. VAT number or “n/a”), assigned geography.
- **Exception:** If any raw transaction has an `account_code` (trimmed) that does **not** exist in the invoicees lookup, the script must **raise an exception** and stop (do not silently skip).

---

## 6. Step 4: Transactions + Category + Geography + VAT Code (Temporary File)

- **Input:** Transactions that have an assigned **Category** from Step 1, and counterparty **Geography** from Step 3 (keyed by trimmed `account_code`).
- **Logic:** For each such transaction, derive VAT code and treatment from Category + Geography using the rules in `docs/vat_code_scheme.md`, with the following specifics:
  - **FXE, PAS, REF:** Do not depend on geography. Use VAT code = `FXE`, `PAS`, or `REF`; Geography column = empty string; Treatment = EXM, OOS, or OOS respectively.
  - **PUR + EX:** Define as **PUR-EX** with treatment **RC** (PUR-EX-RC).
  - **All other Category + Geography combinations:** As in the scheme (e.g. FLT-NL, NFT-EU, PUR-NL, etc.). Geography column = the geography code (NL, EU, EX, XX, or UNKNOWN).

- **Output:** `tmp/transactions_with_vat_code.csv`
- **Content:** One row per transaction (same granularity as input), with added columns at least:
  - **Category** — FLT | NFT | FXE | PAS | REF | PUR.
  - **Geography** — NL | EU | EX | XX | UNKNOWN, or empty string for FXE/PAS/REF.
  - **vat_code** — if present in the input, preserved as-is (never overwritten).
  - **derived_vat_code** — pipeline-assigned VAT code, e.g. FLT-NL, NFT-EU, FXE, PAS, REF, PUR-EX, etc. Used for Box/ICP lookups.
  - **treatment** — e.g. 21, 0, RC, OOS, EXM.

- **Option A (confirmed):** VAT code and Treatment are **separate columns**; for FXE/PAS/REF, Geography is left blank (empty string).

---

## 7. GL Category Lookup (One-Time Creation)

- **Source of truth:** `docs/vat_code_scheme.md` (section “GL Account → Category Mapping”).
- **Output:** `data/gl_category_lookup.csv` (flat list: one row per GL code).
- **Method:** Expand all ranges and patterns (e.g. 72114–72149, 8112–8114, 4xxx) into individual GL codes. Use `data/Acount ledger.csv` (or an agreed list) to resolve which codes exist for ranges like 4xxx. Save under `data/` so the script can load it in Step 1.
- **Columns (minimal):** `gl_account_code`, `category` (and optionally GL name if useful).

---

## 8. File and Directory Conventions

- **Temporary outputs:** All under `tmp/`.
  - `tmp/gl_accounts_with_category.csv`
  - `tmp/gl_accounts_no_category.csv`
  - `tmp/counterparties_geography.csv`
  - `tmp/transactions_with_vat_code.csv`
- **Lookup (created once):** `data/gl_category_lookup.csv`
- Script lives in `app/` (exact entry point and name TBD in implementation).

---

## 9. Error Handling

- **Missing company in lookup:** If any transaction row has a trimmed `account_code` that does not appear in the invoicees file, **raise an exception** and abort (with a clear message indicating the offending account code(s)).
- **Missing or invalid country:** Assign geography **UNKNOWN** and continue; do not abort.
- **Missing GL category:** Transaction is included in `gl_accounts_no_category.csv` and is not output in `transactions_with_vat_code.csv` (only transactions with an assigned category get a VAT code in Step 4).

---

## 10. Out of Scope (for This PRD)

- Connecting to Redshift or Exact Online.
- Generating the final VAT return or ICP report (that may consume the temporary CSVs in a later step).
- Automatic refresh of invoicees or country data; the script assumes files are already present and up to date.

---

## 11. Success Criteria

- Given a valid transaction lines CSV and the required lookup files (including `gl_category_lookup.csv`), the script runs without error and produces the four temporary CSVs in `tmp/`.
- Every transaction whose company exists in the invoicees file is either summarized in Step 2 and, if it has a category, included in Step 4 with correct Category, Geography, vat_code, and treatment.
- Any transaction whose company is not in the invoicees file causes an exception and no partial output is treated as successful.

---

## 12. App File Structure

The implementation in `app/` must follow a clear module layout. File responsibilities are:

| File | Responsibility |
|------|----------------|
| **`geography.py`** | Determining **geography** (NL, EU, EX, XX, UNKNOWN) from counterparty country and VAT validity. Uses invoicees overview and counterparty country data. |
| **`gl_category.py`** | Determining **GL account category** (FLT, NFT, FXE, PAS, REF, PUR) from GL code. Uses the GL category lookup table. |
| **`vat_code.py`** | **VAT code** and **treatment** derivation from Category + Geography. Implements the scheme matrix (including FXE/PAS/REF without geography, PUR-EX-RC, etc.). |

The main script or entry point (e.g. `main.py`, `run.py`, or CLI) in `app/` orchestrates the four steps and calls these modules; it does not duplicate their logic. This structure keeps geography, category, and VAT-code rules in one place each and makes the codebase easy to navigate and maintain.

---

## 13. Testing and Validation

To avoid transactions being left out and to ensure mapping (Category, Geography, VAT code, treatment) is correct:

- **Failure modes** and **test strategy** are described in a separate document: **[Testing and validation strategy](Testing%20and%20validation%20strategy.md)**.
- **Unit tests** per module (`gl_category.py`, `geography.py`, `vat_code.py`) with known inputs and expected outputs (including full Category+Geography matrix and edge cases).
- **Output / report validation tests** in a **separate test file** (e.g. `tests/test_output_reports.py`): run the pipeline on a fixture, then check:
  - **Completeness:** Row count and sum of `amount_dc` reconcile (input = with_category + no_category); no duplicate transaction ids; every counterparty in transactions appears in counterparties output.
  - **Mapping correctness:** Every `vat_code` and (vat_code, treatment) in the output is in the allowed scheme; FXE/PAS/REF have empty geography and correct treatment.

Implementing these tests gives clarity that no transactions are dropped and that the mapping is correct.
