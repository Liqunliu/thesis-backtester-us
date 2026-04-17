---
id: sensitivity_cross_validation
name: "Sensitivity & Cross-Validation (F3 Step 13)"
category: quantitative
tags: [f3, sensitivity, credibility, cross-validation]
data_needed: [income, cashflow]
outputs:
  - field: lambda_sensitivity
    type: float
    desc: "Operating leverage (ΔOE/ΔRevenue elasticity)"
  - field: critical_revenue_multiplier
    type: float
    desc: "(Market Cap + Net Debt) / (OCF - Maint CapEx)"
  - field: extrapolation_credibility
    type: str
    desc: "HIGH / MEDIUM / LOW"
  - field: predictability
    type: str
    desc: "High / Moderate / Low"
  - field: coarse_refined_deviation
    type: float
    desc: "Coarse R minus Refined GG (percentage points)"
  - field: deviation_explanation
    type: str
    desc: "Explanation if deviation > 3pp"
---

# F3 Step 13: Sensitivity & Cross-Validation

How robust is the refined GG?

## Sensitivity Analysis

Test GG sensitivity to key assumptions:

| Assumption | Base | Bull (+) | Bear (-) | GG Impact |
|-----------|------|----------|----------|-----------|
| Maint CapEx coefficient | G | G-0.1 | G+0.1 | ±[X]pp |
| Non-recurring items | Include | Include | Exclude | ±[X]pp |
| Payout ratio | M_anchor | M+5% | M-5% | ±[X]pp |

## Cross-Validation

1. **Coarse vs Refined deviation**:
   - Coarse R (F2) vs Refined GG (F3)
   - If deviation > 3pp → investigate and explain
   - Common causes: accrual distortion, non-recurring items, SBC adjustment

2. **Script GG vs Agent GG**:
   - Compare with pre-computed GG from `gg_quick` factor
   - Divergence suggests manual calculation caught something the script missed

## Credibility Assessment

| Level | Criteria |
|-------|---------|
| HIGH | Stable OCF, predictable CapEx, consistent collection, deviation < 2pp |
| MEDIUM | Some volatility but directionally consistent |
| LOW | Volatile OCF, unpredictable CapEx, high non-recurring, deviation > 3pp |

## Predictability

Can we confidently extrapolate this GG forward?
- High: business model proven, stable competitive position, >5yr track record
- Moderate: some uncertainty but bounded
- Low: material structural changes underway, limited history

```json
{
  "lambda_sensitivity": 1.35,
  "critical_revenue_multiplier": 8.2,
  "extrapolation_credibility": "MEDIUM",
  "predictability": "Moderate",
  "coarse_refined_deviation": 1.8,
  "deviation_explanation": "Within acceptable range — SBC adjustment accounts for 1.2pp"
}
```
