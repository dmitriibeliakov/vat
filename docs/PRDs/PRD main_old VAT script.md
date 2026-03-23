# PRD: Legacy VAT Script Enhancement (main_old.py)

## Overview

Enhance `app/main_old.py` to automatically assign **Margin** and **Box** columns based on the logic documented in `docs/OLD_VAT_Margin_Box_Logic.md`. This script processes 2025 and earlier quarterly VAT raw transaction lines CSV using original Exact Online VAT codes.

## Current State

`main_old.py` currently:
1. Reads transaction CSV from Exact Online
2. Filters out blank/0/"No VAT" codes
3. Creates pivot with VAT code, GL, Amount grouped
4. Outputs with **empty** Box and Margin columns for manual filling

## Goal

Automate the Box and Margin assignment so the output is ready for VAT declaration without manual column population.

## Input Data

### Transaction CSV (from Exact Online)
Required columns:
- `vat_code` - Original Exact VAT code (2, 3, 4, 6, 8, 10, 12, 20, 95, 100, 101, 102)
- `vat_code_description` - VAT code name
- `gl_account_code` - GL account number
- `gl_account_description` - GL account name
- `amount_dc` - Transaction amount
- `account_code` - Counterparty code
- `account_name` - Counterparty name

### Lookup Files
| File | Purpose |
|------|---------|
| `data/gl_margin_lookup.csv` | GL code → Margin value (Margin / No Margin) |
| `data/vat_box_lookup_old.csv` | VAT code + Margin + GL prefix → Box (to be created) |
| `data/*_invoicees_overview.csv` | Counterparty VAT numbers for ICP |
| `data/Coutnerparty country.csv` | Country code → full name mapping |

## Logic

### Step 1: Margin Assignment (GL-based)

Margin is determined **100% by GL account**:

```
IF gl_code IN gl_margin_lookup → use lookup value
ELSE IF gl_code starts with "4" → blank (cost account)
ELSE IF gl_code starts with "1" → blank (balance sheet)
ELSE → blank
```

### Step 2: Box Assignment (VAT code + Margin + GL type)

Box depends on VAT code, Margin value, and GL account type:

#### Sales VAT Codes
| VAT Code | Margin | GL Type | Box |
|----------|--------|---------|-----|
| 2 | Margin | any | 1A |
| 2 | blank/No Margin | any | (none) |
| 6 | any | any | (none) |
| 8 | Margin | any | 3B |
| 8 | No Margin | any | (none) |
| 20 | Margin | 8xxx | 1E |
| 20 | No Margin | any | (none) |
| 95 | Margin | any | 1A |
| 95 | No Margin | any | (none) |
| 100 | Margin | any | 1A |
| 101 | Margin | any | 3B |
| 102 | any | any | (none) |

#### Purchase VAT Codes
| VAT Code | GL Type | Box |
|----------|---------|-----|
| 3 | 4xxx/7xxx | 5B |
| 3 | 1xxx | (none) |
| 4 | 4xxx/7xxx | 5B |
| 4 | 1xxx | (none) |
| 10 | 4xxx/7xxx | 4B, 5B |
| 10 | 1xxx | (none) |
| 12 | 4xxx/7xxx | 4A, 5B |
| 12 | 1xxx | (none) |

## Output

### Primary Output: `tmp/vat_pivot_old_{input_stem}.csv`

Columns:
| Column | Description |
|--------|-------------|
| VAT_code | Original Exact VAT code |
| VAT_description | VAT code description |
| GL_code | GL account code |
| GL_description | GL account description |
| Margin | Margin / No Margin / blank |
| Box | 1A, 1E, 3B, 4A, 4B, 5B, or blank |
| Amount_sum | Sum of amount_dc |
| Transaction_count | Number of transactions |

### Secondary Output: `tmp/vat_declaration_old_{input_stem}.csv`

Aggregated by Box for VAT declaration:
| Column | Description |
|--------|-------------|
| Box | VAT return box (1A, 1E, 3B, 4A, 4B, 5B) |
| Turnover | Sum of amounts (rounded to whole euros) |
| VAT_amount | Calculated VAT where applicable |

### ICP Output: `tmp/icp_old_{input_stem}.csv`

For Box 3B transactions (EU B2B sales), grouped by counterparty:

| Column | Description | Source |
|--------|-------------|--------|
| Code | Counterparty/account code | `account_code` from transactions |
| Name | Company name | `account_name` from transactions |
| Amount | Sum of 3B transaction amounts | Sum of `amount_dc` |
| Round | Rounded amount (integer) | `round(Amount)` for declaration |
| Vat number | Customer EU VAT number | From invoicees lookup; "n/a" if missing |
| Country | Customer country (full name) | From counterparty country lookup |

**Sort order:** Country (alphabetically), then Name within each country.

**Validation:** Box 3B total from VAT pivot must equal sum of Round in ICP report.

## Exclusions

The following are excluded from VAT return (Box = blank):
- Balance sheet accounts (GL starting with 1)
- Transactions with blank/0/"No VAT" VAT codes
- Pass-through turnover (No Margin on sales codes)
- Outside EU sales (VAT code 6, 102)

## Usage

```bash
python -m app.main_old transaction_lines_Q3_2025.csv --tmp-dir tmp
```

## Validation

Compare output against historical Q1/Q2/Q3 2025 declarations in `docs/samples/` to verify Box and Margin assignments match previous manual work.

## Dependencies

- pandas
- Lookup files in `data/` directory

## Applicability

This script applies to **2025 and earlier** quarterly data only. For 2026+, use `app/main.py` with the new derived VAT code scheme.
