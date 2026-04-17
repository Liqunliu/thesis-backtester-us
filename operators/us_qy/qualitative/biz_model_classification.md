---
id: biz_model_classification
name: "Business Model Classification (D1-F)"
category: qualitative
tags: [d1, business-model, classification]
data_needed: [income, balancesheet, cashflow]
outputs:
  - field: business_model_type
    type: str
    desc: "One of 7 types: light-asset-platform, light-asset-brand, capital-light-saas, capital-light-fintech, capital-hungry-manufacturing, capital-hungry-retail, leverage-dependent"
  - field: business_model_description
    type: str
    desc: "One-sentence description of the business model"
  - field: maint_capex_coefficient
    type: float
    desc: "Recommended maintenance CapEx coefficient for Owner Earnings calculation"
---

# D1-F: Business Model Classification

Based on D1-A through D1-D analysis, classify into one of these types:

| Type | Characteristics | CapEx Coeff | Examples |
|------|----------------|-------------|----------|
| light-asset-platform | Near-zero marginal cost, network effects | 0.7-0.8 | META, GOOGL, MSFT (cloud) |
| light-asset-brand | Premium pricing, brand moat | 0.8-1.0 | AAPL, NKE, COST |
| capital-light-saas | Subscription, high retention, <5% capex/rev | 0.7-0.9 | ADBE, CRM, INTU |
| capital-light-fintech | Transaction-based, low capex | 0.7-0.9 | V, MA, PYPL |
| capital-hungry-manufacturing | High capex/revenue ratio, cyclical | 1.0-1.3 | CAT, DE, GE |
| capital-hungry-retail | Inventory-heavy, store footprint | 1.0-1.2 | WMT, TGT, HD |
| leverage-dependent | Profits from interest spread | N/A | JPM, BAC, BRK |

## Instructions

1. Review prior operator outputs: `capital_intensity`, `payment_pattern`, `revenue_quality`, `profit_quality`
2. Select the most fitting type from the table above
3. Set `maint_capex_coefficient` — this value is used downstream by `owner_earnings_us` operator:
   - Light-asset (software/platform/brand): 0.7-1.0
   - Medium-asset (manufacturing/retail): 1.0-1.3
   - Heavy-asset (energy/utilities/mining): 1.2-1.8
4. Provide a one-sentence business model description

```json
{
  "business_model_type": "capital-light-saas",
  "business_model_description": "Enterprise SaaS platform with 95%+ renewal rate and <5% CapEx/Revenue",
  "maint_capex_coefficient": 0.8
}
```
