# VAT Entity Structure Decision: Stay in NL vs. Move Outside EU

**Executive Summary for C Teleport BV Leadership**
**Date: April 2026**

---

## The Question in Plain Terms

The **disclosed agent model** requires us to show our margins on invoices for non-flight products. Flights (96.7% of turnover) are unaffected — 0% VAT, no disclosure. The real exposure is **~1% or less of revenue** where margins become visible to customers (non-flight ancillaries, trains, car rental). Mind that flight ancillaries remain 0% and therefore hidden.

So the decision reduces to: **does exposing margins on ~1% of revenue justify migrating to a new entity, a new accounting system, and months of work?**

There is a third path worth noting: we could redesign our pricing model to become a fully transparent agent — charging customers a fee based on turnover or transaction volume rather than hiding margins in product prices. That would align naturally with the disclosed agent VAT model and remove the margin visibility concern entirely. However, that is a commercial/product decision that warrants its own discussion.

---

## Decision Tree

```
C Teleport BV — VAT structure decision
│
├─ OPTION A: Stay in the Netherlands (disclosed agent)
│  ├─ No migration — continue with Exact Online
│  ├─ Switch invoicing to disclosed agent model
│  │  ├─ Pass through vendor costs without VAT (doorlopende post)
│  │  └─ Disclose and separately VAT our markup/commission. Markups for flights, flight ancillaries and hotels remain hidden. All the rest - disclosed.
│  ├─ Build automated VAT code assignment + reporting (already in progress)
│  └─ Accept ongoing complexity of Dutch/EU VAT rules. Risk of tax exposure.
│
└─ OPTION B: Open entity outside Europe
   ├─ Migrate to multi-entity accounting system. Very complex. PO and IT heavily involved.
   ├─ Restructure contracts, banking, IATA licenses
   ├─ Potentially simpler VAT on non-EU entity's transactions
   └─ NL entity still needed → dual compliance burden
```

---

## Revenue Split (April 2026 Data)

| Product          | Share of turnover | Disclosed agent model |
|:-----------------|:------------------|-------------------|
| **Flights**      | 96.7%             | Not affected |
| **Hotels**       | 2.5%              | Attempt to convert markups to RateHawk's cashback. RateHawk becomes the customer. |
| **Other** (ancillaries, trains, car rental, etc.) | 0.7% | Disclose markups. Flight ancillaries remain not affected. |

The VAT complexity concentrates on **3.3% of turnover** or even less than 0.7% if we focus on other ancillaries (excluding non-flight). Flights — the overwhelming majority — are 0% with no margin disclosure requirement. Hotels (potentially) can hide margins.

---

## Open Items for Discussion

| #    | Item                                     | Owner      | Question                                                     |
| :--- | :--------------------------------------- | :--------- | :----------------------------------------------------------- |
| 1    | **Consolidator markup on hotels**        | Petr       | Do we have a consolidator markup for hotels (similar to flight consolidator markup)? If so, does it need to be disclosed separately under the disclosed agent model, or can it be structured as cashback? If this is a blocker - question to Lennart if we can stop charging them? |
| 2    | **GL account splitting for ancillaries** | VP Finance | Currently, flight and non-flight ancillaries land in the same GL accounts. Flight ancillaries are 0%, non-flight are 21%. The cleanest approach is to split them into separate GL accounts so each account maps to exactly one VAT code. Trade-off: more GL accounts vs. cleaner VAT automation. |

---

## Option A: Stay in the Netherlands (Disclosed Agent)

### What Changes

As a disclosed agent, C Teleport acts transparently as an intermediary: the customer knows who the actual supplier is (airline, hotel, rental company). This means:

1. **Vendor costs are pass-through** (doorlopende post) — not part of our taxable amount
2. **Only our markup/commission is subject to VAT** — and must be **disclosed** separately on invoices
3. **TOMS (Tour Operator Margin Scheme) does not apply** — we are not bundling flights/hotels/cars or reselling (literally buying and then selling). We don't want TOMS. It is bad for us and a customer.

### VAT Treatment by Product Line

