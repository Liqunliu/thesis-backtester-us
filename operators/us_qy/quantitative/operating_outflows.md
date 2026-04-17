---
id: operating_outflows
name: "Operating Outflows & CapEx Decomposition (F3 Steps 8-9)"
category: quantitative
tags: [f3, operating-outflows, capex, maintenance, growth]
data_needed: [income, cashflow, balancesheet]
outputs:
  - field: total_operating_outflows
    type: float
    desc: "Total operating cash outflows ($M)"
  - field: capex_total
    type: float
    desc: "Total CapEx ($M)"
  - field: capex_maintenance
    type: float
    desc: "Estimated maintenance CapEx ($M)"
  - field: capex_growth
    type: float
    desc: "Estimated growth CapEx ($M)"
  - field: capex_da_ratio
    type: float
    desc: "CapEx / D&A ratio (>1.5 expanding, <0.8 underinvesting)"
  - field: free_cash_flow_reconstructed
    type: float
    desc: "OCF - Total CapEx ($M)"
---

# F3 Steps 8-9: Operating Outflows & CapEx Decomposition

## Step 8: Operating Outflows Reconstruction

Trace line-by-line from cash flow statement:
- Payments to employees (from SG&A or disclosed separately)
- Payments for materials/supplies (COGS + inventory change)
- Income tax paid
- Interest paid

Conservative decomposition of each. Identify any unusual items.

## Step 9: CapEx & Investment

1. **Total CapEx** from cashflow

2. **Maintenance vs Growth split**:
   - CapEx/D&A ratio: >1.5 = expanding capacity, <0.8 = underinvesting
   - Maintenance CapEx ≈ D&A × coefficient (from biz_model_classification)
   - Growth CapEx = Total CapEx − Maintenance CapEx

3. **ROU asset changes** (US-specific, ASC 842):
   - Operating lease right-of-use assets affect total capital commitment
   - Note but don't add to CapEx unless material

4. **Free Cash Flow** = OCF − Total CapEx

```json
{
  "total_operating_outflows": 28500.0,
  "capex_total": 3200.0,
  "capex_maintenance": 2100.0,
  "capex_growth": 1100.0,
  "capex_da_ratio": 1.15,
  "free_cash_flow_reconstructed": 8800.0
}
```
