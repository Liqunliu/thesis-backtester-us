---
id: refined_return_aa
name: "Refined Return Rate & AA Calculation (F3 Steps 11-12)"
category: quantitative
tags: [f3, gg, aa, refined, veto, distribution]
data_needed: [income, cashflow, balancesheet]
outputs:
  - field: aa_baseline
    type: float
    desc: "Real Disposable Cash Surplus, baseline ($M)"
  - field: aa_ex_sbc
    type: float
    desc: "AA excluding SBC ($M)"
  - field: gg_primary
    type: float
    desc: "Refined penetration return rate (%)"
  - field: gg_ex_sbc
    type: float
    desc: "GG excluding SBC (%)"
  - field: distribution_willingness
    type: str
    desc: "Strong / Moderate / Weak"
  - field: f3_conclusion
    type: str
    desc: "PASS / VETO"
  - field: f3_score
    type: float
    desc: "F3 sub-score (0-25)"
---

# F3 Steps 11-12: Real Disposable Cash Surplus & Refined GG

The final number that anchors valuation.

## Step 11: AA Calculation

```
AA = OCF - Maintenance CapEx + Retained Non-Recurring - Contingent Liabilities

Calculate for each available year (3-5 years).

AA selection rules:
  If any year's non-recurring > 50% of OCF → exclude that year
  If cash reserve declining → use 2-year average
  Else → use full average

Lambda (λ) = operating leverage = ΔOE / ΔRevenue
  Measures earnings elasticity to revenue change.
  λ > 2.0 = high leverage (small revenue drop → large earnings drop)
```

## Step 12: Distribution Assessment & Refined GG

```
Distribution willingness:
  Strong: consistent dividend increases + aggressive buybacks
  Moderate: modest dividend + selective buybacks
  Weak: no distributions, capital hoarding

Refined GG = AA / Market Cap × 100
GG_exSBC = (AA - SBC) / Market Cap × 100
```

## F3 Veto Gate

```
US Thresholds: Rf = 4.3%, Threshold II = 7.3%

GG ≥ Threshold II → PASS
GG < Threshold II but growth CapEx > 30% of deductions → Review (not auto-veto)
GG < Rf → VETO
```

## F3 Scoring

| Condition | Score |
|-----------|-------|
| GG > 10% + HIGH credibility | 25 |
| GG > 7.3% + MEDIUM credibility | 20 |
| GG > 7.3% + LOW credibility | 15 |
| GG > 5% | 10 |
| GG ≤ 5% | 5 |
| VETO | 0 |

```json
{
  "aa_baseline": 4800.0,
  "aa_ex_sbc": 4350.0,
  "gg_primary": 8.5,
  "gg_ex_sbc": 7.7,
  "distribution_willingness": "Strong",
  "f3_conclusion": "PASS",
  "f3_score": 20
}
```
