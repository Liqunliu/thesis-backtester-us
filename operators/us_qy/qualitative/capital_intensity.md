---
id: capital_intensity
name: "Capital Intensity (D1-A)"
category: qualitative
tags: [d1, business-model, capex]
data_needed: [income, cashflow, balancesheet]
outputs:
  - field: capital_intensity
    type: str
    desc: "capital-light or capital-hungry"
  - field: capex_revenue_ratio
    type: float
    desc: "CapEx / Revenue ratio (latest year, %)"
  - field: capex_da_ratio
    type: float
    desc: "CapEx / D&A ratio (5-year median)"
  - field: capital_intensity_evidence
    type: str
    desc: "One-sentence evidence for classification"
---

# D1-A: Capital Intensity

Assess how much reinvestment the business needs to maintain current earnings.

## Analysis

1. **CapEx / Revenue ratio** (5-year trend):
   - < 5%: capital-light
   - 5-15%: moderate
   - > 15%: capital-hungry

2. **CapEx / D&A ratio** (5-year median):
   - < 0.8: underinvesting (harvesting mode)
   - 0.8-1.5: maintaining
   - > 1.5: expanding capacity

3. **Capital investment time structure**:
   - One-time long-term benefit (e.g., build a platform once) → favorable
   - Recurring each period (e.g., constant fleet replacement) → unfavorable

4. **Criterion**: "sustained capital consumed per unit of earnings maintained"

## Output

Classify as `capital-light` or `capital-hungry` with evidence.

```json
{
  "capital_intensity": "capital-light",
  "capex_revenue_ratio": 4.2,
  "capex_da_ratio": 0.95,
  "capital_intensity_evidence": "CapEx/Revenue consistently <5%, platform model with one-time build costs"
}
```
