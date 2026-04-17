---
id: cyclicality_assessment
name: "Cyclicality & Regulatory Risk (D3)"
category: qualitative
tags: [d3, environment, cyclicality, regulatory]
data_needed: [income, balancesheet]
outputs:
  - field: cyclicality
    type: str
    desc: "strong-cycle / weak-cycle / non-cycle"
  - field: cycle_position
    type: str
    desc: "bottom / mid-cycle / top / N/A (if non-cycle)"
  - field: revenue_volatility_pct
    type: float
    desc: "Peak-to-trough revenue swing (%)"
  - field: regulatory_risk
    type: str
    desc: "Favorable / Neutral / Negative"
  - field: regulatory_details
    type: str
    desc: "Key regulatory concerns or 'None'"
---

# D3: External Environment

## D3-A: Cyclicality

1. **Revenue and profit volatility** over past 1-2 economic cycles:
   - > 30% peak-to-trough → strong-cycle
   - 10-30% → weak-cycle
   - < 10% → non-cycle

2. **External variable dependency**:
   - Commodity prices (energy, materials, agriculture)
   - Interest rates (financials, real estate, capital-intensive)
   - FX exposure (multinationals with concentrated revenue by region)
   - Transmission mechanism: how quickly do external changes flow to earnings?

3. **Cycle position** (if strong-cycle):
   - Bottom: margins depressed, capacity utilization low, capex cut
   - Mid-cycle: normalized margins, steady growth
   - Top: record margins, capacity expansion, aggressive acquisitions

## D3-B: Regulatory & Policy Risk (US-adapted)

| Risk Type | What to check |
|-----------|---------------|
| Antitrust | FTC/DOJ scrutiny or active investigations? |
| Sector regulation | FDA (pharma), FCC (telecom), EPA (energy), SEC (finance) |
| Tax policy | Exposure to corporate tax rate changes, OECD Pillar Two |
| Trade/tariffs | Supply chain exposure, export controls, geopolitical tensions |

Output: Favorable (regulation creates barriers) / Neutral / Negative (regulatory headwind)

```json
{
  "cyclicality": "weak-cycle",
  "cycle_position": "mid-cycle",
  "revenue_volatility_pct": 18.5,
  "regulatory_risk": "Neutral",
  "regulatory_details": "No active FTC investigation; moderate exposure to international tax reform"
}
```
