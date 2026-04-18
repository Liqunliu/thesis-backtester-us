---
id: valuation_synthesis_us
name: "Valuation & Synthesis (F4)"
category: valuation
tags: [f4, valuation, value-trap, safety-margin, scoring]
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
    desc: "LOW (0) / MEDIUM (1) / HIGH (>=2)"
  - field: value_trap_details
    type: str
    desc: "Triggered traps or 'None'"
  - field: position_sizing
    type: str
    desc: "Standard / Reduced / Minimal"
  - field: intrinsic_value
    type: float
    desc: "Composite intrinsic value ($M)"
  - field: upside_pct
    type: float
    desc: "Upside vs current market cap (%)"
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
    desc: "F1+F2+F3+F4 total (0-100)"
  - field: valuation_weights
    type: str
    desc: "Composite weight breakdown"
---

# F4: Valuation & Synthesis

Use pre-computed metrics from the **"Pre-Computed Quantitative Metrics"** section.
Do NOT recalculate GG, AA, owner earnings, or Graham Number.

## Step 1: Safety Margin

Read from snapshot: `GG vs Threshold II (7.3%)`. This is your safety margin in pp.

Position sizing:
- margin > 3pp + HIGH credibility → Standard
- margin > 1pp + MEDIUM credibility → Reduced
- margin < 1pp OR LOW credibility → Minimal

## Step 2: Value Trap Screening (5 checks)

| # | Trap | Trigger |
|---|------|---------|
| 1 | Cash flow deterioration | FCF declining ≥2 years AND >15% drop (check FCF History) |
| 2 | Moat narrowing | moat_rating narrowing from prior chapters |
| 3 | Structural decline | terminal demand shrinking (not cyclical) |
| 4 | Weak distribution | distribution_willingness = "Weak" |
| 5 | Management destroying value | management_rating negative |

N=0 → LOW, N=1 → MEDIUM, N≥2 → HIGH

## Step 3: Intrinsic Value (4 methods)

### A. GG Perpetuity
IV = AA_baseline / 0.09 (use AA from snapshot)

### B. P/E Multiple
Fair P/E = 1/(Rf + risk_premium). Risk premium: 3% (A), 4% (B), 5% (C).
IV = Fair_PE × EPS × Shares

### C. EV/EBITDA (debt-aware)
Fair EV = EBITDA × sector_multiple (7-10x)
IV = EV - Net_Debt (use Net Debt from snapshot)

### D. Graham Number
Already in snapshot. Compare vs current price.

### Composite Weights

| Method | Default | If D/E > 1.0 | If D/E > 2.0 |
|--------|---------|-------------|-------------|
| GG Perp | 30% | 25% | 20% |
| P/E | 25% | 25% | 20% |
| EV/EBITDA | 25% | 35% | 45% |
| Graham | 20% | 15% | 15% |

**CRITICAL**: High-debt companies need EV/EBITDA weight boosted — it's the only method that deducts debt.

## Step 4: Score & Recommend

| Condition | F4 Score |
|-----------|---------|
| Margin > 3pp + 0 traps + upside > 20% | 25 |
| Margin > 1pp + ≤1 trap + upside > 10% | 20 |
| Margin > 0 + manageable | 15 |
| Margin ≈ 0 or multiple traps | 10 |
| HIGH trap risk or negative margin | 5 |

Total = F1 + F2 + F3 + F4. F3 score: use pre-computed GG (GG>10%=25, >7.3%=20, >5%=15).

≥85 → strong BUY, 70-84 → BUY, 50-69 → HOLD, 30-49 → WATCH, ≤29 → AVOID

```json
{
  "gg_vs_threshold": 4.2,
  "value_trap_count": 0,
  "value_trap_risk": "LOW",
  "value_trap_details": "None",
  "position_sizing": "Reduced",
  "intrinsic_value": 180000.0,
  "upside_pct": 35.0,
  "recommendation": "BUY",
  "f4_conclusion": "PASS",
  "f4_score": 20,
  "total_score": 78,
  "valuation_weights": "GG 25%, P/E 25%, EV/EBITDA 35%, Graham 15% (D/E=1.1)"
}
```
