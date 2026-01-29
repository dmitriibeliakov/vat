# VAT Declaration: Margin & Box Column Logic

## Analysis Summary
Based on analysis of Q1, Q2, and Q3 2025 VAT declaration files.
This logic does not apply to 2026 onwards.

---

## 1. MARGIN COLUMN LOGIC

### Rule: Margin is determined 100% by GL Account

The Margin column is **NOT** based on VAT code. It's purely based on the GL account number.

### GL Accounts that are ALWAYS "Margin":
| GL Code | Description |
|---------|-------------|
| 7212 | Consolidator fees costs |
| 7221 | Mark up on compensation of Intercompany expenses (LV) |
| 8010 | Turnover Saas One off fees |
| 8011 | Turnover Saas montly fees |
| 8020 | Airline incentives Intercompany |
| 8021 | GDS incentives |
| 8090 | Platform subscription fee |
| 8091 | Minimum booking fee |
| 8100 | Markup Marine |
| 8101 | Markup Corporate |
| 8104 | Class drops Marine |
| 8105 | Class drops Corporate |
| 8106 | FX markup |
| 8107 | Consolidator markup |
| 8110 | GDS incentive compensation markup |
| 8202 | Mark up ancillary services NL Corporate |
| 8203 | FX markup ancillary services NL Corporate |
| 8205 | Commissions ancillary services NL Corporate |
| 8206 | Commission Hotels (online) |
| 8212 | Mark up ancillary services EU Corporate |
| 8213 | FX markup ancillary services EU Corporate |
| 8222 | Mark up ancillary services outside EU Corporate |
| 8223 | FX markup ancillary services outside EU Corporate |
| 8225 | Extra baggage |

### GL Accounts that are ALWAYS "No Margin":
| GL Code | Description |
|---------|-------------|
| 7211 | Cost of Goods Turnover (0%) |
| 72114 | COGS_IATA_EMDA_NL |
| 72115 | COGS_IATA_EMDS_NL |
| 72116 | COGS_IATA_RFND_NL |
| 72119 | COGS_IATA_TKTT_NL |
| 8102 | Turnover Tickets Marine |
| 8103 | Turnover Tickets Corporate |
| 8115 | Turnover hotels |
| 8201 | Turnover ancillary services NL Corporate |
| 8211 | Turnover ancillary services EU Corporate |
| 8221 | Turnover ancillary services outside EU Corporate |

### GL Accounts that are ALWAYS blank/NaN (cost accounts):
All 4xxx accounts (personnel, subscriptions, office costs, etc.) and balance sheet accounts (1xxx) have no margin value.

### Pattern Recognition:
- **"Margin"** = Revenue accounts where C Teleport earns a spread/markup/commission
- **"No Margin"** = Pass-through turnover (COGS, pure turnover without markup)
- **Blank/NaN** = Cost/expense accounts and balance sheet items

---

## 2. BOX COLUMN LOGIC

### Rule: Box is determined by VAT Code + Margin combination + GL account type

The Box assignment follows this decision tree:

### Sales VAT Codes (Revenue):

| VAT Code | Margin Value | Box | Notes |
|----------|--------------|-----|-------|
| **2** (Ticket sales 21% NL) | Margin | **1A** | NL sales with VAT |
| **2** (Ticket sales 21% NL) | NaN/blank | Nothing | Balance sheet items |
| **6** (Ticket sales outside EU) | Any | **Nothing** | Outside EU = not taxable in NL |
| **8** (Ticket Sales within EU) | Margin | **3B** | ICP - margin on EU sales |
| **8** (Ticket Sales within EU) | No Margin | Nothing | Pass-through turnover |
| **20** (Ticket sales NL 0%) | Margin | **1E** | NL 0% margin (7xxx/8xxx GLs) |
| **20** (Ticket sales NL 0%) | No Margin | Nothing | Pass-through |
| **95** (Ancill services NL) | Margin | **1A** or **1E** | Q1=1E, Q2/Q3=1A |
| **95** (Ancill services NL) | No Margin | Nothing | |
| **100** (Commission 21%) | Margin | **1A** | |
| **101** (Commission EU) | Margin | **3B** | ICP commission |
| **102** (Commission Non EU) | Margin | **Nothing** | Outside EU |

### Purchase VAT Codes (Costs):

The `vat_type` column determines whether a line is a purchase (deductible VAT):
- `vat_type = "I"` → Input/purchase transaction (VAT is deductible)
- `vat_type = "O"` or `"P"` → Offset/accrual entries (excluded from VAT return)

