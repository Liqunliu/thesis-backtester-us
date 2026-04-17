---
id: owner_earnings_us
name: "Owner Earnings — US Adjusted (F2 Step 1)"
category: quantitative
tags: [f2, owner-earnings, sbc, maintenance-capex]
data_needed: [income, cashflow, balancesheet]
gate:
  exclude_industry: [Banks, Insurance, Diversified Financial Services]
outputs:
  - field: owner_earnings
    type: float
    desc: "OE = Net Income + D&A - Maintenance CapEx ($M)"
  - field: owner_earnings_sbc_adj
    type: float
    desc: "OE adjusted for SBC ($M): OE - SBC (if SBC/NI > 20%)"
  - field: maint_capex
    type: float
    desc: "Estimated maintenance CapEx ($M)"
  - field: maint_capex_coeff
    type: float
    desc: "Coefficient used: D&A × coeff = maintenance CapEx"
  - field: sbc_material
    type: bool
    desc: "True if SBC/NI > 20%"
---

# F2 Step 1: Owner Earnings Calculation (US-Adjusted)

OE = Net Income + D&A − Maintenance CapEx

## Calculation

```
From income statement:
  Net Income (attributable) = [value] $M (C)
  US-specific: Stock-Based Compensation = [value] $M (SBC, from cashflow)
  Adjusted Net Income = C - SBC = [value] $M (C_adj)
  → Use C_adj if SBC/NI > 20%, otherwise use C

From cashflow:
  Depreciation & Amortization = [value] $M (D)
  Total Capital Expenditure = [value] $M (E)

CapEx/D&A ratio (5-year median) = [value]

Maintenance CapEx coefficient (from biz_model_classification):
  Light-asset: 0.7-1.0
  Medium-asset: 1.0-1.3
  Heavy-asset: 1.2-1.8
  Selected coefficient = [value] (G)

Maintenance CapEx = D × G = [value] $M (H)
Owner Earnings = C + D − H = [value] $M
Owner Earnings (SBC-adj) = C_adj + D − H = [value] $M
```

## Non-Cash One-Time Adjustment

If the most recent year contains significant non-cash one-time items
(goodwill impairment, restructuring charges, litigation settlements):
- Calculate both reported and adjusted OE
- Flag the adjustment

```json
{
  "owner_earnings": 4250.0,
  "owner_earnings_sbc_adj": 3800.0,
  "maint_capex": 1200.0,
  "maint_capex_coeff": 0.85,
  "sbc_material": true
}
```
