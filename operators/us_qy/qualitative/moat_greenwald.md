---
id: moat_greenwald
name: "Moat Greenwald Three-Dimensional (D2-3b)"
category: qualitative
tags: [d2, moat, greenwald, cross-check]
data_needed: [income, balancesheet]
outputs:
  - field: greenwald_supply
    type: str
    desc: "Supply-side advantages: Strong / Moderate / Weak / N/A"
  - field: greenwald_demand
    type: str
    desc: "Demand-side advantages: Strong / Moderate / Weak / N/A"
  - field: greenwald_scale
    type: str
    desc: "Scale economy advantages: Strong / Moderate / Weak / N/A"
  - field: framework_agreement
    type: str
    desc: "Agree / Diverge — explanation"
  - field: primary_framework
    type: str
    desc: "Which framework better captures this company's dynamics"
---

# D2-3b: Greenwald Three-Dimensional Analysis

Complementary cross-check to Framework A. Surfaces moats the layered framework
underweights — especially local scale economies and demand-side habits.

## Three Dimensions

| Dimension | What to assess | Key evidence |
|-----------|---------------|-------------|
| **Supply-side** | Cost structure advantages, process IP, resource access | Unit cost vs competitors, proprietary processes, exclusive inputs |
| **Demand-side** | Customer habits, switching costs, search costs | Retention rates, customer lifetime value, brand lock-in |
| **Scale economy** | Fixed cost spreading, local vs global scale | Market share in served markets, minimum efficient scale |

Rate each: **Strong / Moderate / Weak / N/A**

## Reconciliation with Framework A

- If both frameworks agree → high confidence in moat rating
- If they diverge → investigate the source of disagreement
- State which framework better captures this company's competitive dynamics and why
- Primary: Framework A (Layer). Greenwald is the cross-check.

## When Greenwald adds value over Framework A

- **Local scale economies**: Framework A may rate "scale" as moderate globally, but Greenwald reveals dominance in specific markets/regions
- **Demand-side habits**: Framework A's "switching costs" may miss habitual usage patterns that aren't contractual
- **Cost advantage decomposition**: Greenwald separates supply-side (structural) from scale-driven cost advantages

```json
{
  "greenwald_supply": "Moderate",
  "greenwald_demand": "Strong",
  "greenwald_scale": "Strong",
  "framework_agreement": "Agree — both identify switching costs and scale as primary moat sources",
  "primary_framework": "Framework A (Layer) — better captures the technical moat dimension"
}
```
