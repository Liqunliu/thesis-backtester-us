---
id: coarse_penetration_return
name: "Coarse Penetration Return Rate (F2 Steps 3-4)"
category: quantitative
tags: [f2, gg, payout, veto, threshold]
data_needed: [income, cashflow]
outputs:
  - field: payout_ratio_anchor
    type: float
    desc: "Anchored payout ratio (%)"
  - field: payout_basis
    type: str
    desc: "committed / 3-year-avg"
  - field: avg_buybacks
    type: float
    desc: "3-year average cancellation-type buybacks ($M)"
  - field: coarse_return_R
    type: float
    desc: "Coarse penetration return rate (%)"
  - field: coarse_return_R_adj
    type: float
    desc: "SBC-adjusted coarse return rate (%)"
  - field: coarse_return_pass
    type: bool
    desc: "False = VETO (R < Rf)"
  - field: f2_conclusion
    type: str
    desc: "PASS / Marginal / VETO"
  - field: f2_score
    type: float
    desc: "F2 sub-score (0-25)"
---

# F2 Steps 3-4: Coarse Penetration Return Rate & Veto Gate

Top-down approximation: what yield can an owner extract at current price?

## Step 3: Calculate R

```
Payout ratio anchoring:
  ⚠ Do NOT use yfinance payoutRatio field.
  Calculate manually: Dividends Paid / Net Income

  Past 3 years payout ratio: [X1%, X2%, X3%]
  Average = [value]%
  Anchor rule: committed policy if stated, else 3-year average

Buybacks O = 3-year average cancellation-type buybacks = [value] $M
Tax rate Q = 15% (US qualified dividends)

Coarse Penetration Return Rate:
  R = [NI × Payout_Anchor × (1 − Q) + O] / Market_Cap × 100

SBC-adjusted:
  R_adj = [NI_adj × Payout_Anchor × (1 − Q) + O] / Market_Cap × 100
```

## Step 4: Veto Gate

```
US Thresholds:
  Rf = 4.3% (risk-free rate)
  Threshold II = 7.3% = max(5%, Rf + 3%)

Veto rules:
  R < Rf (4.3%)                → Hard VETO
  Rf ≤ R < Threshold II (7.3%) → Marginal (needs F3 to confirm)
  R ≥ Threshold II             → PASS
```

## F2 Scoring

| Condition | Score | Conclusion |
|-----------|-------|-----------|
| R > 10% | 25 | PASS |
| R > 7.3% (Threshold II) | 20 | PASS |
| R > 5% | 15 | Marginal |
| R > 4.3% (Rf) | 10 | Marginal |
| R ≤ 4.3% | 0 | VETO |

```json
{
  "payout_ratio_anchor": 35.0,
  "payout_basis": "3-year-avg",
  "avg_buybacks": 1500.0,
  "coarse_return_R": 8.2,
  "coarse_return_R_adj": 7.5,
  "coarse_return_pass": true,
  "f2_conclusion": "PASS",
  "f2_score": 20
}
```
