---
id: f1a_quick_screen
name: "F1A Quick Screen (6 Veto Checks)"
category: screening
tags: [screening, veto, f1, quality-gate]
data_needed: [income, balancesheet, cashflow, indicator]
outputs:
  - field: f1a_pass
    type: bool
    desc: "true if stock passes all 6 quick screen checks"
  - field: f1a_veto_reason
    type: str
    desc: "Reason for veto if failed, empty string if passed"
  - field: capital_intensity_initial
    type: str
    desc: "Initial classification: capital-light or capital-hungry"
  - field: payment_pattern_initial
    type: str
    desc: "Initial classification: prepaid / subscription / post-delivery / advance-funded"
  - field: cyclicality_initial
    type: str
    desc: "Initial classification: strong-cycle / weak-cycle / non-cycle"
  - field: moat_intuition
    type: str
    desc: "One-sentence moat hypothesis"
---

# F1A Quick Screen — 6 Binary Veto Checks

Using only available financial data, evaluate each of the 6 items below.
**If ANY item is YES → set f1a_pass = false and stop.**

## Veto Checklist

| # | Check | Criteria | How to Assess |
|---|-------|----------|---------------|
| 1 | Abnormal audit opinion | Qualified / adverse / disclaimer / going concern emphasis in most recent annual report | Check auditor report in 10-K. Look for "going concern" language. |
| 2 | Frequent auditor changes | Changed auditors >= 2 times in past 5 years, especially Big 4 to smaller firm | Check auditor name in recent 10-K filings vs prior years. |
| 3 | Financial fraud or major violations | SEC enforcement actions, accounting restatements, class action settlements against company or controlling shareholder | Check SEC filings, note any restatements in financial statements. |
| 4 | Cannot understand business model | Cannot explain in one sentence: revenue source, cost structure, profit generation mechanism | Attempt a one-sentence summary. If impossible, veto. |
| 5 | Unproven business model | Not tested through at least 1 full economic cycle (7+ years of operating history), or underwent major business pivot | Check company age, IPO date, and revenue history stability. |
| 6 | Major insider red flags | Insider selling > 20% of holdings / SEC investigation of officers / criminal charges / poison pill adoption | Check insider transaction data if available. |

## Evaluation Instructions

1. For each check, state YES or NO with one-line evidence.
2. If ANY check is YES:
   - Set `f1a_pass = false`
   - Set `f1a_veto_reason` to the check number and reason
   - Stop analysis. Do not compute initial profile.
3. If ALL checks are NO:
   - Set `f1a_pass = true`
   - Set `f1a_veto_reason = ""`
   - Compute the initial profile below.

## Initial Profile (only if all pass)

Based on a quick scan of income statement and cash flow:

- `capital_intensity_initial`: Is CapEx/Revenue > 10%? capital-hungry. Else capital-light.
- `payment_pattern_initial`: Does the company collect cash before delivering (prepaid/subscription) or after (post-delivery)? Check deferred revenue trend.
- `cyclicality_initial`: Has revenue varied > 30% peak-to-trough in available history? strong-cycle. 10-30%? weak-cycle. <10%? non-cycle.
- `moat_intuition`: One sentence on why this business might have a durable competitive advantage (or why it might not).

## Output Format

```json
{
  "f1a_pass": true,
  "f1a_veto_reason": "",
  "capital_intensity_initial": "capital-light",
  "payment_pattern_initial": "subscription",
  "cyclicality_initial": "weak-cycle",
  "moat_intuition": "Platform with network effects and high switching costs"
}
```
