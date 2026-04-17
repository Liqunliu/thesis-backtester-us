---
id: valuation_synthesis_us
name: "Valuation & Synthesis (F4 Steps 1-6)"
category: valuation
tags: [f4, valuation, dcf, ddm, value-trap, safety-margin, scoring]
data_needed: [income, balancesheet, cashflow]
gate:
  exclude_industry: [Banks, Insurance]
outputs:
  - field: gg_vs_threshold
    type: float
    desc: "GG minus Threshold II (safety margin in pp)"
  - field: value_trap_count
    type: int
    desc: "Number of value trap checks triggered (0-5)"
  - field: value_trap_risk
    type: str
    desc: "LOW (0 traps) / MEDIUM (1) / HIGH (>=2)"
  - field: value_trap_details
    type: str
    desc: "List of triggered traps or 'None'"
  - field: position_sizing
    type: str
    desc: "Standard / Reduced / Minimal"
  - field: intrinsic_value
    type: float
    desc: "Composite intrinsic value estimate ($M market cap equivalent)"
  - field: upside_pct
    type: float
    desc: "Current price vs intrinsic value (%)"
  - field: recommendation
    type: str
    desc: "BUY / HOLD / WATCH / AVOID"
  - field: f4_conclusion
    type: str
    desc: "PASS or flag"
  - field: f4_score
    type: float
    desc: "F4 sub-score (0-25)"
  - field: total_score
    type: float
    desc: "F1 + F2 + F3 + F4 total (0-100)"
---

# F4: Valuation & Synthesis (Steps 1-6)

Final factor — integrates all upstream analysis into a valuation and recommendation.

## Step 1: Threshold Calculation

```
Rf = risk-free rate from data (US 10Y Treasury)
Threshold II = max(5%, Rf + 3%)
GG_primary = refined GG from F3

Safety margin = GG_primary - Threshold II
```

## Step 2: Value Trap Screening (5 checks)

| # | Trap | Trigger |
|---|------|---------|
| 1 | Cash flow deterioration | cash_surplus declining ≥2 consecutive years AND decline >15% |
| 2 | Moat narrowing | moat_rating assessed as narrowing or technical layer disrupted |
| 3 | Structural industry decline | terminal demand irreversibly shrinking (not cyclical) |
| 4 | Weak distribution willingness | distribution_willingness = "Weak" |
| 5 | Management destroying value | management_rating = "Destroying value" or "Observation" |

Assessment:
- N=0 → LOW risk
- N=1 → MEDIUM (flag risk but proceed)
- N≥2 → HIGH (if GG > Threshold II × 1.5 → retain; else exclude)

## Step 3: Safety Margin & Position Sizing

```
Safety margin = GG - Threshold II

Cyclicality adjustment (strong-cycle only):
  Cycle bottom: Threshold -1% → wider margin
  Cycle top: Threshold +2% → narrower margin

Position sizing matrix:
  margin > 3pp + HIGH credibility → Standard (full position)
  margin > 1pp + MEDIUM credibility → Reduced
  margin < 1pp OR LOW credibility → Minimal
```

## Step 4: Base Valuation (multiple approaches)

1. **GG-based perpetuity**: Intrinsic Value = AA / discount_rate
2. **P/E multiple**: Compare observed vs fair P/E (Rf-adjusted, moat premium)
3. **EV/EBITDA**: For capital-intensive businesses
4. **P/FCF**: When GAAP earnings differ from cash generation
5. **DDM**: Tax-adjusted dividend yield (15% US qualified)

Reconciliation: do approaches converge? If diverge > 20%, explain.

## Step 5: Price Target & Upside

```
Current market cap vs intrinsic value → upside/downside %
Conservative target = Intrinsic × (1 - volatility adjustment)
```

## Step 6: Cross-Validation & Final

- Do qualitative findings (D1-D6) support quantitative GG?
- Contradictions between Agent A and Agent B? (red flag)
- Integrate: GG + quality + moat + management → final recommendation

## Scoring

| Condition | F4 Score |
|-----------|---------|
| Margin > 3pp + 0 traps + upside > 20% | 25 |
| Margin > 1pp + ≤1 trap + upside > 10% | 20 |
| Margin > 0 + manageable risks | 15 |
| Margin near 0 or multiple traps | 10 |
| Value trap HIGH or margin negative | 5 |

## Total Score & Recommendation

```
Total = F1_score + F2_score + F3_score + F4_score

Any VETO from F1A/F2/F3 → Total capped at 25, recommendation = AVOID

≥85 → strong BUY
70-84 → BUY
50-69 → HOLD/WATCH
30-49 → WATCH
≤29 → AVOID
```

```json
{
  "gg_vs_threshold": 1.2,
  "value_trap_count": 0,
  "value_trap_risk": "LOW",
  "value_trap_details": "None",
  "position_sizing": "Reduced",
  "intrinsic_value": 65000.0,
  "upside_pct": 15.3,
  "recommendation": "BUY",
  "f4_conclusion": "PASS",
  "f4_score": 20,
  "total_score": 75
}
```
