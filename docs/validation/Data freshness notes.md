# Data Freshness Notes

## Q3 2025 Data Comparison

When comparing the VAT pivot output against historical Excel files, expect small differences due to data timing.

### Example: Q3 2025

| Source | Filtered Transactions | Data Cutoff |
|--------|----------------------|-------------|
| Excel (Q3 2025 VAT declaration) | 94,927 | ~Oct 13, 2025 |
| CSV (20260129_transaction_lines_Q3.csv) | 94,994 | Jan 29, 2026 |
| **Difference** | **+67 transactions** | |

### Why Differences Occur

1. **Late journal entries**: Adjustments posted to Q3 after the original Excel was created
2. **Data warehouse refresh**: New extracts may capture transactions missed in earlier loads
3. **Corrections**: Transactions modified or added for reconciliation

### Load Date Distribution (Q3 CSV)

| Load Date | Transactions |
|-----------|--------------|
| 21/11/2025 | 94,960 |
| 12/12/2025 | 11 |
| 25/12/2025 | 22 |
| 26/01/2026 | 1 |

### Impact on VAT Boxes

Small differences in transaction counts lead to small amount differences:

| Box | Difference | Cause |
|-----|------------|-------|
| 1E | +721.65 | +23 transactions in GL 7212 |
| 4A/5B | +215.77 | Data timing |
| 4B/5B | -95.76 | Data timing |
| 5B | -13,443.46 | Data timing |

**Note:** Box 1A and 3B matched exactly after logic fixes were applied.
