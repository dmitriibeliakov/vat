# OLD VAT Filing Algorithm - Explanation for Financial Controller

**Purpose:** This document explains how the OLD VAT filing system (used for 2025 and earlier) automatically processes transaction data and assigns VAT reporting classifications.

**Audience:** Financial Controller reviewing for compliance and correctness.

---

## Overview

The OLD VAT filing system processes quarterly transaction data and automatically determines:
1. **Margin classification** - whether revenue includes a markup/commission (Margin) or is pass-through (No Margin)
2. **Box assignment** - which line of the Dutch VAT return each transaction belongs to
3. **ICP reporting** - which EU B2B transactions must be reported in the Intra-Community supply list

---

## 1. Algorithm Processing Steps
1. **Filter** - Exclude transactions with blank, zero, or "No VAT" codes
2. **Assign Margin** - Determine if the transaction represents margin business (see section 2)
3. **Assign Box** - Determine VAT return box based on tax treatment (see section 3)
4. **Validate VAT** - Check if EU customers have valid VAT numbers (see section 4)
5. **Generate Reports** - Create VAT return summary and ICP report

---

## 2. Margin Classification Logic

### What is "Margin"?
- **Margin** = Revenue where C Teleport earns a commission, markup, or service fee
- **No Margin** = Pass-through turnover where C Teleport acts as intermediary without markup
- **Blank** = Cost accounts and balance sheet items (not revenue)

### How it's Determined
Margin classification is **100% based on GL account**, not VAT code.

#### GL Accounts Classified as "Margin":
- 7212: Consolidator fees costs
- 7221: Mark up on compensation of Intercompany expenses
- 80xx series: SaaS fees, airline/GDS incentives, platform fees, booking fees
- 81xx series: All markup accounts (Marine, Corporate, FX, Class drops, GDS incentive compensation, Consolidator markup)
- 82xx series: All markup on ancillary services (mark-ups, FX markups, commissions for NL/EU/outside EU Corporate services)

#### GL Accounts Classified as "No Margin":
- 7211: Cost of Goods Turnover (0%)
- 721xx: COGS IATA accounts (EMDA, EMDS, RFND, TKTT)
- 8102-8103: Pure ticket turnover (Marine/Corporate)
- 8115: Hotel turnover
- 82xx: Pure ancillary services turnover (without the word "markup")

#### GL Accounts with Blank Margin:
- All 4xxx accounts (personnel costs, subscriptions, office costs)
- All 1xxx accounts (balance sheet: assets, liabilities)

### Business Logic
This distinction is critical because:
- Only **margin business** is taxable in most cases
- Pass-through amounts (No Margin) are typically not included in VAT return
- This reflects the actual economic substance of each transaction type

---

## 3. Box Assignment Logic

"Box" refers to the specific line on the Dutch VAT return (BTW-aangifte) where the transaction should be reported.

### Box Meanings
- **1A** = Domestic sales/services taxed at standard rate (21%)
- **1E** = Domestic sales/services taxed at 0% (exports, international transport)
- **3B** = EU B2B supplies (ICP - reported to other EU countries)
- **4A** = Services purchased from outside EU (reverse charge)
- **4B** = Goods purchased from within EU (reverse charge)
- **5B** = Input VAT to be deducted

### Assignment Rules

#### VAT Code to Box Assignment Table

| VAT Code(s)            | Description                         | Condition                                                                                   | Assigned Box                | Notes                                                        |
|------------------------|-------------------------------------|---------------------------------------------------------------------------------------------|-----------------------------|--------------------------------------------------------------|
| 2                      | 21% NL sales                        | If Margin                                                                                   | 1A                          |                                                              |
| 2                      | 21% NL sales                        | Otherwise                                                                                   | Not reportable              |                                                              |
| 6                      | Sales outside EU                    | Always                                                                                      | Not reportable              | Outside Dutch VAT scope                                      |
| 8                      | Sales within EU                     | If Margin                                                                                   | 3B                          | Subject to VAT validity check (see section 4)                |
| 8                      | Sales within EU                     | If No Margin                                                                                | Not reportable              |                                                              |
| 20                     | 0% NL sales                         | If Margin AND GL is 7xxx or 8xxx                                                            | 1E                          |                                                              |
| 20                     | 0% NL sales                         | Otherwise                                                                                   | Not reportable              |                                                              |
| 95                     | Ancillary services NL               | If Margin                                                                                   | 1A                          |                                                              |
| 95                     | Ancillary services NL               | Otherwise                                                                                   | Not reportable              |                                                              |
| 100                    | Commission 21%                      | If Margin                                                                                   | 1A                          |                                                              |
| 101                    | Commission EU                       | If Margin                                                                                   | 3B                          | Subject to VAT validity check                                |
| 102                    | Commission Non-EU                   | Always                                                                                      | Not reportable              |                                                              |
| 3, 4                   | NL VAT 9% (3) or 21% (4)            | If vat_type = "I"                                                                           | 5B                          | Deductible input VAT                                         |
| 3, 4                   | NL VAT 9% (3) or 21% (4)            | Otherwise                                                                                   | Not reportable              |                                                              |
| 10                     | Purchases EU 21%                    | If vat_type = "I" AND GL is cost/asset (4xxx, 7xxx, or fixed assets 150/160)                | 4B + 5B                     |                                                              |
| 10                     | Purchases EU 21%                    | Otherwise                                                                                   | Not reportable              |                                                              |
| 12                     | Purchases outside EU                | If vat_type = "I" AND GL is cost/asset (4xxx, 7xxx, or fixed assets 150/160)                | 4A + 5B                     |                                                              |
| 12                     | Purchases outside EU                | Otherwise                                                                                   | Not reportable              |                                                              |

