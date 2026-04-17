---
id: moat_quant_gate
name: "Moat Quantitative Gate (D2-2)"
category: qualitative
tags: [d2, moat, roe, gate]
data_needed: [income, balancesheet]
outputs:
  - field: roe_5yr_avg
    type: float
    desc: "5-year average ROE (%)"
  - field: roe_volatility
    type: float
    desc: "ROE standard deviation across years (pct)"
  - field: trough_net_margin
    type: float
    desc: "Lowest net margin in available data (%)"
  - field: moat_existence
    type: str
    desc: "Strong evidence / Moderate evidence / Questionable"
---

# D2-2: Moat Quantitative Gate

Verify moat existence with financial data BEFORE the qualitative deep dive.

## Gate Criteria

| Condition | Assessment |
|-----------|-----------|
| 5yr avg ROE > 15% AND SD < 5 pct | **Strong evidence** of moat |
| 5yr avg ROE 12-15% OR moderate volatility | **Moderate evidence** — moat possible |
| 5yr avg ROE < 12% AND no visible structural barrier | **Questionable** — needs strong qualitative support |

## Edge Cases

- **Negative equity** (buyback-driven, e.g., AAPL, MCD): ROE is meaningless.
  Use ROA or ROIC as substitute. Note the limitation.
- **Cyclical companies**: use mid-cycle ROE, not peak-year ROE.
- **Recent IPO / transformation**: < 5 years of data — note limited sample.

## Instructions

1. Calculate 5-year average ROE from income statement (Net Income / Shareholders' Equity)
2. Calculate standard deviation across the 5 years
3. Find the trough (lowest) net margin year
4. Apply the gate criteria above
5. If negative equity detected, switch to ROA and note it

```json
{
  "roe_5yr_avg": 18.5,
  "roe_volatility": 3.2,
  "trough_net_margin": 14.8,
  "moat_existence": "Strong evidence"
}
```
