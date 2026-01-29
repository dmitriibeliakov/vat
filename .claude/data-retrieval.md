# Retrieving VAT Transaction Data

## Source System
- **Application**: Exact Online (accounting)
- **Warehouse**: Redshift
- **Table**: `"mongo_cteleport_exact_service"."transaction_lines"`

## Data Access Constraint
**Never connect directly** to Exact Online, Redshift, or any database.

Instead:
1. Explain **how** to retrieve the data
2. Propose/adapt an appropriate **SQL query** for the user to run

## Reporting Period
- VAT reports are **quarterly** (not monthly)
- Filter using `financial_year` and `financial_period`

### Quarter to Month Mapping
| Quarter | financial_period values |
|---------|------------------------|
| Q1 | 1, 2, 3 |
| Q2 | 4, 5, 6 |
| Q3 | 7, 8, 9 |
| Q4 | 10, 11, 12 |

## SQL Query Patterns

### Basic Quarter Query
```sql
SELECT *
FROM "mongo_cteleport_exact_service"."transaction_lines"
WHERE "financial_year" = 2025
  AND "financial_period" IN (10, 11, 12);  -- Q4
```

### Template for Any Quarter
```sql
SELECT *
FROM "mongo_cteleport_exact_service"."transaction_lines"
WHERE "financial_year" = {year}
  AND "financial_period" IN ({month1}, {month2}, {month3});
```

## Best Practices
- Always filter by both `financial_year` and `financial_period`
- Default to quarter-based filters when user mentions a VAT quarter and year
- Export results as CSV for processing in this workspace
