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
| **20** (Ticket sales NL 0%) | Margin | **1E** | NL 0% margin (8xxx GLs) |
| **20** (Ticket sales NL 0%) | Margin (7212) | Nothing | Exception: 7212 in Q1 |
| **20** (Ticket sales NL 0%) | No Margin | Nothing | Pass-through |
| **95** (Ancill services NL) | Margin | **1A** or **1E** | Q1=1E, Q2/Q3=1A |
| **95** (Ancill services NL) | No Margin | Nothing | |
| **100** (Commission 21%) | Margin | **1A** | |
| **101** (Commission EU) | Margin | **3B** | ICP commission |
| **102** (Commission Non EU) | Margin | **Nothing** | Outside EU |

### Purchase VAT Codes (Costs):

| VAT Code | Margin Value | GL Type | Box |
|----------|--------------|---------|-----|
| **3** (NL VAT 9%) | NaN | 4xxx/7xxx costs | **5B** |
| **3** (NL VAT 9%) | NaN | 1xxx balance sheet | Nothing |
| **4** (NL VAT 21%) | NaN | 4xxx/7xxx costs | **5B** |
| **4** (NL VAT 21%) | NaN | 1xxx balance sheet | Nothing |
| **10** (Purchases EU 21%) | Margin | Any | **4B/5B** |
| **10** (Purchases EU 21%) | NaN | 4xxx costs | **4B/5B** |
| **10** (Purchases EU 21%) | NaN | 1xxx balance sheet | Nothing |
| **12** (Purchases outside EU) | NaN | 4xxx costs | **4A/5B** |
| **12** (Purchases outside EU) | NaN | 1xxx balance sheet | Nothing |
| **12** (Purchases outside EU) | Margin (8011) | | Nothing |

---

## 3. SUMMARY DECISION RULES

### For MARGIN column:
```
IF GL starts with 81xx AND contains "Markup/Mark up/Class drops/FX/Commission/incentive" → Margin
IF GL starts with 82xx AND contains "Mark up/FX/Commission" → Margin  
IF GL = 7212 or 7221 → Margin
IF GL = 8010, 8020, 8021, 8090, 8091, 8225 → Margin
IF GL starts with 81xx AND contains "Turnover" → No Margin
IF GL starts with 82xx AND contains "Turnover" → No Margin
IF GL starts with 72 AND contains "COGS" → No Margin
IF GL = 7211 → No Margin
IF GL starts with 4xxx (costs) → blank/NaN
IF GL starts with 1xxx (balance sheet) → blank/NaN
```

### For BOX column:
```
IF VAT = 8 AND Margin = "Margin" → 3B (ICP)
IF VAT = 8 AND Margin = "No Margin" → Nothing
IF VAT = 6 → Nothing (outside EU)
IF VAT = 20 AND Margin = "Margin" AND GL starts with 8 → 1E
IF VAT = 20 AND Margin = "No Margin" → Nothing
IF VAT = 2 AND Margin = "Margin" → 1A
IF VAT = 95 AND Margin = "Margin" → 1A (or 1E in Q1)
IF VAT = 101 AND Margin = "Margin" → 3B
IF VAT = 102 → Nothing
IF VAT = 10 AND GL starts with 4/7 (not 1xxx) → 4B/5B
IF VAT = 10 AND GL starts with 1 → Nothing
IF VAT = 12 AND GL starts with 4/7 (not 1xxx) → 4A/5B
IF VAT = 12 AND GL starts with 1 → Nothing
IF VAT = 3 or 4 AND GL starts with 4 → 5B
IF VAT = 3 or 4 AND GL starts with 1 → Nothing
```

---

## 4. NOTES

1. **VAT Code 95 inconsistency**: Q1 used Box=1E for margin items, but Q2/Q3 switched to Box=1A. This appears to be a correction.

2. **Balance sheet accounts** (1xxx series) always get Box=Nothing regardless of VAT code, because they don't belong in the VAT return.

3. **7212 with VAT 20 in Q1**: Was Box=Nothing, but in Q2/Q3 it correctly became 1E. This was likely a data entry error in Q1.

4. **The key insight**: The Box column represents which line of the Dutch VAT return (BTW-aangifte) the amount should be reported on:
   - 1A = Deliveries/services taxed at 21%/9% rate
   - 1E = Deliveries/services taxed at 0% rate
   - 3B = ICP (Intra-Community supplies to EU businesses)
   - 4A = Services purchased from outside EU
   - 4B = Goods purchased from within EU (ICT)
   - 5A/5B = Input VAT to be deducted
   - Nothing = Not part of VAT return (balance sheet items, pass-through)
