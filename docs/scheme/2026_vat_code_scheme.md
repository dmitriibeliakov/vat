# 2026 VAT code scheme (Exact Online, as implemented)

Exact Online rolled out a new 3-letter VAT code scheme starting the **last
weeks of Q2 2026**, alongside the old numeric codes (2, 6, 8, 20, 95, 100,
101, 102, 3, 4, 10, 12) during the transition — Q2 2026 transaction data
contains a mix of both.

**Source of truth:** this scheme is defined and maintained in Airtable, not
in this repo:
https://airtable.com/appPG8qsc6I48lDDX/tblejwp9mhwjrCcb8/viwFWUWmFYuXytJGy

The tables below are a snapshot transcribed from that Airtable on 2026-07-13
(screenshots in `assets/`). If the Airtable changes, re-check here.

This supersedes the code names drafted in commit `c0b7cf1` ("Define final
VAT code scheme with 3-char codes...", 2026-04-10) — the as-implemented
codes differ from that draft (e.g. `FWW`/`NWW`/`FIN` shipped instead of the
drafted `FXX`/`NXX`/`CUR`/`REF`).

## Treatment table

| Treatment | VAT codes | Notes |
|---|---|---|
| 21% | `NNL`, `UNL` | Default rate NL. Applies everywhere unless a special rule overrides. |
| 0% | `FEU`, `NEX` | VAT tax is applied, but at 0%. For EU non-NL companies this is correct per paragraph 6.2 of the Dutch tax authorities' ruling (international passenger transport). Otherwise they land in Box 3B, which requires a valid VAT number. |
| Out of Scope | `NWW`, `FWW`, `PAS` | Not reported on the Dutch VAT return. Non-EU sales and pass-through transactions. |
| Exempt | `FIN` | Payment method fees only (Ecommpay, Amex). In scope for VAT but exemption applied — requires explicit exemption text on the invoice. |
| Reverse Charge | `NEU`, `UEU`, `UWW` | Intra-EU B2B services — customer self-accounts. |
| 9% | `UN9` | Reduced rate NL (rare in our context). Purchases only. |

## GL category → VAT code

| Category | GL code prefix | VAT codes |
|---|---|---|
| Flight Margin | `F` | `FEU`, `FWW` |
| Non-Flight Margin | `N` | `NNL`, `NEU`, `NEX`, `NWW` |
| Pass-through: flights | `PAS` | `PAS` |
| Pass-through: non-flights | `PAS` | `PAS` |
| Payment method fee | `FIN` | `FIN` |
| Purchases | `U` | `UNL`, `UEU`, `UWW`, `UN9` |

## Box mapping

| Box | In ICP | Description | VAT codes |
|---|---|---|---|
| 1A | | Domestic supplies 21% — standard-rate domestic supplies | `NNL` |
| 1E | | Zero-rated supplies — intermediation in international passenger transport, and Box-1E pseudo-zero for EU-no-VAT customers | `NEX`, `FEU` |
| 3B | ✓ | Intra-EU supplies of services — reverse-charged to EU VAT-registered customers. Total must equal ICP listing | `NEU` |
| 4A | | Reverse-charged purchases — non-EU. Services purchased from suppliers outside the EU | `UWW` |
| 4B | | Reverse-charged purchases — EU. Services purchased from EU suppliers | `UEU` |
| 5B | | Input VAT deductible — recoverable VAT on purchases | `UNL`, `UEU`, `UWW`, `UN9` |

Codes with no box in this table (`NWW`, `FWW`, `PAS`, `FIN`) are intentionally
excluded from the VAT return per the Out-of-Scope / Exempt treatment above.

## Implementation: GL category, not `vat_code`, decides the sales-side box

The table above documents Exact's *intended* code scheme, but as of
2026-07-13 the actual `vat_code` values in the data were found to be
unreliable — e.g. the `82002` Commission Hotels GL (a real, taxable
markup) was being tagged `PAS` for every single transaction, including NL
customers, wrongly excluding it from the VAT return entirely (found while
investigating why Box 1A dropped in Q2). Confirmed with Dima: **don't use
Exact's `vat_code` to determine the sales-side box at all.** Instead:

1. **Margin or cost?** Source: `data/gl_category_lookup.csv`, keyed by GL
   account (Exact's stable chart of accounts, not the more volatile
   `vat_code` text). Categories: `FLT` (flight margin/commission), `NFT`
   (non-flight margin/commission), `PAS` (pass-through cost/turnover),
   `PUR` (purchase/expense), `FXE` (FX markup, treated as exempt), `REF`
   (refund).
2. **If margin (`FLT`/`NFT`), flight or not?** Flight margin (`FLT`) is
   *always* 1E for NL/EU customers — international passenger transport is
   zero-rated per paragraph 6.2 regardless of B2B status, not standard
   reverse charge — and out of scope for non-EU customers. Non-flight
   margin (`NFT`) follows the usual split: 1A if NL, 3B if EU (subject to
   the existing invalid-VAT downgrade to 1E), out of scope otherwise.
3. **If cost/exempt/refund (`PAS`/`FXE`/`REF`):** always out of scope,
   regardless of `vat_code` or customer country.

This is implemented in `get_box()` in `app/main_old.py`, checking category
before ever looking at `vat_code`. GLs categorized `PUR` (the purchase
side - 4A/4B/5B) or missing from `gl_category_lookup.csv` fall through to
the legacy `vat_code`-driven logic below, which acts as a safety net -
`main()` prints a warning if any Margin-classified GL is missing from the
category lookup.

**Impact**: this reclassifies most flight margin to EU B2B customers from
Box 3B (reverse charge, ICP-reported) to Box 1E (zero-rated, not ICP) -
a large swing, not a business change. Applied from Q2 2026 onward only;
**Q1 2026 was already filed under the old vat_code-driven treatment and
was deliberately left unchanged** (see `output/VAT final report Q1'26.xlsx`).

The old `vat_code`-driven sales logic (numeric codes 2/6/8/20/95/100/101/102,
and the new letter codes FEU/FWW/NEU/NEX/NNL/PAS/NWW documented above) is
still present in `get_box()` as that fallback path, not deleted - it's what
produced the filed Q1'26 numbers and is still exercised for the purchase
side and any uncategorized GL.

## Known gap, not fixed here

`build_vat_declaration()` applies a flat 21% VAT rate to any box ending in
"A" or "B", including `UN9` (9% reduced rate) landing in Box 5B. Low
materiality currently but needs a rate-aware fix if `UN9` volume grows.
