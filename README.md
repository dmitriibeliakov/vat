## VAT & ICP Reporting Toolkit

This project is a **local toolkit** to turn raw accounting transactions exported from Redshift into **Dutch VAT (BTW) and ICP (Opgaaf ICP) reports**.  
It automates the logic that is currently done manually in Excel, using a combination of:
- **Raw transaction exports** from Redshift
- **Lookup CSVs** maintained in this repo
- **Excel VAT/ICP templates** as reference for the final reports

The goal is that for a given **quarter and year**, you can drop in the raw data, run the app, and obtain:
- A **pivoted transaction dataset** with a clear **VAT code** per transaction
- An **aggregated VAT report** aligned with the Belastingdienst online form
- An **aggregated ICP report** whose total matches VAT Box 3b

---

## Running the VAT code assignment app

The app in `app/` reads a transaction lines CSV, assigns GL category and counterparty geography, and writes four temporary CSVs under `tmp/`. See [docs/PRD VAT code assignment script.md](docs/PRD%20VAT%20code%20assignment%20script.md) for the full spec.

**Prerequisites:** Python 3.9+, `pandas`. Install with: `pip install -r requirements.txt`

**Command:**

```bash
python -m app.main <path/to/transaction_lines.csv>
```

**Options:**

- `--data-dir DIR` — Data directory containing lookup CSVs (default: `data`)
- `--tmp-dir DIR` — Output directory for temporary CSVs (default: `tmp`)

**Example:**

```bash
python -m app.main 20260129_transaction_lines_Q4.csv
```

**Required files in `data/`:** `gl_category_lookup.csv`, `20260129_invoicees_overview.csv` (or equivalent), `Coutnerparty country.csv`. Every transaction’s `account_code` (trimmed) must exist in the invoicees overview; otherwise the script raises an error and stops.

**Outputs in `tmp/`:** `gl_accounts_with_category.csv`, `gl_accounts_no_category.csv`, `counterparties_geography.csv`, `transactions_with_vat_code.csv`.

---

## Repository structure

- `20260129_transaction_lines_Q4.csv`  
  Example **raw transactions export** from Redshift for a specific quarter. In production, the user will periodically export similar files and place them in this repo.

- `data/`  
  Lookup and master-data CSVs used to enrich and classify transactions:
  - `GL accounts classification.csv` – Tree-like GL grouping from Exact Online.
  - `Acount ledger.csv` – Canonical GL account ledger from Exact Online.
  - `20260129_invoicees_overview.csv` – Invoicees overview from Exact Online, including `vat_status` and country; used to determine B2B/B2C and VAT validity.
  - `Coutnerparty country.csv` – Country → “EU / non‑EU / NL” mapping from Pigment; used for VAT Box 3b and ICP classification.

- `docs/`  
  Project documentation:
  - `How to file VAT and ICP manually.md` – Step‑by‑step description of the current **manual** Excel-based process.
  - `Pivot transactions to VAT and ICP.md` – Conceptual mapping of raw transactions to **VAT codes** and then to **VAT/ICP report boxes**; this is the primary rules spec for the app.
  - `reference files.md` – Describes the lookup files in `data/` and how they are used.
  - `docs/samples/*.xlsx` – Historical VAT/ICP Excel files prepared by the previous financial controller. They define:
    - The **final layout** of the VAT return (boxes 1–5 as in Belastingdienst)
    - The **final layout** of the ICP report (per‑customer VAT breakdown)
    - Example pivot tables/logic for turning transaction lines into report lines.

---

## High‑level design

The app will **not** connect directly to Exact Online or Redshift. Instead it assumes:

1. **Raw transactions** are exported from Redshift into a CSV and placed in the repo (e.g. `20260129_transaction_lines_Q4.csv`).  
   - These rows correspond to `"mongo_cteleport_exact_service"."transaction_lines"` in Redshift.  
   - Filtering by VAT reporting period is done via `financial_year` and `financial_period` (see `.cursor/rules/retreive-vat-transactions.mdc`).

2. **Lookup tables** are maintained as CSV files under `data/` and refreshed manually from:
   - Exact Online exports (GL ledger, GL classifications, invoicees overview)
   - Pigment export for country / EU classification

3. The app reads:
   - The **raw transaction CSV**
   - The **lookup tables**
   and produces internal tables that can then be pivoted into:
   - A **VAT table** (grouped by VAT report box and VAT code)
   - An **ICP table** (grouped by customer VAT ID and country, for EU B2B only)

4. The final numbers are filled into the **VAT** and **ICP** forms, following the layout in `docs/samples/*.xlsx`. In the future this may be automated using the Excel templates directly.

---

## Core workflow

From a user perspective, the standard quarterly flow looks like this:

