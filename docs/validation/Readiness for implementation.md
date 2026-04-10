# Readiness for Implementation

**Purpose:** Checklist against the PRD to confirm we can start coding.  
**Related:** [PRD VAT code assignment script](PRD%20VAT%20code%20assignment%20script.md).

---

## 1. Summary

| Status | Item |
|--------|------|
| ✅ Ready | Transaction CSV structure matches PRD. |
| ✅ Ready | Invoicees overview has all PRD columns. |
| ✅ Ready | Counterparty country file has Code and Is EU. |
| ✅ Ready | Acount ledger exists for expanding GL ranges (4xxx, 72114–72149). |
| ⚠️ Missing | **`data/gl_category_lookup.csv`** — must be created once before the pipeline can run. |
| ⚠️ Missing | **`app/`** folder and modules (geography.py, gl_category.py, vat_code.py, entry point). |
| ⚠️ Note | Acount ledger encoding/format may need special handling. |
| ⚠️ Note | GL code normalization (transaction vs ledger vs lookup) should be consistent. |

---

## 2. Input Files vs PRD

### 2.1 Transaction lines CSV

- **PRD expects:** `gl_account_code`, `amount_dc`, `account_code` (path passed as argument).
- **Actual:** `20260129_transaction_lines_Q4.csv` in project root has:
  - `gl_account_code` ✅ (e.g. 1300, 8021)
  - `amount_dc` ✅
  - `account_code` ✅ (with leading spaces, e.g. `"                34"`)
  - `id` ✅ (for row identity and duplicate checks)
- **Verdict:** Ready. Use this file (or equivalent) as the transaction input.

### 2.2 GL category lookup

- **PRD expects:** `data/gl_category_lookup.csv` with at least `gl_account_code`, `category`.
- **Actual:** File **does not exist**. It must be **created once** from `docs/scheme/vat_code_scheme_temporary.md` (Section 7 of PRD), with ranges (72114–72149, 8112–8114, 4xxx) expanded using `data/Acount ledger.csv`.
- **Verdict:** **Missing.** Create this file (or a one-off script that generates it) before running the main pipeline. Blocking for Step 1.

### 2.3 Invoicees overview

- **PRD expects:** `exact_account_code`, `country_code`, `vat_number`, `valid_eu_vat_number`.
- **Actual:** `data/20260129_invoicees_overview.csv` header:
  - `id`, `tenant_id`, `name`, `country`, `country_code`, `vat_number`, `registration_number`, `no_vat`, `vat_status`, `valid_eu_vat_number`, `currency`, `exact_account_code`, `last_invoice_date`
  - All four PRD columns present ✅
- **Verdict:** Ready. Handle `valid_eu_vat_number` as boolean or string (`true`/`false`); normalize when comparing.

### 2.4 Counterparty country

- **PRD expects:** `Code` (ISO country code), `Is EU` (TRUE/FALSE).
- **Actual:** `data/Coutnerparty country.csv` header: `Code`, `Full name`, `Rabobank risk category`, `Is EU` ✅
- **Verdict:** Ready. Normalize `Is EU` (e.g. case-insensitive) when comparing.

### 2.5 Acount ledger (for building GL lookup only)

- **PRD expects:** Used to expand “4xxx” and possibly other ranges when creating `gl_category_lookup.csv`.
- **Actual:** `data/Acount ledger.csv` exists. Columns: `"Code"`, `"DescriptionDescription"`. Contains GL codes (e.g. 4000, 72114, 72115, …).
- **Caveats:**
  - File may be **UTF-16** encoded (BOM `ÿþ` and spaced characters in some reads). Implementation should try `utf-16` or `utf-16-le` when reading, and strip BOM if present.
  - Codes are quoted strings (e.g. `"4000"`, `"72114"`). When building the lookup, normalize to the same format used for `gl_account_code` in transactions (e.g. string, optional leading-zero handling).
- **Verdict:** Ready for use when generating `gl_category_lookup.csv`; document encoding and normalization in implementation.

---

## 3. GL Code Normalization (Recommendation)

- **Transaction CSV:** `gl_account_code` appears as numeric-like values (1300, 8021) — may be read as int or string.
- **Acount ledger:** Codes are strings, sometimes with leading zeros (e.g. `"0100"`, `"4000"`).
- **Recommendation:** When building and using `gl_category_lookup.csv`, define a single convention: e.g. store GL codes as **strings**, strip leading zeros (or consistently zero-pad to N digits) so that matching between transaction rows and the lookup is reliable. Apply the same normalization in `gl_category.py` when resolving category.

---

## 4. What Must Exist Before Coding / First Run

1. **Create `data/gl_category_lookup.csv`**  
   One-off: parse `docs/scheme/vat_code_scheme_temporary.md` GL→Category mapping, expand ranges (72114–72149, 8112–8114, 4xxx) using codes from `data/Acount ledger.csv`, output flat list with columns e.g. `gl_account_code`, `category`. Optionally add a small script `app/build_gl_lookup.py` (or in `scripts/`) so the lookup can be regenerated when the scheme changes.

2. **Create `app/` and modules**  
   As per PRD Section 12: `geography.py`, `gl_category.py`, `vat_code.py`, plus an entry point (e.g. `main.py` or CLI). Create `tmp/` when writing outputs (or document that the script creates it).

3. **Optional:** Add `tmp/` to `.gitignore` if temporary outputs should not be committed.

---

## 5. Conclusion

- **Data:** All required CSVs exist and match PRD column assumptions **except** `data/gl_category_lookup.csv`, which must be created once (and can be generated from the scheme + Acount ledger).
- **Code:** `app/` and the four-step pipeline do not exist yet; implementation can start once the GL lookup is available (or the first task can be “generate the GL lookup”).
- **Recommendation:** Start by (1) implementing the one-off GL category lookup generation and producing `data/gl_category_lookup.csv`, then (2) implement `app/` and the pipeline. Handle Acount ledger encoding (UTF-16) and GL code normalization from the beginning so all lookups and reports stay consistent.
