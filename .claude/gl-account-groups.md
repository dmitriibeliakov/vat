# GL Account Groups from CSVs

## Source Files
| File | Contents | Origin |
|------|----------|--------|
| `data/Acount ledger.csv` | Complete GL accounts list (Code, DescriptionDescription) | Exact Online export |
| `data/GL accounts classification.csv` | Tree-like grouping (Code, ClassificationDescription) | Exact Online export |

Both are raw exports from Exact Online via `Master data` → `Import/Export`.

## Filtering by GL Group (e.g., "Revenue")

When filtering transactions by a GL group name:

### Step 1: Locate the Group
1. Open `GL accounts classification.csv`
2. Search `ClassificationDescription` column for the group name (case-insensitive, partial match OK)
3. Take the matching row's `Code` as the **base group code**

### Step 2: Collect Child GL Codes
1. Treat the classification file as a hierarchy/tree
2. Starting from the base group code, collect all **children and descendants**
3. Keep each descendant's `Code` value
4. Result: set of GL codes belonging to the requested group

### Step 3: Validate Against Ledger
1. Open `Acount ledger.csv`
2. Use `Code` column as the canonical list of actual GL accounts
3. **Intersect** the codes from Step 2 with the ledger codes
4. Result: final set of valid GL account codes

### Step 4: Filter Transactions
1. User provides a transactions CSV
2. Identify the GL account code column (should match `Acount ledger.csv` codes)
3. Filter to rows where GL account code is in the final set from Step 3

## Constraints
- Never connect directly to Exact Online, Redshift, or any database
- Only operate on user-provided CSV files plus local ledger/classification CSVs