| Product                    | Vendor cost             | Our markup (NL customer) | Our markup (EU customer) | Margin disclosed? |
|:---------------------------|:------------------------|:-------------------------|:-------------------------|:------------------|
| **Flights**, incl. class drops, all sorts of markups | Pass-through (0%)       | **0%**                   | **0%**                   | **No** (same rate) |
| **Flight ancillaries** incl. seat, baggage, meals | Pass-through (0%)       | **0%**                   | **0%**                   | **No** (same rate) |
| **Non-flight ancillaries and other transport modalities** | Pass-through            | **21%**                  | Reverse charge           | **Yes**           |
| **Hotels**                 | Pass-through            | **21%**                  | Reverse charge           | **Potentially No** — if restructured as cashback from Ratehawk (see below) |
| **FX markup**              | n/a                     | **Exempt**               | **Exempt**               | **No** — blended into invoice line items (pass-through on invoice), reported as Exempt in Exact Online |

### What is simple (no change needed)

- **Flights and flight ancillaries** (baggage, seat selection, meals, class changes): **0% across the board**. Both the flight itself and our intermediation are zero-rated under Dutch law (Tabel II, posts b.3 and b.4). No obligation to disclose the margin. This covers ~90%+ of revenue. BDO confirmed this treatment is correct.

### What requires work

- **Hotels**: Currently we apply 9% on total hotel value, which is incorrect. Under disclosed agent, the hotel price becomes pass-through. Our markup would normally be separately shown at 21%. However, the margin can be hidden if restructured as **cashback from Ratehawk** — i.e., Ratehawk pays us a volume incentive rather than us marking up the hotel price to the customer. This requires two prerequisites:
  1. **New agreement with Ratehawk** — the contract must explicitly structure the payment as cashback/incentive from Ratehawk to C Teleport, not as a markup on the customer price
  2. **Demonstrate revenue source** — we must be able to show that this income is generated by Ratehawk (the supplier) rewarding us for volume/performance, not by customers paying above the hotel rate. The economic substance must support the claim that this is cashback, not a disguised margin

- **Non-flight ancillaries** (trains, airport lounge, car rental intermediation): Our markup must be disclosed and taxed at 21% for Dutch customers. This is new — previously margins were not always transparent. Currently the markups are hidden as we charge 21% over the total amount of ancillaries.

- **Edge cases and permanent grey areas**:
  - Car rental: short-term (up to 30 days) is taxed where the car is picked up; long-term changes the place of supply. However, long term rental is extremely unlikely.
  - Hotel breakfast: 9% rate vs. 21% for accommodation (separate supplies since 2026)
  - Items that straddle flight vs. non-flight (e.g., is airport lounge part of the flight? No — it is personal comfort, taxed at 21%)
  - Credit card and FX fees may be exempt financial transactions, but if they exceed 1% of turnover, this could affect input VAT recovery

### Pros

| #   | Advantage                                                                                                    |
|:----|:-------------------------------------------------------------------------------------------------------------|
| 1   | **No migration** — continue with Exact Online, existing bank accounts, IATA NL license, contracts            |
| 2   | **Already in progress** — VAT code assignment automation, test suite, and reporting pipeline are being built  |
| 3   | **Flights are simple** — 0% on everything, no margin disclosure, covers the majority of business             |
| 4   | **Deterministic compliance** — rules are complex but codifiable: code + tests = auditable, reproducible VAT  |
| 5   | **BDO has confirmed** the disclosed agent treatment for all product lines (memo July 2025)                   |
| 6   | **EU presence** — valuable for EU B2B customers (reverse charge mechanism, ICP reporting, credibility)       |
| 7   | **No dual-entity overhead** — single set of books, single audit, single filing                               |

### Cons

| #    | Disadvantage                                                 |
| :--- | :----------------------------------------------------------- |
| 1    | **Permanent complexity** — Dutch VAT rules are intricate; edge cases (long-term car rental, breakfast split, personal comfort items) will always require judgment calls |
| 2    | **100% compliance is aspirational** — there will always be minor areas of imperfect treatment. This is a fact of operating under EU VAT, not a solvable problem |
| 3    | **Margin transparency** — disclosing markup on hotels, trains, and other non-flight items changes commercial dynamics. Customers see exactly what we earn |
| 4    | **Ongoing development cost** — maintaining the VAT code system, updating rules when law changes (e.g., hotel rate from 9% to 21% in 2026), handling new product types |

---

## Option B: Open Entity Outside Europe

### What This Means

Establish a new legal entity in a non-EU jurisdiction. The non-EU entity would handle some or all of the business, potentially moving the place of supply outside the Dutch/EU VAT system.

### Pros

