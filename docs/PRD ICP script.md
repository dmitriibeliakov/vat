# PRD: ICP Report Script (main_old.py Enhancement)

## Overview

Enhance `app/main_old.py` to generate the **ICP Report** (Intra-Community Supply / Opgaaf ICP) and properly handle **VAT number validity** before creating the VAT pivot. The ICP report is a breakdown of Box 3B (EU B2B sales) by customer, required for Dutch tax filing.

## Key Insight

**Critical rule**: If an EU customer does not have a valid VAT number, their turnover cannot be reported as Box 3B (ICP). Instead, it must be treated as Box 1E (0% VAT export services). This affects both the ICP report and the VAT declaration totals.

## Current State

`main_old.py` currently:
1. Reads transaction CSV
2. Assigns Margin and Box columns
3. Creates VAT pivot
4. Outputs a basic ICP grouped by counterparty

**Missing**: VAT validity check before box assignment, which can cause:
- Incorrect Box 3B totals (includes customers without valid EU VAT)
- ICP report with invalid entries
- Box 1E totals that are too low

## Goal

1. **Pre-validate** VAT numbers before box assignment
2. **Reclassify** EU B2B sales to Box 1E when customer VAT is invalid
3. **Generate ICP report** containing only valid VAT customers
4. Ensure **Box 3B total = ICP total** (validation check)

## Input Data

### Transaction CSV
Same as existing PRD, with key columns:
- `account_code` - Counterparty code (links to invoicees)
- `account_name` - Counterparty name
- `vat_code` - Original Exact VAT code (8, 101 for EU B2B)
- `amount_dc` - Transaction amount

### VAT Validity Lookup
| File | Purpose |
|------|---------|
| `data/*_invoicees_overview.csv` | Source of VAT validity |

**Key columns in invoicees_overview.csv**:
| Column | Description |
|--------|-------------|
| `exact_account_code` | Links to `account_code` in transactions |
| `name` | Company name |
| `country` | Full country name |
| `country_code` | 2-letter ISO code |
| `vat_number` | Customer's VAT number |
| `valid_eu_vat_number` | **TRUE/FALSE** - key validity flag |

### Country Mapping
| File | Purpose |
|------|---------|
| `data/Counterparty country.csv` | Country code to full name (for ICP sorting) |

## Processing Logic

### Step 0: Load VAT Validity Data (NEW)

```
1. Load invoicees_overview.csv
2. Create lookup: account_code → valid_eu_vat_number, vat_number, country
3. Match by trimmed exact_account_code
```

### Step 1: Enrich Transactions with VAT Validity

For each transaction:
```
IF account_code exists in invoicees lookup:
    vat_valid = invoicees[account_code].valid_eu_vat_number
    vat_number = invoicees[account_code].vat_number
    country = invoicees[account_code].country
ELSE:
    vat_valid = FALSE  (conservative default)
    vat_number = "n/a"
    country = "Unknown"
```

### Step 2: Adjust Box Assignment (MODIFIED)

Original Box 3B assignment (VAT codes 8, 101 with Margin):
```
IF original_box == "3B" AND vat_valid == FALSE:
    adjusted_box = "1E"  # Reclassify to 0% export
ELSE:
    adjusted_box = original_box  # Keep as-is
```

**Affected VAT codes**:
- **8** (Ticket Sales within EU) - reclassify invalid to 1E
- **101** (Commission EU) - reclassify invalid to 1E

### Step 3: Generate ICP Report

Filter and aggregate transactions for ICP:
```
ICP transactions = WHERE:
    - original_box == "3B"
    - vat_valid == TRUE
    - GL account starts with "8" (revenue accounts)
```

Group by `account_code`:
```
ICP_row = {
    Code: account_code (trimmed integer),
    Name: account_name,
    Amount: SUM(amount_dc),
    Round: ROUND(Amount, 0),
    Vat number: vat_number from lookup,
    Country: country from lookup
}
```

### Step 4: Continue with VAT Pivot and Declaration

Use `adjusted_box` (not `original_box`) for:
- VAT pivot grouping
- VAT declaration totals

## Output Files

### 1. ICP Report: `tmp/icp_old_{input_stem}.csv`

| Column | Description | Example |
|--------|-------------|---------|
| Code | Account code (integer) | 2358 |
| Name | Company name | AXIS Aviation Austria GmbH |
| Amount | Sum of transactions | -195.21 |
| Round | Rounded amount | -195 |
| Vat number | EU VAT number | ATU78323306 |
| Country | Full country name | Austria |

