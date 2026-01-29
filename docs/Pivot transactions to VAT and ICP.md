VAT and ICP reports are linked, but they serve different purposes. Think of the **VAT Report** as your "Summary" and the **ICP Report** as your "Evidence for EU Sales."

---

# VAT sections

To ensure compliance with Dutch law (*Belastingwetgeving*), the VAT return (**BTW-aangifte**) must follow the official structure set by the Dutch Tax Authority (*Belastingdienst*). The return is strictly divided into **5 Rubrieken (Categories)**:

### 1. Rubriek 1: Domestic Performance (*Prestaties binnenland*)

This is where you report sales made to customers **within the Netherlands**.

* **1a (High rate):** Turnover and VAT for the standard **21%** rate.
* **1b (Low rate):** Turnover and VAT for the **9%** rate (e.g., food, books). *Note: From Jan 1, 2026, most accommodation/hotels are now 21%, while camping remains 9%.*
* **1c (Other rates):** Special rates (e.g., the 13% flat rate for sports canteens).
* **1d (Private use):** VAT owed on business assets used for private purposes (e.g., a company car).
* **1e (0% rate):** Sales that are not taxed or where the VAT is shifted to the buyer within NL.

### 2. Rubriek 2: Domestic Reverse Charge (*Verleggingsregelingen*)

Use this if another Dutch entrepreneur has **shifted the VAT to you**.

* You calculate the VAT yourself and report it here, but you typically deduct the same amount in Section 5b, making the net effect zero.

### 3. Rubriek 4: Transactions from Abroad (*Prestaties vanuit het buitenland*)

This is for goods or services **you purchased** from suppliers outside the Netherlands.

* **4a (Non-EU):** Imports from outside the European Union.
* **4b (EU):** Purchases from other EU member states (*Intracommunautaire verwervingen*).

### 4. Rubriek 3: Transactions to Abroad (*Prestaties naar het buitenland*)

This is for goods or services **you sold** to customers outside the Netherlands.

* **3a (EU):** Sales to businesses in other EU countries (0% VAT applies, but must be reported here).
* **3b (Non-EU):** Exports to countries outside the EU (0% VAT).
* **3c (Installation/Distance sales):** Specialized sales involving installation abroad.

### 5. Rubriek 5: Calculation and Input Tax (*Berekening en Voorbelasting*)

The final calculation to determine if you pay or receive money.

* **5a (Total VAT):** The sum of all VAT reported in Sections 1 through 4.
* **5b (Input Tax / *Voorbelasting*):** The VAT **you paid** on business expenses and purchases that you are entitled to claim back.
* **5c (Subtotal):** 5a minus 5b.
* **5d (KOR):** Reduction for the Small Business Scheme (*Kleineondernemersregeling*), if applicable.
* **5g (Final Total):** The final amount to be paid or refunded.

---

## VAT vs. ICP: The Relationship

While it’s common to think of the ICP as "part" of the VAT report, it is technically a separate filing. However, **the totals must match.**

* **VAT Report (Section 3b):** You report the total revenue from goods and services delivered to businesses in other EU countries. You don't list customer names here—just one big number.
* **ICP Report (Opgaaf ICP):** You provide the **breakdown** of that 3b number. You list the VAT number of every EU customer and the specific amount you billed each one.

---

## 2. Mapping Transactions in Accounting

You need to assign a **VAT Code** to every transaction. A good VAT code isn't just a percentage; it's a "Route" that tells the system where to put the money.

### The Classification Logic

After you read the raw transactions file, we need to assign codes to each transaction, each transaction should have these attributes:

1. **Country Code:** (NL, DE, FR, US, etc.)
2. **Product Type:** (Goods vs. Services - mind that our company never sells goods, only services)
3. **Customer VAT Type:** (B2B with valid VAT number vs. B2C/Private)
4. **VAT Code:** The "Master Key" that maps to the reports.

---

## 3. Creating the pivot tables that result into VAT and ICP reports



1. **For the VAT Report:** Filter your Pivot Table by **VAT Code** or **Report Category**. Sum the "Amount" column. This gives you the totals for Box 3b, 1a, etc.
2. **For the ICP Report:** Filter the Pivot Table for **VAT Code = EU_B2B**. Put **Customer VAT ID** in the "Rows" and **Amount** in the "Values."

---

## 4. Pro-Tips for Accuracy

* **The VIES Check:** For the ICP report to be valid, you **must** verify that your customer's VAT number is active in the VIES (EU VAT system). If it's invalid, you technically cannot use the 0% "Reverse Charge" (Box 3b) and must charge Dutch VAT instead.
* **Goods vs. Services:** On the ICP report, these are often separated (Goods = *Leveringen*, Services = *Diensten*). Ensure your VAT codes distinguish between the two.
* **Reverse Charge Purchases:** Don't forget that if *you* buy something from the EU (e.g., Google Ads from Ireland), that goes in **Box 4b**, but it does **not** go on the ICP report (since that's only for sales).

Would you like me to create a sample CSV structure or an Excel formula logic that you can copy-paste into your workbook?