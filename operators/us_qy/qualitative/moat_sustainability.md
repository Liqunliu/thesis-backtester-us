---
id: moat_sustainability
name: "Moat Sustainability & Monitoring (D2-6)"
category: qualitative
tags: [d2, moat, sustainability, kpi, erosion]
data_needed: [income, balancesheet]
outputs:
  - field: moat_rating
    type: str
    desc: "WIDE / NARROW / NONE"
  - field: pricing_power
    type: str
    desc: "Strong / Moderate / Weak / None"
  - field: human_capital_type
    type: str
    desc: "System-type (codified, favorable) / Talent-type (key-person risk)"
  - field: moat_sustainability
    type: str
    desc: "Durable / At risk / Eroding"
  - field: moat_erosion_vectors
    type: str
    desc: "Top 2-3 threats with estimated timeline"
  - field: moat_monitor_kpis
    type: str
    desc: "3 KPIs with current value and warning threshold"
---

# D2-6: Moat Sustainability & Monitoring

Final moat assessment integrating D2-2 through D2-5.

## Pricing Power Evidence

- Track record of price increases in past 3-5 years? (with examples)
- Customer churn or retention data (if available)

## Supply Chain Position

- Bargaining power vs upstream suppliers: Strong / Balanced / Weak
- Bargaining power vs downstream customers: Strong / Balanced / Weak

## Moat Erosion Vectors

Identify top 2-3 specific threats:
1. [Threat] — estimated timeline: [X years]
2. [Threat] — estimated timeline: [X years]
3. [Threat] — estimated timeline: [X years]

## Human Capital Dependency

- **System-type**: Competitive advantage codified into processes, IP, platforms (favorable)
- **Talent-type**: Advantage depends on key individuals (unfavorable — key-person risk)

## Moat Monitoring KPIs

3 concrete, measurable indicators:

| KPI | Current Value | Warning Threshold | Rationale |
|-----|--------------|-------------------|-----------|
| [KPI 1] | [value] | [warn if crosses X] | [why] |
| [KPI 2] | [value] | [warn if crosses X] | [why] |
| [KPI 3] | [value] | [warn if crosses X] | [why] |

## Final Moat Rating

Synthesize D2-2 (quantitative gate) + D2-3 (frameworks) + D2-4 (false advantages) + D2-5 (competitors):
- **WIDE**: Strong quantitative evidence + multiple durable moat sources + no false advantages
- **NARROW**: Moderate evidence + 1-2 moat sources + manageable erosion vectors
- **NONE**: Questionable evidence OR confirmed false advantages OR rapid erosion

```json
{
  "moat_rating": "NARROW",
  "pricing_power": "Moderate",
  "human_capital_type": "System-type",
  "moat_sustainability": "Durable",
  "moat_erosion_vectors": "1. AI disruption to core product (3-5 years), 2. Regulatory pressure on data usage (2-3 years)",
  "moat_monitor_kpis": "Net revenue retention >110% (current: 115%), Gross margin >70% (current: 74%), R&D/Revenue >15% (current: 18%)"
}
```
