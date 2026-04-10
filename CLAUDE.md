# VAT Reporting Project Instructions

This project handles VAT (Value Added Tax) reporting for C Teleport BV, processing transaction data from Exact Online and generating Dutch VAT returns and ICP reports.

## Core Constraints

### Data Access
- **Never connect directly** to Exact Online, Redshift, or any other database
- Instead, explain to the user **how** to retrieve data and propose appropriate SQL queries for them to run
- Only operate on **user-provided CSV files** plus the local reference files in this workspace

### Large File Handling
- Transaction files (e.g., `*_transaction_lines_*.csv`) are often 100+ MB
- **Do not** load entire large files into memory with generic read tools
- Use streaming, chunking, or data tools designed for large datasets
- When only part of the data is needed, apply filters rather than scanning the whole file

## Data Sources

### Transaction Data
- **Source system**: Exact Online (accounting)
- **Warehouse table**: `"mongo_cteleport_exact_service"."transaction_lines"` in Redshift
- **Reporting frequency**: Quarterly (not monthly)

### Quarter to Month Mapping
For `financial_period` filtering:
- Q1: months 1, 2, 3
- Q2: months 4, 5, 6
- Q3: months 7, 8, 9
- Q4: months 10, 11, 12

### Reference Files in this Project
| File | Purpose |
|------|---------|
| `data/Acount ledger.csv` | GL accounts list (Code, DescriptionDescription) |
| `data/GL accounts classification.csv` | GL account hierarchy (Code, ClassificationDescription) |
| `data/vat_code_box_icp_lookup.csv` | VAT code to Box/ICP mapping |
| `data/*_invoicees_overview.csv` | Customer VAT validity lookup |
| `data/gl_margin_lookup.csv` | GL code to Margin mapping |
| `docs/scheme/vat_code_scheme_temporary.md` | VAT code algorithm (source of truth) |

## Critical Business Rules

### One GL Account = One VAT Code
- Each GL account must map to **exactly one VAT code** — never mix multiple VAT codes on a single GL account
- This is fundamental: GL accounts are the primary input for determining the VAT code (Category), so a 1:1 mapping must be maintained
- If any proposed change would result in one GL account mapping to multiple VAT codes, **stop and notify the user** before proceeding

### ICP and VAT Validity
- **Only customers with valid EU VAT numbers** qualify for ICP (Box 3B)
- If VAT is invalid or missing: reclassify from Box 3B → Box 1E
- **Box 3B total must equal ICP report total** (validation check)
- VAT validity source: `valid_eu_vat_number` field in invoicees_overview.csv
- Accounts not found in lookup are treated as invalid (conservative default)

## Key Documentation

- [VAT Code Scheme](.claude/vat-code-scheme.md) - VAT code logic and tax treatment algorithm
- [VAT Report Format](.claude/vat-report-format.md) - Dutch VAT return structure
- [ICP Report Format](.claude/icp-report-format.md) - Intra-Community Supply report
- [GL Account Groups](.claude/gl-account-groups.md) - How to filter by GL groups
- [Data Retrieval](.claude/data-retrieval.md) - SQL patterns for transaction data
