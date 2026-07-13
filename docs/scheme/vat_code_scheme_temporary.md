# VAT Code Scheme - Temporary (Transitionary)

*Transitionary scheme before migrating to the [future ideal scheme](vat_code_scheme_future.md)*

---

## Key Difference from Future Scheme

In the future scheme, non-flight pass-through amounts (GMV, COGS) are **Out of Scope** under a single `PAS` category. In this temporary scheme, pass-through amounts are **not separated** from revenue - the full invoiced amount (pass-through + margin) is treated as a single supply and taxed based on service type:

| Service Type | NL VAT Rate | Rationale                          |
|:-------------|:------------|:-----------------------------------|
| Cars         | 21%         | Standard rate - domestic car rental |
| Hotels       | 9%          | Reduced rate - accommodation        |
| Other        | 0%          | Zero-rated (intermediation)         |
| Flights      | 0%          | Zero-rated (int'l transport)        |

---

## Core Logic

Same two-input approach as the future scheme, but with **finer service-type categories**:

| Input        | Source                  | Determines               |
|:-------------|:------------------------|:--------------------------|
| **Category** | GL Account              | What type of service      |
| **Geography**| Customer/Supplier Country | Where the customer is located |

---

## VAT Code Structure

Format: `[Category]-[Geography]`

### Categories (from GL Code)

| Code    | Category          | Description                                                |
|:--------|:------------------|:-----------------------------------------------------------|
| **FLT** | Flights           | Margins and markups on flights                             |
| **CAR** | Cars              | Car rental revenue + pass-through (full amount)            |
| **HTL** | Hotels            | Hotel revenue + pass-through (full amount)                 |
| **NFO** | Non-Flight Other  | Other non-flight services: trains, SaaS, platform, baggage |
| **FXE** | FX/Exempt         | Currency/FX markup (exempt financial service)              |
| **REF** | Refunds           | Tax refunds                                                |
| **PUR** | Purchases         | Costs/expenses                                             |

### Geographies (from Customer/Supplier Country)

| Code   | Geography          | Description                                          |
|:-------|:-------------------|:-----------------------------------------------------|
| **NL** | Netherlands        | Dutch customer/supplier                              |
| **EU** | EU (excl. NL)      | Non-NL EU customer/supplier with valid VAT number    |
| **EX** | Non-NL EU no VAT   | Non-NL EU customer without valid VAT number          |
| **XX** | Non-EU             | Customer/supplier outside EU                         |

---

## Treatment Derivation Matrix

| Category | NL  | EU  | EX (EU no VAT) | XX  |
|:---------|:----|:----|:----------------|:----|
| **FLT**  | 0   | 0   | 0               | OOS |
| **CAR**  | 21  | RC  | 21              | OOS |
| **HTL**  | 9   | RC  | 9               | OOS |
| **NFO**  | 0   | 0   | 0               | OOS |
| **FXE**  | EXM | EXM | EXM             | EXM |
| **REF**  | OOS | OOS | OOS             | OOS |
| **PUR**  | 21/9| RC  | -               | RC  |

### Treatment Codes Explained

| Treatment | Meaning                          | VAT Return         |
|:----------|:---------------------------------|:-------------------|
| **21**    | 21% Dutch VAT charged            | Box 1A             |
| **9**     | 9% Dutch VAT charged (reduced)   | Box 1A             |
| **0**     | 0% zero-rated supply             | Box 1E             |
| **RC**    | Reverse Charge to customer       | Box 3B (sales) or 4A/4B (purchases) |
| **OOS**   | Out of Scope - not reportable    | Not reported        |
| **EXM**   | VAT Exempt (Article 135)         | Not reported        |

---

## Complete VAT Code List

### Revenue Codes

| VAT Code | Treatment | Box | ICP  | Invoice Text                                              |
|:---------|:----------|:----|:-----|:----------------------------------------------------------|
| FLT-NL   | 0         | 1E  | No   | VAT 0% - intermediation int'l passenger transport         |
| FLT-EU   | 0         | 1E  | No   | VAT 0% - intermediation int'l passenger transport         |
| FLT-EX   | 0         | 1E  | No   | VAT 0% - intermediation int'l passenger transport         |
| FLT-XX   | OOS       | -   | No   | *(none)*                                                  |
| CAR-NL   | 21        | 1A  | No   | VAT 21%                                                   |
| CAR-EU   | RC        | 3B  | **Yes** | Reverse charge - Article 196 Directive 2006/112/EC     |
| CAR-EX   | 21        | 1A  | No   | VAT 21%                                                   |
| CAR-XX   | OOS       | -   | No   | *(none)*                                                  |
| HTL-NL   | 9         | 1A  | No   | VAT 9%                                                    |
| HTL-EU   | RC        | 3B  | **Yes** | Reverse charge - Article 196 Directive 2006/112/EC     |
| HTL-EX   | 9         | 1A  | No   | VAT 9%                                                    |
| HTL-XX   | OOS       | -   | No   | *(none)*                                                  |
| NFO-NL   | 0         | 1E  | No   | VAT 0% - intermediation                                   |
| NFO-EU   | 0         | 1E  | No   | VAT 0% - intermediation                                   |
| NFO-EX   | 0         | 1E  | No   | VAT 0% - intermediation                                   |
| NFO-XX   | OOS       | -   | No   | *(none)*                                                  |
| FXE      | EXM       | -   | No   | VAT exempt - Article 135 Directive 2006/112/EC            |
| REF      | OOS       | -   | No   | *(none)*                                                  |

### Purchase Codes

| VAT Code | Treatment | Box      |
|:---------|:----------|:---------|
| PUR-NL   | 21 (or 9) | 5B       |
| PUR-EU   | RC        | 4B + 5B  |
| PUR-XX   | RC        | 4A + 5B  |

---

## GL Account -> Category Mapping

### FLT (Flights)

| GL Code | GL Name                            |
|:--------|:-----------------------------------|
| 8100    | Markup Marine                      |
| 8101    | Markup Corporate                   |
| 8104    | Class drops Marine                 |
| 8105    | Class drops Corporate              |
| 8107    | Consolidator markup                |
| 8110    | GDS incentive compensation markup  |
| 8020    | Airline incentives Intercompany    |
| 8021    | GDS incentives                     |
| 80134   | IATA Commission TKTT NL            |
| 81134   | IATA Commission TKTT LV            |
| 8102    | Turnover Tickets Marine            |
| 8103    | Turnover Tickets Corporate         |
| 7211    | Cost of Goods Turnover (0%)        |
| 72114-72149 | COGS IATA accounts             |
| 7212    | Consolidator fees costs            |

### CAR (Cars)

| GL Code | GL Name                                        |
|:--------|:-----------------------------------------------|
| *(TBD)* | Car rental turnover + pass-through GL accounts |

### HTL (Hotels)

| GL Code | GL Name                            |
|:--------|:-----------------------------------|
| 8115    | Turnover hotels                    |
| 8206    | Commission Hotels (online)         |

### NFO (Non-Flight Other)

| GL Code | GL Name                                    |
|:--------|:-------------------------------------------|
| 8205    | Commissions ancillary services             |
| 8202    | Mark up ancillary services NL              |
| 8212    | Mark up ancillary services EU              |
| 8222    | Mark up ancillary services outside EU      |
| 8225    | Extra baggage                              |
| 8010    | Turnover SaaS One off                      |
| 8011    | Turnover SaaS monthly                      |
| 8090    | Platform subscription fee                  |
| 8091    | Minimum booking fee                        |
| 8201    | Turnover ancillary services NL             |
| 8211    | Turnover ancillary services EU             |
| 8221    | Turnover ancillary services outside EU     |

### FXE (FX/Exempt)

| GL Code | GL Name                                    |
|:--------|:-------------------------------------------|
| 8106    | FX markup                                  |
| 8203    | FX markup ancillary                        |
| 8213    | FX markup ancillary services EU            |
| 8223    | FX markup ancillary services outside EU    |

### REF (Refunds)

| GL Code | GL Name    |
|:--------|:-----------|
| 8229    | Tax refund |

### PUR (Purchases)

| GL Code | GL Name                                          |
|:--------|:-------------------------------------------------|
| 4xxx    | All operating expenses                           |
| 7220    | Compensation of Intercompany expenses            |
| 7221    | Mark up on compensation Intercompany (LV)        |

---

## VAT Return Box Mapping

| Box    | VAT Codes                         |
|:-------|:----------------------------------|
| **1A** | CAR-NL, CAR-EX, HTL-NL, HTL-EX   |
| **1E** | FLT-NL, FLT-EU, FLT-EX, NFO-NL, NFO-EU, NFO-EX |
| **3B** | CAR-EU, HTL-EU                    |
| **4A** | PUR-XX                            |
| **4B** | PUR-EU                            |
| **5B** | PUR-NL, PUR-EU, PUR-XX           |

---

## ICP Report

**Filter**: VAT Code in (`CAR-EU`, `HTL-EU`)

**Validation**: Box 3B total = ICP total

---

## Migration Notes

When transitioning to the future scheme:
1. `CAR` and `HTL` pass-through amounts move back to `PAS` (OOS)
2. `CAR` and `HTL` margin amounts merge into `NFT`
3. `NFO` margin amounts merge into `NFT`
4. Flight pass-through amounts (tickets, COGS) move from `FLT` back to `PAS`
