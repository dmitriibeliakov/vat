## Key Business Rules Summary for assigning VAT codes to transactions

> **Note:** The VAT codes shown below are the current numeric codes configured in Exact Online (e.g. 2, 6, 8, 20, 95, 100, 101, 102). These will be replaced by three-character alphanumeric codes (e.g. FLN, NFE, PAN) as defined in [exact_vat_codes.md](exact_vat_codes.md).

### Revenue Transactions (GL 8xxx)

| Customer Location | Margin Account | VAT Code in Exact Online | Return Box |
| ----------------- | -------------- | -------- | ---------- |
| NL                | Yes            | 2 or 20  | 1A or 1E   |
| NL                | No             | 20       | Nothing    |
| EU                | Yes            | 8        | 3B (→ ICP) |
| EU                | No             | 8        | Nothing    |
| Non-EU            | Yes            | 6        | Nothing    |
| Non-EU            | No             | 6        | Nothing    |

### Purchase Transactions (GL 4xxx, 7xxx)

| Supplier Location | VAT Code in Exact Online | Return Box |
| ----------------- | -------- | ---------- |
| NL                | 3 or 4   | 5B         |
| EU                | 10       | 4B/5B      |
| Non-EU            | 12       | 4A/5B      |
