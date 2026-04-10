# Exact Online VAT Codes — Double Accounting Scheme

*3-character codes for Exact Online, with dual-rate accounting*

---

## Complete VAT Code Table

| Code | Category     | Explanation                         | Rate in Exact | Rate to tax authorities |
|:-----|:-------------|:------------------------------------|:--------------|:-------------------|
| FLN  | Margin       | Flight margin – NL                  | 0%            | 0% (Box 1E)       |
| FLE  | Margin       | Flight margin – EU valid VAT        | 0%            | 0% (Box 1E)       |
| FLX  | Margin       | Flight margin – EU no valid VAT     | 0%            | 0% (Box 1E)       |
| FLW  | Margin       | Flight margin – non-EU              | 0%            | OOS                |
| NFN  | Margin       | Non-flight margin – NL              | 21%           | 21% (Box 1A)      |
| PHN | Hotel (base and margin) | Hotel booking - NL (special case) | 9% | OOS |
| NFE  | Margin       | Non-flight margin – EU valid VAT    | RC            | RC (Box 3B / ICP) |
| NFX  | Margin       | Non-flight margin – EU no valid VAT | RC            | 0% (Box 1E)       |
| NFW  | Margin       | Non-flight margin – non-EU          | OOS           | OOS                |
| FXE  | Margin       | FX markup – exempt                  | EXM           | EXM                |
| PAN  | Pass-through | Pass-through – NL                   | 21%           | OOS                |
| PAE  | Pass-through | Pass-through – EU valid VAT         | RC            | OOS                |
| PAX  | Pass-through | Pass-through – EU no valid VAT      | 21%           | OOS                |
| PAW  | Pass-through | Pass-through – non-EU               | OOS           | OOS                |
| REF  | Other        | Tax refund                          | OOS           | OOS                |
| PUN  | Purchases    | Purchases – NL                      | 21%           | 21% (Box 5B)      |
| PUE  | Purchases    | Purchases – EU                      | RC            | RC (Box 4B + 5B)  |
| PUW  | Purchases    | Purchases – non-EU                  | RC            | RC (Box 4A + 5B)  |

---

## Rationale

### Why double accounting?

Exact Online stores a single tax rate per VAT code, but the business needs two different rates for the same transaction line:

1. **Customer Rate** — the VAT percentage shown on the invoice to the customer
2. **Tax Authority Rate** — the VAT treatment reported on the Dutch VAT return

For margin codes (FLx, NFx, FXE) and purchase codes (PUx), both rates are identical — the customer is charged what we owe to the tax authorities. No special handling needed.

The divergence arises on **pass-through** amounts (ticket prices, COGS, CC fees). These are paid on behalf of the customer and carry no margin, so legally they are out of scope for VAT. However, showing 0% or OOS on one invoice line and 21% on another (for the markup) creates confusing invoices and customer disputes. The solution: configure pass-through codes in Exact with the customer-facing rate, while the VAT return logic treats them as OOS.

### Pass-through mirrors margin

Each pass-through geography variant mirrors the customer rate of its corresponding non-flight margin code:

| Geography          | Margin code | Pass-through code | Shared customer rate |
|:-------------------|:------------|:-------------------|:---------------------|
| NL                 | NFN (21%)   | PAN (21%)          | 21%                  |
| EU valid VAT       | NFE (RC)    | PAE (RC)           | RC                   |
| EU no valid VAT    | NFX (RC)    | PAX (21%)          | 21%                  |
| Non-EU             | NFW (OOS)   | PAW (OOS)          | OOS                  |

**PAX gets 21%, not RC**: when the EU customer has no valid VAT number, they cannot self-account via reverse charge. They are invoiced with 21% Dutch VAT, same as a domestic customer.

### 3-character code design

Exact Online supports a maximum of 3 characters for VAT codes. The naming convention:

- **Characters 1–2**: Category (`FL` = flight, `NF` = non-flight, `FX` = FX/exempt, `PA` = pass-through, `RE` = refund, `PU` = purchase)
- **Character 3**: Geography (`N` = NL, `E` = EU valid VAT, `X` = EU no valid VAT, `W` = non-EU/world)

Exception: `FXE` uses `E` for "exempt" since FX has no geography dimension.

### Worked example: baggage to a Dutch customer

Baggage sold for €35 (€25 pass-through + €10 markup):

| Line item      | Code | Amount | Customer VAT (21%) | Tax return        |
|:---------------|:-----|-------:|--------------------:|:------------------|
| Baggage price  | PAN  |    €25 |              €5.25 | OOS — not reported|
| Baggage markup | NFN  |    €10 |              €2.10 | 21% → Box 1A     |
| **Total**      |      | **€35**|           **€7.35**|                   |

The customer sees a consistent 21% across both lines. Only the €2.10 markup VAT is reported to the tax authorities.
