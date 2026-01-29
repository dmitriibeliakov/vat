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
| `docs/vat_code_scheme.md` | VAT code algorithm (source of truth) |

## Key Documentation

- [VAT Code Scheme](.claude/vat-code-scheme.md) - VAT code logic and tax treatment algorithm
- [VAT Report Format](.claude/vat-report-format.md) - Dutch VAT return structure
- [ICP Report Format](.claude/icp-report-format.md) - Intra-Community Supply report
- [GL Account Groups](.claude/gl-account-groups.md) - How to filter by GL groups
- [Data Retrieval](.claude/data-retrieval.md) - SQL patterns for transaction data
