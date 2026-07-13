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

## Implementation

`app/main_old.py`'s `get_box()` implements this mapping for the new codes
(added 2026-07-13, alongside the pre-existing numeric-code logic used for
2025-and-earlier data and the early part of Q2 2026). Unlike the old numeric
codes, box assignment for the new codes depends only on `vat_code` — no
GL-based Margin lookup is needed, since the new codes are category-specific
by construction.

One known gap carried over from the old logic, not fixed here: `build_vat_declaration()`
applies a flat 21% VAT rate to any box ending in "A" or "B", including `UN9`
(9% reduced rate, rare/low materiality) landing in Box 5B. Needs a rate-aware
fix if `UN9` volume grows.
