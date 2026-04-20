---
id: survival_gate
name: "Survival Gate — Z-Score & Cash Runway"
category: screening
tags: [survival, z-score, bankruptcy, cash-burn, runway, veto]
data_needed: [income, balancesheet, cashflow]
gate:
  veto: true
outputs:
  - field: survival_pass
    type: bool
    desc: "True if company can survive 18+ months"
  - field: z_score
    type: float
    desc: "Altman Z-Score (from pre-computed metrics)"
  - field: z_zone
    type: str
    desc: "safe (>2.99) / grey (1.81-2.99) / distress (<1.81)"
  - field: cash_runway_months
    type: float
    desc: "Months of cash remaining at current burn rate"
  - field: debt_risk
    type: str
    desc: "LOW / MEDIUM / HIGH / CRITICAL"
  - field: survival_notes
    type: str
    desc: "Key survival factors and risks"
---

# Survival Gate — Will This Company Survive?

**CRITICAL**: This is a VETO gate. If survival_pass = false, stop all analysis.

Use pre-computed metrics from the snapshot. Do NOT recalculate Z-score.

## Step 1: Altman Z-Score Assessment

Read `altman_z_score` and `altman_zone` from Pre-Computed Quantitative Metrics.

| Zone | Z-Score | Assessment |
|------|---------|-----------|
| Safe | > 2.99 | Low bankruptcy risk — proceed |
| Grey | 1.81 - 2.99 | Elevated risk — proceed with caution |
| Distress | < 1.81 | **VETO** — high bankruptcy probability |

Exception: If Z-score is in distress zone BUT the company has:
- Cash runway > 24 months AND
- Revenue growing > 20% YoY AND
- Gross margin > 40%
Then override to PASS with debt_risk = "HIGH" (hyper-growth burn justified).

## Step 2: Cash Runway

If `ocf_negative` = true (company is burning cash):

| Runway | Assessment |
|--------|-----------|
| > 36 months | Comfortable — can survive multiple pivots |
| 18-36 months | Adequate — one shot at profitability |
| 12-18 months | Tight — needs fundraising or rapid improvement |
| < 12 months | **VETO** — imminent cash crisis |

If `ocf_negative` = false: company is cash-flow positive. No runway concern.

## Step 3: Debt Structure Assessment

From pre-computed metrics check:
- `debt_to_equity`: > 3.0 = HIGH risk
- `interest_coverage`: < 1.5x = CRITICAL (can't service debt)
- `total_debt` vs `cash_and_equivalents`: net debt position

If EDGAR footnotes available (SEC Filing Footnotes section):
- Check P6 (Commitments) for near-term debt maturities
- Check P13 (Non-Recurring) for restructuring charges (already in trouble?)

## Step 4: Revenue Trajectory as Lifeline

A company burning cash can still survive if revenue is growing fast enough
to reach profitability before cash runs out.

From pre-computed metrics:
- `revenue_growth_yoy`: Is revenue still growing?
- `revenue_trajectory`: accelerating / stable / decelerating?
- `gross_margin_direction`: expanding (path to profitability) or compressing (death spiral)?

**Death spiral signal**: Revenue decelerating + gross margin compressing + OCF negative
→ VETO regardless of Z-score.

```json
{
  "survival_pass": true,
  "z_score": 2.15,
  "z_zone": "grey",
  "cash_runway_months": 28.5,
  "debt_risk": "MEDIUM",
  "survival_notes": "Grey zone Z-score but 28-month runway + revenue growing 35% YoY. Gross margin expanding. Survival probable if growth continues."
}
```
