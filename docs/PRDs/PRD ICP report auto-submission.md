# PRD: Automated ICP Report Submission

## Problem

C Teleport BV currently submits the ICP declaration (Opgaaf Intracommunautaire Prestaties) via Tax Connection. The data preparation is already automated by this project — the remaining question is whether the submission itself can be automated.

## Goal

Evaluate feasibility and recommend an approach for programmatically submitting the quarterly ICP report to the Belastingdienst.

---

## How ICP Filing Works Electronically

### Same Channel as VAT Returns

ICP declarations use the **exact same Digipoort/SBR infrastructure** as VAT returns:

- Same **WUS 2.0 SOAP** endpoints (Aanleverservice + Statusinformatieservice)
- Same **PKIoverheid certificates** for authentication
- Same **XBRL** format, but different taxonomy entry point

| Filing type | Taxonomy entry point                |
|:------------|:------------------------------------|
| VAT return  | `bd-rpt-ob-aangifte-{year}.xsd`     |
| ICP report  | `bd-rpt-icp-opgaaf-{year}.xsd`      |

**Important**: ICP declarations must be submitted individually — they cannot be bundled with a VAT return in a single message.

### XBRL Content for ICP

The ICP XBRL instance document contains:

- Company fiscal number (RSIN/KvK)
- Reporting period (quarter)
- Per counterparty:
  - VAT identification number
  - Country code (2-letter ISO)
  - Total amount of intra-community supplies (services and/or goods)

### Authentication

Identical to VAT return submission — requires a **PKIoverheid Private Services Server Certificate** (see [PRD VAT return auto-submission.md](PRD%20VAT%20return%20auto-submission.md) for details).

### Test Environment

Same as VAT — the Digipoort preproduction environment at `preprod-dgp2.procesinfrastructuur.nl` accepts ICP test submissions with free Logius test certificates.

---

## Existing Tools

### Open-source

The same Java libraries that handle VAT also handle ICP:

| Project                                                                               | ICP support |
|:--------------------------------------------------------------------------------------|:------------|
| [beemsoft/digipoort-microservice](https://github.com/beemsoft/digipoort-microservice) | Yes         |
| [beemsoft/sbr-nl-bd-taxonomy](https://github.com/beemsoft/sbr-nl-bd-taxonomy)         | Yes         |

**No Python library exists** for Digipoort ICP submission. Same building blocks apply (zeep, lxml, signxml).

### ERP Integrations

- **Exact Online** likely supports ICP filing natively via Digipoort
- **Microsoft Dynamics 365 Business Central** and **Dynamics AX** have built-in ICP submission
- **Odoo** community has discussed Digipoort integration

---

## Options

### Option A: Build Custom Digipoort Integration in Python

Since ICP uses the same Digipoort channel as VAT, building one means you get both. The incremental effort for ICP on top of a VAT integration is small — mainly the XBRL template and per-counterparty data mapping.

**Effort if VAT integration already built**: +1–2 weeks.
**Effort standalone**: Same as VAT (10–16 weeks) — the Digipoort plumbing is the hard part.

### Option B: Use Java Microservice as Sidecar

Same approach as VAT — the [beemsoft/digipoort-microservice](https://github.com/beemsoft/digipoort-microservice) supports both VAT and ICP.

**Effort**: 2–4 weeks (covers both VAT and ICP).

### Option C: Use Exact Online's Built-in ICP Filing

If the ICP data in Exact Online matches our computed figures (after correct VAT code configuration), Exact can submit ICP natively.

**Effort**: Near-zero — configuration only.
**Caveat**: Same as with VAT — requires trust that Exact's data matches our independent computation.

### Option D: Continue Using Tax Connection

Tax Connection is already used for ICP filing today. The question is whether they offer an API to push data programmatically instead of manual entry.

**Effort**: 1–2 weeks if API exists; status quo if not.

### Option E: Use a Third-Party Compliance Service

| Service                             | Description                                       |
|:------------------------------------|:--------------------------------------------------|
| Taxually (taxually.com)             | Global VAT compliance, handles NL ICP filing      |
| Marosa (marosavat.com)              | API-based VAT compliance, handles ESL/ICP         |
| Twinfield                           | Dutch accounting with Digipoort (~€53/month)      |

These services typically accept ICP data as JSON/CSV via API and handle XBRL generation + Digipoort submission.

**Effort**: 1–2 weeks integration. **Cost**: €100–500/month SaaS fee.

---

## Recommendation

**Option D (continue Tax Connection)** is the path of least resistance for now — it works, and ICP is filed quarterly. Investigate whether Tax Connection offers an API or bulk upload.

**Option C (Exact Online built-in)** becomes viable once the double accounting codes are configured and we trust the data in Exact matches our computations.

**If building a Digipoort integration for VAT (unlikely per the VAT PRD recommendation)**, add ICP support at the same time — it's marginal extra effort since the infrastructure is shared.

---

## Key Difference from VAT Submission

The ICP report has a **per-counterparty breakdown** (VAT number + country + amount), whereas the VAT return is aggregate boxes. This means the XBRL generation is slightly more complex — it needs to iterate over all EU customers with valid VAT numbers and emit one fact per counterparty. Our pipeline already produces this data.

---

## References

- [Belastingdienst — Opgaaf ICP](https://www.belastingdienst.nl/wps/wcm/connect/bldcontentnl/belastingdienst/zakelijk/btw/zakendoen_met_het_buitenland/goederen_en_diensten_naar_andere_eu_landen/opgaaf_icp/)
- [Belastingdienst — ICP Declaration (English)](https://www.belastingdienst.nl/wps/wcm/connect/bldcontenten/belastingdienst/business/vat/vat_in_the_netherlands/filing_vat_return_and_paying_vat/filing_a_vat_return/statement_of_intra_community_services/)
- [Microsoft Learn — Electronic VAT & ICP declarations NL](https://learn.microsoft.com/en-us/dynamics365/business-central/localfunctionality/netherlands/electronic-vat-and-icp-declarations)
- [Marosa — Dutch ESL/ICP](https://marosavat.com/manual/vat/netherlands/returns/esl/)
- [beemsoft/digipoort-microservice](https://github.com/beemsoft/digipoort-microservice)
- [Aansluit Suite Digipoort](https://aansluiten.procesinfrastructuur.nl/site/english)
