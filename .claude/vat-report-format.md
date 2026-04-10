# VAT Report Format and Design

## Overview
The VAT report is a **pivot table** of `tmp/transactions_with_vat_code.csv`, aggregating transaction amounts by Dutch VAT box.

## Source Files
| File | Purpose |
|------|---------|
| `docs/scheme/vat_code_scheme_temporary.md` | VAT code scheme definition |
| `data/vat_code_box_icp_lookup.csv` | VAT code to Box/ICP mapping |
| `tmp/transactions_with_vat_code.csv` | Input transactions with derived codes |

## Lookup CSV Structure: `data/vat_code_box_icp_lookup.csv`

| Column | Description |
|--------|-------------|
| **Vat code** | Full VAT code (e.g., FLT-NL-0, NFT-EU-RC, PUR-EU-RC) |
| **VAT box** | Dutch return box (1A, 1E, 3B, 4A, 4B, 5B). Empty = not reported |
| **ICP** | TRUE if belongs in ICP report (Box 3B breakdown) |

### Multi-Box Codes
Some codes map to multiple boxes via multiple rows in the lookup:
- Example: `PUR-EU-RC` maps to both 4B and 5B

## Processing Pipeline

### Input
- File: `tmp/transactions_with_vat_code.csv`
- Key columns: `derived_vat_code`, `amount_dc_numeric`
- Note: Original `vat_code` from source is preserved, never overwritten

### Box Assignment
1. Look up **VAT box** from the lookup using `derived_vat_code`
2. Codes with no box (empty in lookup) are **excluded**
3. Codes with multiple boxes contribute the amount to **each** box

### VAT Pivot Output
- File: `tmp/vat_report_pivot.csv`
- Columns: **Box**, **Sum_amount**, **transaction_count**
- Aggregation: Group by Box, sum amounts

### ICP Pivot Output
- File: `tmp/icp_report_pivot.csv`
- Filter: Only rows where lookup **ICP = TRUE**
- See [ICP Report Format](icp-report-format.md) for details

## Validation: Box 3B = ICP Total
- **Box 3B total** from `tmp/vat_report_pivot.csv`
- **ICP sum** from `tmp/icp_report_pivot.csv` (Amount column)
- These must be equal (both derived from ICP=TRUE codes)
