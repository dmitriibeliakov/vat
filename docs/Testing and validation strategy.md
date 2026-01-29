# Testing and Validation Strategy

**Purpose:** Ensure no transactions are left out and that mapping (Category, Geography, VAT code, treatment) is correct.  
**Related:** [PRD VAT code assignment script](PRD%20VAT%20code%20assignment%20script.md).

---

## 1. What Can Go Wrong (Failure Modes)

### 1.1 Transactions left out or lost

| Risk | Cause | Where it shows |
|------|--------|----------------|
| **Transaction not in any output** | Logic bug: row skipped or filtered incorrectly. | Row count or amount mismatch vs input. |
| **Transaction has no category** | GL code missing from lookup (typo, range not expanded, new GL in Exact). | In `gl_accounts_no_category.csv`; not in `transactions_with_vat_code.csv`. |
| **Transaction’s company not in invoicees** | New customer or export out of date. | Script raises exception (by design). |
| **Duplicate or missing rows in output** | Bug in join/merge or in writing CSVs. | Duplicate `id`s or count ≠ input count. |
| **Amount drift** | Wrong column used, wrong sign, or aggregation error. | Sum of `amount_dc` in outputs ≠ input. |

### 1.2 Incorrect mapping (wrong Category, Geography, VAT code, or treatment)

| Risk | Cause | Where it shows |
|------|--------|----------------|
| **Wrong GL → Category** | Lookup typo, wrong range (e.g. 4xxx), or code in wrong category in scheme. | Revenue reported as PUR, or vice versa. |
| **Wrong Geography** | Country not in country file, `Is EU` wrong, or `valid_eu_vat_number` misinterpreted. | NL/EU/EX/XX/UNKNOWN wrong → wrong VAT code. |
| **Wrong VAT code or treatment** | Bug in Category+Geography matrix (e.g. PUR-EX, FXE/PAS/REF). | Wrong box (1A, 1E, 3B, etc.) or wrong treatment. |
| **Trim/normalization** | `account_code` vs `exact_account_code` (spaces, case) not aligned. | Company not found (exception) or wrong counterparty matched. |
| **UNKNOWN overused** | Country missing from country file or invoicees missing country. | Many transactions with Geography=UNKNOWN. |

### 1.3 Configuration and data quality

| Risk | Cause | Mitigation |
|------|--------|------------|
| **Lookup file stale** | New GL codes or new countries not in CSVs. | Regular refresh; tests that flag new GLs with no category. |
| **Scheme change** | `vat_code_scheme.md` updated but code or lookup not. | Tests derived from scheme (golden matrix). |
| **Wrong file path or encoding** | Paths or CSV encoding differ per environment. | Config or CLI args; tests with fixtures. |

---

## 2. Tests That Give Clarity the Mapping Is Correct

### 2.1 Unit tests (per module, known inputs → expected outputs)

**`gl_category.py`**

- Given a GL code in the lookup → returns the correct category (FLT, NFT, FXE, PAS, REF, PUR).
- Given a GL code **not** in the lookup → returns `None` (or equivalent “no category”).
- Edge: empty string, whitespace-only, numeric vs string (e.g. `8021` vs `"8021"`) — behaviour documented and tested.

**`geography.py`**

- **NL:** `country_code=NL` → geography NL (ignore VAT validity for NL).
- **EU:** EU country (e.g. DE) + `valid_eu_vat_number=true` → EU.
- **EX:** EU country + `valid_eu_vat_number=false` (or missing) → EX.
- **XX:** Non-EU country (from country file) → XX.
- **UNKNOWN:** Country code not in country file → UNKNOWN; counterparty not in invoicees → UNKNOWN (or exception at pipeline level).
- Edge: missing `country_code`, missing `valid_eu_vat_number`, `Is EU` casing (TRUE/FALSE/True/False).

**`vat_code.py`**

- **Matrix coverage:** For every (Category, Geography) pair in the scheme, one test: input (Category, Geography) → expected (vat_code, treatment). Pairs to cover:
  - FLT: NL, EU, EX, XX
  - NFT: NL, EU, EX, XX
  - FXE: any geography (or empty) → vat_code=FXE, treatment=EXM, geography output empty
  - PAS: any → vat_code=PAS, treatment=OOS, geography empty
  - REF: any → vat_code=REF, treatment=OOS, geography empty
  - PUR: NL, EU, EX, XX → PUR-NL (21/9), PUR-EU (RC), PUR-EX (RC), PUR-XX (RC)
