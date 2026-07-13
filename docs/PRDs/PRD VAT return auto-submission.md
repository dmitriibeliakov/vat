# PRD: Automated VAT Return Submission

## Problem

C Teleport BV currently files Dutch VAT returns (BTW-aangifte, form OB 400E) manually through the Belastingdienst web portal "Mijn Belastingdienst Zakelijk". This project already automates **data preparation** — computing VAT amounts per box from Exact Online transaction data. The remaining manual step is the actual submission.

## Goal

Evaluate feasibility and recommend an approach for programmatically submitting the quarterly VAT return to the Belastingdienst.

---

## How Dutch VAT Filing Works Electronically

### The SBR/Digipoort Stack

The Belastingdienst does **not** offer a modern REST API. All machine-to-machine tax filings go through **Digipoort**, a secure government gateway operated by Logius.

| Layer              | Standard                                                             |
|:-------------------|:---------------------------------------------------------------------|
| Data format        | **XBRL** (eXtensible Business Reporting Language)                    |
| Taxonomy           | **Dutch Taxonomy (NT)** — updated annually by SBR-NL                 |
| Transport          | **SOAP 1.1/1.2** via WUS (Web Utility Services)                     |
| Message signing    | **WS-Security** with PKIoverheid certificates                       |
| Governance         | Managed by **SBR-NL** (sbr-nl.nl) and **Logius** (logius.nl)        |

### Submission Flow

1. Generate an **XBRL instance document** conforming to the Dutch Taxonomy for OB declarations
2. Wrap it in a **SOAP envelope** signed with a PKIoverheid certificate
3. Submit via the Digipoort **Aanleverservice** endpoint
4. Poll the **Statusinformatieservice** for processing status (accepted/rejected/error)

### XBRL Content

The VAT return XBRL contains:

- Entity identifier: RSIN
- Reporting period (quarter)
- Amounts per box (1A, 1B, 1E, 2A, 3A, 3B, 4A, 4B, 5B, 5D, 5E, 5F, 5G)
- Corresponding tax amounts
- Currency: EUR

### Authentication: PKIoverheid Certificates

| Certificate        | Purpose                                           | Source                                                |
|:-------------------|:--------------------------------------------------|:------------------------------------------------------|
| Private (company)  | Signs SOAP messages, identifies the company       | Purchase from CSP (KPN, DigiCert, QuoVadis) ~€600/3yr |
| Public (Digipoort) | Encrypts messages, verifies Digipoort's identity  | Download from Belastingdienst                         |

Requires face-to-face identity verification of the certificate manager. Cannot be self-signed.

### Test Environment

A **preproduction environment** exists:

- **Aansluit Suite Digipoort**: https://aansluiten.procesinfrastructuur.nl/site/english
- **Free Logius test certificate**: request via servicecentrum@logius.nl
- **ODB Belastingdienst**: https://odb.belastingdienst.nl — developer test facilities

---

## Existing Tools and Libraries

### Open-source (not Python)

| Project                                                                              | Language | What it does                                         |
|:-------------------------------------------------------------------------------------|:---------|:-----------------------------------------------------|
| [OpenSBR/DigipoortWusConnection](https://github.com/OpenSBR/DigipoortWusConnection) | C# .NET  | Reference implementation for Digipoort WUS           |
| [beemsoft/digipoort-microservice](https://github.com/beemsoft/digipoort-microservice)| Java     | Spring Boot microservice for XBRL + Digipoort        |
| [beemsoft/techytax-xbrl](https://github.com/beemsoft/techytax-xbrl)                 | Java     | Full tax app including XBRL generation and filing     |

### Python building blocks (no turnkey solution exists)

| Library        | Purpose                                       |
|:---------------|:----------------------------------------------|
| Arelle         | XBRL validation and rendering                 |
| python-zeep    | SOAP client for calling WUS endpoints         |
| lxml           | XML generation for building XBRL instances    |
| signxml/xmlsec | WS-Security signing                           |

---

## Options

### Option A: Build Custom Digipoort Integration in Python

| Phase                            | Effort         |
|:---------------------------------|:---------------|
| Certificate procurement          | 2–4 weeks      |
| Learn SBR/XBRL/Dutch Taxonomy   | 2–3 weeks      |
| Build XBRL instance generator    | 2–3 weeks      |
| Build SOAP/WUS client + signing  | 2–3 weeks      |
| Testing in Aansluit Suite        | 1–2 weeks      |
| Production validation            | 1 week         |
| **Total**                        | **10–16 weeks** |

**Ongoing cost**: Annual taxonomy updates, certificate renewal every 2–3 years.
**Risk**: No existing Python reference implementation. Python's WS-Security/SOAP ecosystem is less mature than Java/.NET for this use case.

### Option B: Use Java Microservice as Sidecar

Deploy the [beemsoft/digipoort-microservice](https://github.com/beemsoft/digipoort-microservice) as an HTTP service. Python pipeline generates VAT data → calls the Java service → it handles XBRL + Digipoort.

**Effort**: 2–4 weeks. **Risk**: Java dependency; library may target older taxonomy version.

### Option C: Use Exact Online's Built-in SBR Filing

Exact Online has native Digipoort/SBR integration. If VAT codes in Exact are correctly configured (which this project is moving towards), Exact can submit directly.

**Effort**: Near-zero development — configuration only.
**Caveat**: Requires that the VAT amounts in Exact match our independently computed figures. The double accounting scheme (see [exact_vat_codes.md](../exact_vat_codes.md)) is designed to make this possible.

### Option D: Use a Third-Party Compliance Service

| Service                    | Type                | Notes                                        |
|:---------------------------|:--------------------|:---------------------------------------------|
| Tax Connection             | Filing portal       | Already used for ICP; may support OB too      |
| Taxually (taxually.com)    | VAT compliance SaaS | Multi-country VAT filings                    |
| Anrok (anrok.com)          | Tax automation SaaS | Registration + filing + reporting            |
| Twinfield                  | Accounting + filing | Has Digipoort built in (~€53/month)          |

**Effort**: 1–3 weeks integration. **Cost**: Monthly SaaS fee (typically €100–500/month).

---

## Recommendation

**Option C (Exact Online built-in filing)** is the pragmatic choice. The bottleneck has always been correct VAT code assignment, not the submission step itself (which takes minutes manually). This project already solves the hard part — once the double accounting codes are configured in Exact, its native SBR filing handles submission.

**If full end-to-end automation is desired later**, Option D (third-party service, e.g. extending the existing Tax Connection relationship) offers the best effort-to-value ratio. Building a custom Digipoort integration (Option A) is only justified if filing volume or auditability requirements demand it.

---

## References

- [Belastingdienst — Filing using accounting software](https://www.belastingdienst.nl/wps/wcm/connect/bldcontenten/belastingdienst/business/tax_return/filing_digital_tax_returns/filing-tax-returns-using-accounting-software/)
- [Aansluit Suite Digipoort](https://aansluiten.procesinfrastructuur.nl/site/english)
- [ODB Belastingdienst — Test facilities](https://odb.belastingdienst.nl)
- [OpenSBR — DigipoortWusConnection](https://github.com/OpenSBR/DigipoortWusConnection)
- [beemsoft/digipoort-microservice](https://github.com/beemsoft/digipoort-microservice)
- [SBR-NL](https://www.sbr-nl.nl)
- [Arelle XBRL Platform](https://arelle.org/)
