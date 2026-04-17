---
id: profit_quality
name: "Profit Quality Decomposition (D1-D)"
category: qualitative
tags: [d1, profit, quality, manipulation]
data_needed: [income, balancesheet, cashflow]
outputs:
  - field: core_oper_profit_growth
    type: float
    desc: "YoY core operating profit growth (%)"
  - field: non_operational_pct
    type: float
    desc: "Non-operating income as % of pre-tax profit"
  - field: non_operational_warning
    type: bool
    desc: "True if non-operational contribution > 15%"
  - field: expense_manipulation_signals
    type: str
    desc: "List of concerns or 'None'"
  - field: profit_quality
    type: str
    desc: "HIGH / MODERATE / LOW"
---

# D1-D: Profit Quality Decomposition

Is the core business truly improving or riding non-operational tailwinds?

## Analysis

1. **Profit growth driver decomposition**:
   - Gross margin change (pricing power vs input costs)
   - SGA/R&D/admin expense rate changes (efficiency vs cutting for short-term)
   - Non-operating items: FX gains/losses, investment income, asset disposal gains, grants

2. **Non-operational profit contribution**:
   - Calculate: (non-operating income / total pre-tax profit)
   - If > 15% → **WARNING**: core operating profit may be weaker than reported
   - Key test: if non-operational contribution exceeds reported profit growth, core is declining

3. **Hidden expense manipulation checks**:
   - R&D capitalization rate increasing? (shifting R&D from expense to balance sheet)
   - SGA cuts while revenue grows? (sacrificing future growth for short-term margins)
   - Unusual depreciation policy changes?
   - US-specific: SBC expense recognized but excluded from "adjusted" metrics

4. **Core operating profit growth**:
   - Strip: non-recurring items, FX, grants, disposal gains
   - Compare to headline profit growth

## Debt & Profit Source Checks (D1-E, conditional)

Expand only if data flags warrant:

- **Debt check** (if interest-bearing debt / total assets > 20%):
  - Interest coverage: EBITDA / interest expense > 3x?
  - Cash coverage: (cash + ST investments) / total debt > 1.0?
  - Distinguish operating leverage (high fixed assets, low debt) from financial risk (high debt, weak cash flow)

- **Profit source check** (if investment income / pre-tax profit > 20%):
  - Flag "investment-income-dependent"
  - Check cash backing of investment income

```json
{
  "core_oper_profit_growth": 6.2,
  "non_operational_pct": 8.5,
  "non_operational_warning": false,
  "expense_manipulation_signals": "None",
  "profit_quality": "HIGH"
}
```