**Sort order**: Country (alphabetically), then Name within country.

**Sign convention**: Revenue is negative in Exact Online.

### 2. VAT Pivot: `tmp/vat_pivot_old_{input_stem}.csv`

Same as existing PRD, but Box column uses `adjusted_box`:
- Box 3B contains only valid VAT transactions
- Box 1E contains reclassified invalid VAT transactions

### 3. VAT Declaration: `tmp/vat_declaration_old_{input_stem}.csv`

Same as existing PRD, with corrected totals.

### 4. Invalid VAT Report (NEW): `tmp/invalid_vat_old_{input_stem}.csv`

List of transactions reclassified from 3B to 1E for audit:
| Column | Description |
|--------|-------------|
| account_code | Customer code |
| account_name | Customer name |
| vat_number | Invalid/missing VAT number |
| country | Customer country |
| amount_sum | Total reclassified amount |
| original_box | Was 3B |
| adjusted_box | Now 1E |

## Validation Rules

### Rule 1: ICP = Box 3B
```
ABS(sum(ICP.Round)) == ABS(VAT_declaration.Box_3B_Turnover)
```

### Rule 2: No Invalid VAT in ICP
```
FOR each row in ICP:
    ASSERT vat_number is not empty/n/a
    ASSERT valid_eu_vat_number == TRUE (from lookup)
```

### Rule 3: Reclassified Amount Check
```
sum(invalid_vat_report.amount_sum) ==
    (Box_3B_original - Box_3B_adjusted)
```

## ICP Report Format Reference

Based on `docs/samples/C Teleport BV - ICP Q3 2025 input file.xlsx`:

```
Code    Name                              Amount      Round           Vat number      Country
2358    AXIS Aviation Austria GmbH        -195.21     =ROUND(C2,0)    ATU78323306     Austria
2419    Bairline Fluggesellschaft mbH     -40.38      =ROUND(C3,0)    ATU66132909     Austria
2534    JetView GmbH                      -1702.03    =ROUND(C4,0)    ATU78020035     Austria
...
```

The Excel file uses formula `=ROUND(Cn,0)` for the Round column. In CSV output, calculate the actual rounded value.

## Processing Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Raw Transaction CSV                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 0: Load VAT Validity Lookup (invoicees_overview.csv)      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 1: Enrich transactions with vat_valid, vat_number, country│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 2: Calculate original_box (Margin + VAT code logic)       │
│          Then calculate adjusted_box (reclassify if invalid)    │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│   ICP Report     │ │  Invalid VAT     │ │   VAT Pivot      │
│  (valid 3B only) │ │    Report        │ │ (adjusted_box)   │
└──────────────────┘ └──────────────────┘ └──────────────────┘
                              │
                              ▼
                   ┌──────────────────┐
                   │ VAT Declaration  │
                   │ (from adjusted)  │
                   └──────────────────┘
```

## Usage

```bash
python -m app.main_old transaction_lines_Q3_2025.csv \
    --invoicees data/20260129_invoicees_overview.csv \
    --tmp-dir tmp
```

## EU Countries for ICP

ICP only applies to EU member states. The following country codes qualify:
```
AT, BE, BG, HR, CY, CZ, DK, EE, FI, FR, DE, GR, HU, IE,
IT, LV, LT, LU, MT, NL, PL, PT, RO, SK, SI, ES, SE
```

Note: NL (Netherlands) is excluded from ICP as it's the domestic country.

## Edge Cases

### 1. Missing Account in Lookup
If `account_code` not found in invoicees_overview.csv:
- Treat as invalid VAT
- Log warning for review

### 2. Empty VAT Number
If `vat_number` is empty, "n/a", or "null":
- `valid_eu_vat_number` should be FALSE
- Reclassify to 1E

### 3. Non-EU Countries in Box 3B
Should not happen (VAT code 8 is EU-specific), but if found:
- Log as data quality issue
- Keep in 3B if VAT appears valid

### 4. Credit Notes (Positive Amounts)
Some ICP entries may be positive (refunds/credits). Include them in ICP report as-is with their sign.

## Dependencies

- pandas
- Lookup files:
  - `data/*_invoicees_overview.csv` (VAT validity)
  - `data/gl_margin_lookup.csv` (Margin assignment)
  - `data/Counterparty country.csv` (Country names)

## Applicability

This enhancement applies to **2025 and earlier** quarterly data only. For 2026+, the new VAT code scheme (`app/main.py`) handles VAT validity through derived codes.
