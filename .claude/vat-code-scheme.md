# VAT Code and Tax Treatment Algorithm

## Source of Truth
The primary algorithm for VAT codes and tax treatment is defined in **`docs/scheme/vat_code_scheme_temporary.md`**.

## VAT Code Format
VAT codes always contain **exactly two dashes** and can be split into three parts:

```
{category}-{geography}-{treatment}
```

### Examples
| VAT Code | Category | Geography | Treatment |
|----------|----------|-----------|-----------|
| FLT-NL-0 | FLT | NL | 0 |
| NFT-EU-RC | NFT | EU | RC |
| PUR-EX-RC | PUR | EX | RC |

### Codes Without Geography
For codes like FXE, PAS, REF where geography doesn't apply, the geography part is empty:
- `FXE--EXM`
- `PAS--OOS`
- `REF--OOS`

## Logic Derivation
When implementing or explaining VAT code assignment:

1. **Category**: Derived from the GL account
2. **Geography**: Derived from customer/supplier country
3. **Treatment**: Derived from the Category + Geography matrix (21%, 0%, RC, OOS, EXM)

Always consult `docs/scheme/vat_code_scheme_temporary.md` for the complete mapping logic.