| VAT Code | vat_type | GL Condition | Box |
|----------|----------|--------------|-----|
| **3** (NL VAT 9%) | I | Any | **5B** |
| **3** (NL VAT 9%) | O/P | Any | Nothing |
| **4** (NL VAT 21%) | I | Any | **5B** |
| **4** (NL VAT 21%) | O/P | Any | Nothing |
| **10** (Purchases EU 21%) | I | 4xxx/7xxx costs OR 150/160 | **4B, 5B** |
| **10** (Purchases EU 21%) | I | Other (e.g., 1xxx balance sheet) | Nothing |
| **10** (Purchases EU 21%) | O/P | Any | Nothing |
| **12** (Purchases outside EU) | I | 4xxx/7xxx costs OR 150/160 | **4A, 5B** |
| **12** (Purchases outside EU) | I | Other (e.g., 1xxx balance sheet) | Nothing |
| **12** (Purchases outside EU) | O/P | Any | Nothing |

---

## 3. SUMMARY DECISION RULES

### For MARGIN column:
```
IF GL starts with 81xx AND contains "Markup/Mark up/Class drops/FX/Commission/incentive" → Margin
IF GL starts with 82xx AND contains "Mark up/FX/Commission" → Margin  
IF GL = 7212 or 7221 → Margin
IF GL = 8010, 8011, 8020, 8021, 8090, 8091, 8225 → Margin
IF GL starts with 81xx AND contains "Turnover" → No Margin
IF GL starts with 82xx AND contains "Turnover" → No Margin
IF GL starts with 72 AND contains "COGS" → No Margin
IF GL = 7211 → No Margin
IF GL starts with 4xxx (costs) → blank/NaN
IF GL starts with 1xxx (balance sheet) → blank/NaN
```

### For BOX column:

**Sales VAT Codes (based on Margin):**
```
IF VAT = 2 AND Margin = "Margin" → 1A
IF VAT = 6 → Nothing (outside EU, never taxable in NL)
IF VAT = 8 AND Margin = "Margin" → 3B (ICP)
IF VAT = 8 AND Margin = "No Margin" → Nothing
IF VAT = 20 AND Margin = "Margin" AND GL starts with 7 or 8 → 1E
IF VAT = 20 AND Margin ≠ "Margin" → Nothing
IF VAT = 95 AND Margin = "Margin" → 1A (Q2/Q3 2025 convention)
IF VAT = 100 AND Margin = "Margin" → 1A
IF VAT = 101 AND Margin = "Margin" → 3B (ICP)
IF VAT = 102 → Nothing (outside EU)
```

**Purchase VAT Codes (based on vat_type + GL):**
```
vat_type "I" = Input/purchase (VAT deductible)
vat_type "O"/"P" = Offset/accrual entries (excluded)
Cost/Asset GL = GL starts with 4 or 7, OR GL = 150 or 160

IF VAT = 3 AND vat_type = "I" → 5B
IF VAT = 4 AND vat_type = "I" → 5B
IF VAT = 10 AND vat_type = "I" AND Cost/Asset GL → 4B, 5B
IF VAT = 12 AND vat_type = "I" AND Cost/Asset GL → 4A, 5B
All other cases → Nothing
```

---

## 4. NOTES

1. **VAT Code 95 inconsistency**: Q1 used Box=1E for margin items, but Q2/Q3 switched to Box=1A. This appears to be a correction. The implemented logic uses 1A.

2. **Balance sheet accounts** (1xxx series) generally get Box=Nothing, because they don't belong in the VAT return. However, GL 150 (Inventory) and GL 160 (Computers) are exceptions—they are fixed assets and do get Box assignment for purchase VAT codes.

3. **7212 with VAT 20**: GL 7212 (Consolidator fees costs) gets Box=1E when paired with VAT 20 and Margin. The rule applies to both 7xxx and 8xxx Margin accounts.

4. **vat_type column**: For purchase VAT codes (3, 4, 10, 12), the `vat_type` column from the raw data determines whether VAT is deductible:
   - `vat_type = "I"` (Input) → This is a purchase, VAT is deductible
   - `vat_type = "O"` or `"P"` (Offset) → Accrual/reversal entry, excluded from VAT return

   This is more reliable than inferring from GL account alone.

5. **Cost/Asset GL definition**: For VAT 10 and 12, even with `vat_type = "I"`, an additional GL check excludes balance sheet items:
   - GL starting with 4 or 7 → Cost accounts (included)
   - GL = 150 or 160 → Fixed assets (included)
   - Other 1xxx → Balance sheet (excluded)

6. **The key insight**: The Box column represents which line of the Dutch VAT return (BTW-aangifte) the amount should be reported on:
   - 1A = Deliveries/services taxed at 21%/9% rate
   - 1E = Deliveries/services taxed at 0% rate
   - 3B = ICP (Intra-Community supplies to EU businesses)
   - 4A = Services purchased from outside EU
   - 4B = Goods purchased from within EU (ICT)
   - 5B = Input VAT to be deducted
   - Nothing = Not part of VAT return (balance sheet items, pass-through)
