---
id: payment_pattern
name: "Payment Pattern (D1-B)"
category: qualitative
tags: [d1, business-model, working-capital]
data_needed: [income, balancesheet, cashflow]
outputs:
  - field: payment_pattern
    type: str
    desc: "prepaid / subscription / post-delivery / advance-funded"
  - field: working_capital_direction
    type: str
    desc: "Positive (company funds customers) or Negative (customers/suppliers fund company)"
  - field: deferred_revenue_trend
    type: str
    desc: "Growing / Stable / Declining / N/A"
---

# D1-B: Payment Pattern

Map the complete cash flow timeline for a typical transaction.

## Analysis

1. **Transaction cash flow timeline**:
   - When is cost incurred vs when is payment received?
   - Does the company collect cash before delivering value (prepaid/subscription)?
   - Or does it deliver first and collect later (post-delivery)?

2. **Working capital direction** (from balance sheet trends):
   - Negative working capital (e.g., AMZN, COST) → customers/suppliers fund operations → favorable
   - Positive and growing working capital → company advances cash → unfavorable
   - Check: AR growth vs Revenue growth, Deferred Revenue trend, AP/Inventory dynamics

3. **SaaS/subscription patterns**:
   - Growing deferred revenue = prepaid model = cash flow advantage
   - High renewal rates (>90%) make deferred revenue quasi-recurring

## Classification

| Pattern | Cash Flow Advantage | Examples |
|---------|-------------------|----------|
| prepaid | Strong — cash before delivery | Insurance, annual licenses |
| subscription | Strong — recurring, predictable | SaaS, streaming |
| post-delivery | Neutral to weak — AR collection risk | Enterprise sales, consulting |
| advance-funded | Very strong — negative working capital | Marketplace, retail (COST, WMT) |

```json
{
  "payment_pattern": "subscription",
  "working_capital_direction": "Negative (customers fund operations)",
  "deferred_revenue_trend": "Growing"
}
```
