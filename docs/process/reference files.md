`docs/samples` - past VAT submissions done by our previous financial controller in Excel. They may explain the logic of how raw transactions are turned into VAT and ICP reports.

`data/GL accounts classification.csv` - GL account groups exported from Exact Online.

`data/Acount ledger.csv` - GL account ledger exported from Exact Online.

`data/[timestamp]_invoicees_overview.csv` - Invoicees overview exported from Exact Online. Contains actual status of VAT check in column `vat_status`. It will be used to assign VAT code to transactions based on the vat_status and country (NL, EU or non-EU) of the invoicee.

Note about VAT validation statusses:
- **Unknown** is the default value and means that no validation has been performed yet. Should not be a case for production env.
- **Pending** means that validation is scheduled or in progress.
- **Valid** means that the VAT number has been validated and is valid.
- **Invalid** the VAT number has been validated and is invalid.
- **Error** the VAT number has been validated, but the service returned an exception. The next validation attempt is scheduled for the following day.
- **NotSupported** invoicee’s ‘No Vat’ is set to false, but the VAT number is not supported by the service for validation.
- **NotApplicable** invoicee’s  ‘No Vat’  is set to true.

`data/Coutnerparty country.csv` - Counterparty country export from Pigment. Explains which country belongs to Europe. This is used to create the ICP report and VAT report box 3b as explained in the [Pivot transactions to VAT and ICP](Pivot%20transactions%20to%20VAT%20and%20ICP.md) document.
