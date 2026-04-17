---
id: gaap_audit
name: "US GAAP Audit (F3 Step 10)"
category: quantitative
tags: [f3, gaap, audit, contingent-liabilities, asc606]
data_needed: [income, balancesheet, cashflow]
outputs:
  - field: gaap_adjustments
    type: str
    desc: "List of identified GAAP distortions or 'None'"
  - field: contingent_liabilities
    type: float
    desc: "Material contingent liabilities to deduct from AA ($M, 0 if none)"
  - field: gaap_quality
    type: str
    desc: "Clean / Minor adjustments / Material distortion"
---

# F3 Step 10: US GAAP Audit

Detect accounting distortions that inflate or deflate reported earnings.

## Checks

1. **Revenue recognition aggressiveness** (ASC 606):
   - Bill-and-hold arrangements
   - Multiple performance obligations
   - Variable consideration estimates
   - Comparison of revenue recognition timing vs cash collection

2. **R&D capitalization**:
   - Is R&D capitalization rate increasing? (shifting expense to balance sheet)
   - Software development costs capitalized (ASC 350-40)

3. **Depreciation policy**:
   - Unusual useful life assumptions?
   - Recent policy changes that reduce expense?

4. **Stock-based compensation**:
   - How is SBC treated in "adjusted" metrics?
   - Mark-to-market on equity awards?

5. **Goodwill impairment timing**:
   - Overdue impairment testing?
   - Goodwill/Equity ratio (>100% = fragile book value)

6. **Contingent liabilities** (from 10-K footnotes if available):
   - Litigation reserves
   - Guarantees
   - Environmental obligations
   - Off-balance-sheet arrangements
   - If material: deduct from AA in refined_return_aa operator

7. **Operating vs finance lease classification** (ASC 842):
   - Does classification understate leverage?

## Output

```json
{
  "gaap_adjustments": "None",
  "contingent_liabilities": 0,
  "gaap_quality": "Clean"
}
```
