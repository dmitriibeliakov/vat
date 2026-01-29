# ICP Report Format (Opgaaf ICP)

## Overview
The ICP report (Intra-Community Supply / Opgaaf ICP) is a breakdown of EU B2B sales (Box 3B) by customer, with one row per counterparty showing VAT number and amount.

## Critical Rule: VAT Validity

**IMPORTANT**: Only customers with **valid EU VAT numbers** can be included in the ICP report.

If a customer has an invalid or missing VAT number:
- Their turnover is **excluded from Box 3B** (and ICP)
- Their turnover is **reclassified to Box 1E** (0% export services)

This ensures **Box 3B total always equals the ICP report total**.

### VAT Validity Source
- File: `data/*_invoicees_overview.csv`
- Key field: `valid_eu_vat_number` (boolean: true/false)
- Lookup by: `exact_account_code` matching transaction `account_code`

### Accounts Not in Lookup
If an account is not found in the invoicees lookup:
- Treat as **invalid VAT** (conservative default)
- Reclassify their 3B turnover to 1E
- Log in `invalid_vat_old_*.csv` for review

## Reference Sample
`docs/samples/C Teleport BV - ICP Q3 2025 input file.xlsx`

## Column Layout

| Column | Description | Source |
|--------|-------------|--------|
| **Code** | Counterparty/account code | `account_code` (trimmed) from transactions |
| **Name** | Company name | From invoicees/counterparty data |
| **Amount** | Sum of transaction amounts (default currency) | Sum of `amount_dc` for that counterparty |
| **Round** | Rounded amount (integer) | `round(Amount)` for declaration |
| **Vat number** | Customer VAT number (EU) | From invoicees; use "n/a" if missing |
| **Country** | Customer country | From counterparty; prefer full name |

## Row Scope

### Include
Only transactions where **derived VAT code** has **ICP = TRUE** in `data/vat_code_box_icp_lookup.csv`.

In the standard scheme, this is **NFT-EU-RC** (Box 3B, EU B2B reverse charge).

### Exclude
- Domestic (NL) transactions
- Non-EU transactions
- Non-RC (reverse charge) transactions
- Purchases (Box 4B)

### Aggregation
- One row per distinct counterparty (account code)
- Sum `amount_dc` over all ICP-in-scope lines for that counterparty

## Sort Order
Sort by:
1. **Country** (alphabetically)
2. **Name** or **Code** (within each country)

## Validation
**Box 3B total** (from VAT report) must equal **sum of Amount** (or sum of Round) in the ICP report.

## Output
- File: `tmp/icp_report_pivot.csv`
- Amounts in default currency (EUR)
- Sign follows transaction data (often negative for revenue in Exact)
