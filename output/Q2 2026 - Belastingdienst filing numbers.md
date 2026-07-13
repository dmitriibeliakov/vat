# Q2 2026 VAT return (BTW aangifte) — numbers to enter

Portal: https://mijnzakelijk.belastingdienst.nl/onp-ng/ (login: eHerkenning Level 3)
Period: Q2 2026 (April–June)

Generated from `output/VAT final report Q2'26.xlsx`, using the same `vat_code`-driven
treatment as Q1 2026's filing (`main_old.py --legacy-vat-code-box`), for filing
consistency across quarters. See `docs/scheme/2026_vat_code_scheme.md` for why a
newer, more accurate treatment exists but wasn't used for this filing.

## Rubriek 1: Leveringen/diensten binnen Nederland

| Rubriek | Omzet (turnover) | Btw (VAT) |
|---|---|---|
| 1a — Leveringen/diensten belast met hoog tarief (21%) | **19.260** | **4.045** |
| 1e — Leveringen/diensten belast met 0% of niet bij u belast | **416.345** | — |

## Rubriek 3: Prestaties naar het buitenland

| Rubriek | Omzet (turnover) |
|---|---|
| 3b — Leveringen/diensten naar landen binnen de EU | **771.182** |

## Rubriek 4: Leveringen/diensten vanuit het buitenland aan u verricht

| Rubriek | Omzet (turnover) | Btw (VAT) |
|---|---|---|
| 4a — Leveringen/diensten uit landen buiten de EU | **339.479** | **71.291** |
| 4b — Leveringen/diensten uit landen binnen de EU | **344.292** | **72.301** |

## Rubriek 5: Voorbelasting, kleineondernemersregeling, totaal

| Rubriek | Bedrag |
|---|---|
| 5b — Voorbelasting (input VAT to deduct) | **167.959** |

`5b` is the sum of the VAT amounts on 4a + 4b + the domestic input VAT base
(deductible VAT on domestic purchases, EUR 24.367) — it is **not** a turnover
figure, it's the single deductible-VAT number the portal asks for in Rubriek 5b.

## Sanity check before submitting

- Box 3b (771.182) must equal the total of the ICP submission (`ICP Q2'26.csv`) — verified, both are 771.182,25.
- Compare against Q1 2026's filed return for a gut-check on scale (see PR #1 on the vat-reporting repo for the full quarter-over-quarter breakdown and the analysis of what's driving the changes).

## ICP (Opgaaf ICP)

File: `output/ICP Q2'26.csv` — 168 customers, EUR 771.182,25 total (amounts are
positive, per the Tax Connection ICP submission convention — the source data in
Exact/the VAT report keeps revenue as negative, so the sign was flipped for this
file only). Submit via Tax Connection, not the main Belastingdienst portal.