| #    | Advantage                                                    |
| :--- | :----------------------------------------------------------- |
| 1    | **Simpler VAT on non-EU transactions** — services supplied from outside the EU to non-EU customers are completely outside scope of EU VAT |
| 2    | **No margin disclosure obligation** — non-EU entity is not subject to Dutch disclosed agent rules |
| 3    | **New IATA license** - independence from GMT, marginal savings. |

### Cons

| #    | Disadvantage                                                 |
| :--- | :----------------------------------------------------------- |
| 1    | **Massive migration project** — new accounting system (Odoo shortlisted), new chart of accounts, new processes, new integrations. |
| 2    | **Multi-entity accounting** — intercompany transactions, transfer pricing, consolidation. Dramatically increases accounting complexity. We need to get there at some point, but is it the right moment, when our product department is not fully functional? |
| 3    | **NL entity probably still needed** — IATA NL license, existing NL customer contracts, NL-based team. Result: **two** compliance burdens, not zero |
| 5    | **Contract migration** — all existing customer and vendor agreements reference C Teleport BV (NL) |
| 6    | **Banking and payments** — new banking relationships, potential issues with payment processing across entities. Maybe can be done easily with Revolut. |
| 7    | **Transfer pricing scrutiny** — tax authorities (NL and new jurisdiction) will examine intercompany pricing. This is an ongoing compliance cost that replaces, rather than eliminates, the VAT complexity |
| 8    | **Timeline** — realistically 6-12+ months before the new entity is operational and carrying transactions |
| 9    | **EU customers still trigger EU VAT** — if the non-EU entity provides services to EU B2B customers, the customers must self-assess VAT. Fugro stops buying hotels with us because we cannot recover VAT for them. |

---

## Side-by-Side Comparison

| Criterion                  | Option A: Stay in NL                    | Option B: Non-EU Entity                                      |
| :------------------------- | :-------------------------------------- | :----------------------------------------------------------- |
| **Migration effort**       | None                                    | Very high (6-12+ months)                                     |
| **Accounting system**      | Keep Exact Online                       | Migrate to Odoo (multi-entity)                               |
| **Margin disclosure**      | Required for hotels, trains, car rental | Not required (non-EU entity)                                 |
| **Compliance complexity**  | High but codifiable                     | High (one more jurisdiction + transfer pricing)              |
| **Ongoing cost**           | Dev time for VAT automation             | Dual accounting + audit + legal + compliance                 |
| **Risk of non-compliance** | Medium — edge cases exist               | Medium — different edge cases (transfer pricing, PE risk, substance requirements) |
| **Timeline to implement**  | Weeks (automation already in progress)  | 6-12+ months                                                 |
| **Reversibility**          | Fully reversible                        | Very hard to reverse                                         |

---

## Key Insight

**96.7% of C Teleport's turnover is flight intermediation**, which is **0% VAT regardless of entity structure**. The entire VAT complexity concentrates on the remaining 3.3% (hotels 2.5%, other 0.7%).

A full entity restructuring to avoid VAT on 3.3% of turnover — at the cost of a multi-month migration, dual-entity accounting, and transfer pricing compliance — is not justified at current product mix. The calculus changes only if non-flight products gain significant traction.

---

## Questions for Management Team Discussion

| #    | Question                                                     | Who decides   |
| :--- | :----------------------------------------------------------- | :------------ |
| 1    | **Hotel consolidator markup** — do we charge a consolidator markup on hotels? If yes, can it be restructured as Ratehawk cashback, or should we stop charging it altogether? | Petr, Lennart |
| 2    | **Ratehawk cashback agreement** — are we ready to sign a new agreement with Ratehawk that structures our hotel income as cashback/incentive (supplier-side revenue), not as a customer-facing markup? | Hady          |
| 3    | **GL account split for ancillaries** — do we split flight ancillaries (0%) and non-flight ancillaries (21%) into separate GL accounts for clean VAT automation? More GL accounts, but cleaner compliance. | Hady          |
| 4    | **Transparent agent pricing model** — should we explore charging customers a flat fee (e.g., % of turnover or per-transaction) instead of hiding margins in product prices? This eliminates the disclosure concern entirely but changes our commercial model. | Leadership    |
| 5    | **Is now the right time for multi-entity?** — we will need multi-entity accounting at some point, but is it justified now given the product department's current capacity and the small non-flight revenue share? | Leadership    |

---

*This document is based on the BDO memo of 9 July 2025, Dutch VAT law (Wet op de omzetbelasting 1968), EU VAT Directive 2006/112/EC, and internal analysis of C Teleport's product lines and accounting structure.*