**Notes:**
- The system also checks the `vat_type` field for purchase VAT codes:
    - `vat_type = "I"` means Input/Purchase (actual cost, VAT is deductible)
    - `vat_type = "O"` or `"P"` means Offset/Accrual (excluded from VAT return)
- VAT codes 3 and 4 apply to input VAT only if `vat_type` is "I"
- "Margin" and "No Margin" are determined by GL account (see previous section)

### Why Balance Sheet is Excluded
Transactions on balance sheet GL accounts (1xxx series, except fixed assets such as 150 and 160) are **not included** in the VAT return because they represent balance sheet movements (receivables, payables, equity) rather than taxable supplies or deductible costs.  
**Note:** The list of fixed asset GLs (such as 150 and 160) is not exhaustive and may need to be expanded to include any additional relevant GL accounts based on the organization’s chart of accounts.

---

## 4. EU VAT Validity Check (ICP Qualification)

### The Issue
Not all EU sales qualify for Box 3B (ICP). The customer must have a **valid EU VAT number** to receive supplies tax-free under the reverse charge mechanism.

### Validation Process
For every transaction assigned to Box 3B:
1. Look up the customer's VAT number in the invoicees overview file
2. Check the `valid_eu_vat_number` field (True/False)
3. Also verify the customer country is actually in the EU

### Reclassification Rule
If a transaction is initially assigned Box 3B but the customer has:
- **Invalid VAT number**, OR
- **Missing/unknown VAT number**, OR
- **Country is not EU**

Then it is **reclassified to Box 1E** (0% domestic export services).

### Why This Matters
- Box 3B amounts must be reported in the ICP (Intra-Community supply report)
- If a customer's VAT is invalid, they cannot receive reverse-charge treatment
- The supply must instead be treated as a 0% export (Box 1E)
- **Critical validation**: Box 3B total must exactly equal the ICP report total

---

## 5. Outputs Generated

### VAT Pivot Report
Detailed breakdown showing:
- Each combination of VAT code, GL account, Margin, and Box
- Amount sum and transaction count for each combination
- Used for detailed analysis and audit trail

### VAT Declaration Summary
Aggregated totals by Box:
- Box 1A, 1E, 3B, 4A, 4B, 5B
- Turnover amounts (rounded to whole euros)
- Calculated VAT amounts where applicable (21% for boxes 1A, 4A, 4B, 5B)
- This is what gets filed with the tax authorities

### ICP Report
For Box 3B transactions only, grouped by customer:
- Customer account code and name
- Total amount supplied to that customer
- Customer's EU VAT number
- Customer's country
- Sorted by country, then alphabetically by name

### Invalid VAT Report (audit)
Lists all transactions that were reclassified from 3B to 1E:
- Customer name and account code
- VAT number on file (if any)
- Country
- Amount reclassified
- For audit purposes to review data quality issues

---

## 6. Key Compliance Considerations

### Margin Business Recognition
- The GL-based margin classification must accurately reflect economic reality
- "Margin" should only apply to accounts where C Teleport earns a spread/commission
- Pass-through amounts should not be taxed

### ICP Reporting Accuracy
- Only customers with verified valid EU VAT numbers appear in ICP
- Box 3B and ICP totals must match (critical reconciliation)
- Invalid VAT numbers trigger reclassification to prevent incorrect reverse charge

### Completeness
- All non-zero, non-blank VAT code transactions are processed
- Balance sheet movements correctly excluded
- Offset/accrual entries (vat_type "O"/"P") correctly excluded from return

### Data Quality Dependencies
The system relies on:
1. **GL margin lookup file** - must correctly classify all revenue GL accounts
2. **Invoicees overview file** - must have current VAT validation status
3. **Transaction data quality** - VAT codes and GL codes must be correctly assigned in Exact Online

---

## 7. Validation Checks to Perform

As Financial Controller, you should verify:

1. **Margin Classification**
   - Review the GL margin lookup file - does each GL's classification match your understanding?
   - Are all revenue GLs properly classified as Margin or No Margin?

2. **Box Assignment Logic**
   - Do the VAT code → Box mappings align with Dutch VAT law?
   - Are purchases correctly assigned to deductible boxes (5B)?
   - Are EU transactions properly routed to 3B vs 1E?

3. **ICP Reconciliation**
   - Review the invalid VAT report - are there customers who should have valid VATs?

4. **Compare to Historical Declarations**
   - Run the algorithm on Q1/Q2/Q3 2025 data
   - Compare output to actual filed returns
   - Investigate any material differences

5. **Sample Transaction Review**
   - Pick representative transactions from each Box
   - Trace through the logic manually
   - Confirm correct classification

---

## 8. Limitations and Notes

### Scope
- This algorithm applies to **2025 and earlier only**
- For 2026+, a new system with derived VAT codes is used

### Fixed Logic
- VAT Code 95 uses Box 1A (not 1E as in Q1 2025) - this was corrected from Q2 onwards
- The 21% VAT calculation assumes standard rate (Box 1A, 4A, 4B, 5B)

### Data Dependencies
- Customer VAT validation depends on external verification (invoicees file)
- If invoicees file is not provided, VAT validity check is disabled (all treated as invalid = reclassified to 1E)

---

## Questions to Guide Your Review

1. Do the Margin assignments reflect the actual economic substance of each GL account?
2. Are the Box assignments compliant with Dutch VAT law for each transaction type?
3. Is the ICP qualification logic (valid VAT number requirement) correct?
4. Are the exclusions (balance sheet, pass-through, outside EU) appropriate?
5. Does the output match historical filed returns for 2025?

---

**Document Purpose:** This explanation is designed to help you understand the automated logic so you can verify compliance and correctness without needing to read Python code. If any aspect needs clarification or deeper investigation, please ask.
