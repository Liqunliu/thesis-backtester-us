---
id: non_recurring_classification
name: "Non-Recurring Cash Flow Classification (F3 Step 7)"
category: quantitative
tags: [f3, non-recurring, distributable-cash]
data_needed: [cashflow, income]
outputs:
  - field: retained_items_total
    type: float
    desc: "Non-recurring items RETAINED as distributable cash ($M)"
  - field: deducted_items_total
    type: float
    desc: "Non-recurring items DEDUCTED as non-distributable ($M)"
  - field: retained_pct_of_ocf
    type: float
    desc: "Retained items as % of OCF (flag if >50%)"
  - field: non_recurring_flag
    type: bool
    desc: "True if non-operating items dominate (>50% of OCF)"
---

# F3 Step 7: Non-Recurring Cash Flow Classification

Classify by "whether constitutes distributable cash."

## Retained Items (real distributable cash — NOT deducted)

- Asset disposal proceeds — real cash, management can use for distributions
- Other investment income — dividends from associates, interest, money market gains
- Annotate impact on future earnings capacity

## Deducted Items (non-distributable)

- Government subsidies/grants
- Insurance proceeds
- Other one-time non-investment inflows

## Assessment

- Calculate retained items total as % of OCF
- If > 50% → Flag: non-operating cash dominated year
- If this happens in multiple years → operating business may not generate enough distributable cash on its own

```json
{
  "retained_items_total": 120.0,
  "deducted_items_total": 45.0,
  "retained_pct_of_ocf": 3.2,
  "non_recurring_flag": false
}
```
