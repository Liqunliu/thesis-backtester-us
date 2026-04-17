---
id: cash_revenue_reconstruction
name: "Cash Revenue Reconstruction & AR Audit (F3 Steps 5-6)"
category: quantitative
tags: [f3, cash-revenue, ar, collection, asc606]
data_needed: [income, balancesheet, cashflow]
outputs:
  - field: true_cash_revenue
    type: float
    desc: "Real cash revenue after AR/deferred rev adjustment ($M)"
  - field: collection_ratio
    type: float
    desc: "Real Cash Revenue / Reported Revenue"
  - field: ar_quality
    type: str
    desc: "Good / Acceptable / Concerning"
  - field: asc606_risk
    type: str
    desc: "Normal / Aggressive recognition risk exists"
---

# F3 Steps 5-6: Cash Revenue Reconstruction & AR Audit

Strip accrual noise to find real cash collected from customers.

## Step 5: Revenue Reconstruction (year by year)

```
Revenue = [value] $M (S)
AR net change = [value] $M (T) — increase positive, decrease negative
Deferred Revenue net change = [value] $M (U)

Conservative rules:
  AR increase → Deduct (earned but not collected)
  AR decrease → Add back (collected previously owed)
  Deferred Rev increase → Do NOT add back (undelivered obligation)
  Deferred Rev decrease → Deduct (consumed previously collected cash)
  Exception: SaaS with >95% renewal may add back DR increase (annotate)

Real Cash Revenue = S − T_increase − U_decrease
Collection Ratio = Real Cash Revenue / S
```

| Year | Revenue | AR Change | DR Change | Cash Revenue | Ratio |
|------|---------|-----------|-----------|-------------|-------|

## Step 6: AR Footnote Audit (mandatory if Collection Ratio < 1)

If AR footnotes available (from EDGAR/data_pack_footnotes):
- AR aging: >1 year as % of total, trend
- Bad debt provision rate vs peers: lenient / in-line / conservative
- Customer concentration: top 5 as % of AR
- Related-party AR as % of total
- ASC 606 aggressiveness: bill-and-hold, variable consideration, multiple POs

If footnotes unavailable: note limitation and proceed.

```json
{
  "true_cash_revenue": 38500.0,
  "collection_ratio": 0.97,
  "ar_quality": "Good",
  "asc606_risk": "Normal"
}
```
