---
id: revenue_quality
name: "Revenue Quality Decomposition (D1-C)"
category: qualitative
tags: [d1, revenue, quality, ar]
data_needed: [income, balancesheet]
outputs:
  - field: core_revenue_share
    type: float
    desc: "Core recurring revenue as % of total revenue"
  - field: core_revenue_growth
    type: float
    desc: "YoY core revenue growth rate (%)"
  - field: headline_revenue_growth
    type: float
    desc: "YoY headline revenue growth rate (%)"
  - field: low_quality_items
    type: str
    desc: "List of identified low-quality revenue items with amounts"
  - field: collection_quality
    type: str
    desc: "Improving / Stable / Deteriorating"
  - field: ar_revenue_ratio_trend
    type: str
    desc: "Direction of AR/Revenue ratio over 5 years"
---

# D1-C: Revenue Quality Decomposition

Separate core earning power from noise.

## Analysis

1. **Revenue decomposition by segment/product**:
   - Identify which segments are **core recurring** vs **low-quality**
   - Low-quality items:
     - One-time gains, lawsuit settlements, government subsidies
     - Related-party revenue, asset disposals
     - Non-recurring licensing/milestone payments
     - Pandemic/stimulus windfalls
   - Watch for consolidation scope changes (acquisitions inflating revenue vs organic growth)

2. **Core revenue growth**:
   - Calculate core revenue growth rate (stripping low-quality items)
   - Compare to headline growth — divergence signals noise
   - If core growth << headline growth → noise is driving the number

3. **Segment-level margin analysis**:
   - Is high growth coming from low-margin segments ("watering down")?
   - Are high-margin segments growing or shrinking?

4. **Collection quality** (AR/Revenue ratio trend):
   - AR growing faster than revenue = collection quality deterioration
   - Calculate DSO (Days Sales Outstanding) trend if possible

```json
{
  "core_revenue_share": 92.5,
  "core_revenue_growth": 8.3,
  "headline_revenue_growth": 12.1,
  "low_quality_items": "FX translation gain $120M, one-time license fee $85M",
  "collection_quality": "Stable",
  "ar_revenue_ratio_trend": "Flat at ~12% over 5 years"
}
```