- **UNKNOWN:** Category + Geography=UNKNOWN → defined behaviour (e.g. still output a code or flag; document).
- **No invented codes:** Only vat_codes that exist in the scheme (including PUR-EX).

These tests act as **living documentation** of the scheme and catch typos or matrix bugs.

### 2.2 Output / report validation tests (separate test file)

Run the pipeline on a **fixed fixture** (small transaction CSV + small lookups) and validate the **output files** (the “reports”):

**Completeness (no transactions left out)**

- **Row count:**  
  `count(transactions_with_vat_code) + count(transactions_with_no_category)` = total rows in input transaction CSV.  
  (Transactions with no category are those whose GL is in `gl_accounts_no_category`; you need either a list of such transaction ids or a sum of counts per GL to reconstruct total “no category” count.)
- **Amount reconciliation:**  
  Sum of `amount_dc` over **all** input transactions =  
  Sum of `amount_dc` in `gl_accounts_with_category` (over all rows) +  
  Sum of `amount_dc` in `gl_accounts_no_category` (over all rows).  
  So: `sum(input.amount_dc) = sum(gl_with.amount_dc) + sum(gl_no.amount_dc)`.
- **No duplicates:**  
  Transaction id (e.g. `id`) in `transactions_with_vat_code.csv` appears at most once.
- **Counterparties:**  
  Every distinct trimmed `account_code` in the transaction file appears in `counterparties_geography.csv` (and the pipeline raises if any are missing from invoicees).

**Consistency (mapping rules respected)**

- **Allowed VAT codes:**  
  Every `vat_code` in `transactions_with_vat_code.csv` is in the allowed set (FLT-NL, FLT-EU, FLT-EX, FLT-XX, NFT-NL, NFT-EU, NFT-EX, NFT-XX, FXE, PAS, REF, PUR-NL, PUR-EU, PUR-EX, PUR-XX, and optionally UNKNOWN if you support it).
- **Allowed geography:**  
  Geography is one of: NL, EU, EX, XX, UNKNOWN, or empty (for FXE, PAS, REF).
- **(vat_code, treatment) pairs:**  
  Every (vat_code, treatment) in the output matches the scheme (e.g. FLT-NL→0, NFT-EU→RC, FXE→EXM, PUR-EX→RC). Can be implemented as a small allowed list or by re-deriving treatment from vat_code in the test and asserting equality.
- **FXE / PAS / REF:**  
  Rows with Category in (FXE, PAS, REF) have empty Geography and the single code FXE, PAS, or REF with correct treatment.

**Optional: baseline / regression**

- For a **known** transaction file (e.g. Q4 2025 export), store baseline totals: e.g. sum of `amount_dc` per `vat_code`, or per Box (1A, 1E, 3B, …). After pipeline run, compare current totals to baseline and fail if different (after you’ve verified the baseline is correct). Helps catch “silent” mapping or logic changes.

### 2.3 Where to put the tests

- **Unit tests:**  
  `tests/test_gl_category.py`, `tests/test_geography.py`, `tests/test_vat_code.py` (or under `app/tests/` if you prefer). Use small CSV fixtures or in-memory data.
- **Output / report validation:**  
  `tests/test_output_reports.py` (or `tests/test_pipeline_output.py`): runs the main script on a fixture transaction file + fixture lookups, then checks the four output CSVs for the invariants above (counts, sums, allowed codes, (vat_code, treatment) consistency).

This gives you:

1. **Confidence no one is left out:** count and amount reconciliation + duplicate check.  
2. **Confidence mapping is correct:** unit tests for every (Category, Geography) and output checks that only valid codes and treatments appear and match the scheme.

---

## 3. Summary Table

| Goal | Test type | What to check |
|------|-----------|----------------|
| No transactions lost | Output validation | Row count + amount sum: input = with_category + no_category |
| No duplicate rows | Output validation | Unique transaction id in `transactions_with_vat_code` |
| Every counterparty resolved | Output validation + design | Exception if company missing; all account_codes in counterparties file |
| GL → Category correct | Unit (gl_category) | Known GL → expected category; unknown GL → no category |
| Country/VAT → Geography correct | Unit (geography) | NL, EU, EX, XX, UNKNOWN cases + edge cases |
| Category+Geography → VAT code/treatment correct | Unit (vat_code) | Full matrix + FXE/PAS/REF + PUR-EX |
| Only scheme-compliant codes in output | Output validation | All vat_code and (vat_code, treatment) in allowed set |
| FXE/PAS/REF no geography | Output validation | Empty geography, single code, correct treatment |

Implementing these in a **separate test file** (and unit tests per module) gives clear, repeatable checks that the mapping is correct and that nothing is left out.