1. **Export transactions from Redshift**  
   - In Redshift, query `"mongo_cteleport_exact_service"."transaction_lines"` for the desired **financial year** and **quarter** (mapped to `financial_period` months as described in `.cursor/rules/retreive-vat-transactions.mdc`).  
   - Save the result as a CSV (e.g. `YYYYMMDD_transaction_lines_Q{N}.csv`) into the project root.

2. **Refresh lookup CSVs (if needed)**  
   - Update the files in `data/` from their source systems following `docs/process/reference files.md`:
     - GL ledger and GL classification from Exact Online (`Master data` → `Import/Export`).
     - Invoicees overview from Exact Online (includes `vat_status` values like `Valid`, `Invalid`, `NotApplicable`, etc.).
     - Counterparty country list from Pigment, used to decide whether a transaction is NL, EU, or non‑EU.

3. **Assign VAT codes to each transaction**  
   For every transaction row, the app enriches and classifies it using:
   - **Country** (NL vs EU vs non‑EU) from `Coutnerparty country.csv`.
   - **Customer VAT type** from `2026…_invoicees_overview.csv`:
     - B2B with valid VAT number
     - B2B with invalid/unknown VAT number
     - B2C / No VAT / Not applicable
   - **Product type** (goods vs services – in this business, only services are sold).
   - **GL account group** from `GL accounts classification.csv` + `Acount ledger.csv`.

   Based on the rules documented in `Pivot transactions to VAT and ICP.md`, the app assigns a **VAT code** that:
   - Encodes the reporting destination (e.g. NL 21% in 1a, EU B2B services in 3b, exports, reverse charge purchases, etc.).
   - Indicates whether the transaction belongs in the **VAT report**, the **ICP report**, or both.

4. **Create a pivoted VAT/ICP dataset**  
   After VAT codes are assigned, the enriched transaction table includes at least:
   - Country code
   - Product type (services only)
   - Customer VAT type
   - VAT code
   - Amount (and possibly VAT amount)
   - GL account and derived GL group

   This dataset plays the same role as the manually built pivot tables described in:
   - `How to file VAT and ICP manually.md`
   - `Pivot transactions to VAT and ICP.md`

5. **Generate the ICP report**  
   - Filter transactions to those that belong to **ICP** (typically EU B2B services, VAT code like “EU_B2B” as per the rules).  
   - Group by:
     - Customer VAT ID
     - Customer country
   - Sum the taxable **revenue** amount per customer and per country.  
   - Output a table in the same structure as the ICP sample in `docs/samples/*.xlsx`.  
   - The **total of this table must equal VAT Box 3b** in the VAT report.

6. **Generate the VAT report**  
   - Filter/aggregate the remaining transactions by **VAT box** and **VAT code**, following the mapping rules:
     - Rubriek 1 (domestic performance) – boxes 1a, 1b, 1c, 1d, 1e
     - Rubriek 2 (domestic reverse charge)
     - Rubriek 3 (transactions to abroad) – boxes 3a, 3b, 3c
     - Rubriek 4 (transactions from abroad) – boxes 4a, 4b
     - Rubriek 5 (calculation and input tax) – boxes 5a–5g
   - Sum the amounts per box (and VAT amounts where relevant) and output a table whose structure matches the VAT samples in `docs/samples/*.xlsx`.
   - As a consistency check, ensure that:
     - **Box 3b total** equals the **sum of the ICP report**.
     - Reverse‑charge VAT reported in 4a/4b is also reflected correctly in 5b (input tax).

---

## Relationship between VAT and ICP in this project

- The **VAT report** is the **summary** view required by the Belastingdienst portal.  
- The **ICP report** is the **detail breakdown** of EU B2B sales that justifies Box 3b:
  - VAT is 0% but must still be reported.
  - The app ensures that the **sum of all ICP lines equals VAT Box 3b**.

In the current manual flow (see `How to file VAT and ICP manually.md`), this is done by building multiple pivot tables in Excel.  
This project’s purpose is to **formalize that logic in code** so that quarterly submissions are reproducible, less error‑prone, and easier to audit.

---

## Future implementation notes

This README describes the **functional design** and data flow, not a fixed tech stack.  
The implementation can be in Python, SQL+CLI, or another language, but should:

- Treat the raw **Redshift export** and **lookup CSVs** as the **sole inputs** (no direct DB calls from the app).
- Produce:
  - A **classified transactions table** with VAT codes.
  - **Aggregated VAT and ICP tables** suitable for:
    - Direct export to CSV / Excel, or
    - Filling into the provided Excel samples / online forms.
- Include automated checks that:
  - VAT Box 3b equals the total ICP revenue.
  - Basic sanity checks per GL group / VAT code (optional but recommended).

As the project evolves, this README can be extended with:
- Exact command‑line usage or UI instructions.
- Detailed VAT code catalog and mapping table (VAT code → VAT box + ICP flag).
- Links to any unit/integration tests that validate report totals against the sample Excel files.

