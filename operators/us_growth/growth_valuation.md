---
id: growth_valuation
name: "Growth Valuation & Recommendation"
category: valuation
tags: [valuation, peg, ev-revenue, ps, growth-adjusted, scoring]
data_needed: [income, cashflow, balancesheet, market_data]
outputs:
  - field: peg_ratio
    type: float
    desc: "PE / EPS Growth Rate (< 1.5 = attractive)"
  - field: ev_revenue_vs_growth
    type: float
    desc: "EV/Revenue divided by growth rate (< 1.0 = attractive)"
  - field: ps_percentile
    type: str
    desc: "COMPRESSED / FAIR / STRETCHED / EXTREME"
  - field: growth_adjusted_value
    type: str
    desc: "UNDERVALUED / FAIR / OVERVALUED / EXTREME_OVERVALUED"
  - field: recommendation
    type: str
    desc: "BUY / ACCUMULATE / HOLD / REDUCE / AVOID"
  - field: position_size_pct
    type: float
    desc: "Suggested position (% of portfolio)"
  - field: total_score
    type: float
    desc: "0-100 composite score"
  - field: conviction
    type: str
    desc: "HIGH / MEDIUM / LOW"
  - field: exit_triggers
    type: str
    desc: "Conditions that invalidate the growth thesis"
  - field: falsifiable_thesis
    type: str
    desc: "One-sentence thesis that can be proven wrong"
---

# Growth Valuation & Recommendation

Growth stocks require growth-adjusted valuation. Traditional PE/PB
are misleading for companies investing heavily in future growth.

Use pre-computed metrics from the snapshot.

## Step 1: PEG Ratio

```
PEG = PE / Expected EPS Growth Rate (%)

If PE available and positive:
  EPS Growth ≈ Revenue Growth (for pre-profit, use revenue growth proxy)
  PEG = PE / revenue_growth_yoy (from pre-computed)
```

| PEG | Assessment |
|-----|-----------|
| < 0.75 | Deeply undervalued for growth rate |
| 0.75 - 1.0 | Undervalued — growth not priced in |
| 1.0 - 1.5 | Fair — growth roughly priced in |
| 1.5 - 2.5 | Fully valued — limited upside |
| > 2.5 | Overvalued — growth doesn't justify price |

If PE is negative (pre-profit), PEG is not applicable — skip to EV/Revenue.

## Step 2: EV/Revenue vs Growth Rate

The core metric for pre-profit growth stocks:

```
EV = Market Cap + Net Debt (from pre-computed)
EV/Revenue = EV / Latest Revenue

Growth-Adjusted Ratio = (EV/Revenue) / (Revenue Growth % / 100)
  Example: EV/Rev = 8x, Growth = 30% → Ratio = 8/30 = 0.27 (attractive)
  Example: EV/Rev = 15x, Growth = 20% → Ratio = 15/20 = 0.75 (fair)
```

| Ratio | Assessment |
|-------|-----------|
| < 0.3 | UNDERVALUED — market ignoring growth |
| 0.3 - 0.7 | FAIR — reasonable for growth rate |
| 0.7 - 1.2 | FULLY_VALUED — growth priced in |
| > 1.2 | OVERVALUED — growth premium excessive |

## Step 3: P/S Context

From pre-computed: `price_to_sales`

For context, compare P/S against what's reasonable for the growth rate:

| Revenue Growth | "Fair" P/S Range | Notes |
|---------------|-----------------|-------|
| > 40% | 8-15x | Hyper-growth premium justified |
| 25-40% | 5-10x | Strong growth |
| 15-25% | 3-7x | Moderate growth |
| < 15% | 1-4x | Mature growth |

| P/S vs Fair Range | Percentile |
|------------------|-----------|
| Below range | COMPRESSED |
| Within range | FAIR |
| 1-2x above range | STRETCHED |
| > 2x above range | EXTREME |

## Step 4: Growth-Adjusted Intrinsic Value

Simplified forward revenue model:
```
Forward Revenue (3yr) = Current Revenue × (1 + Growth Rate)^3
Assumed steady-state margin at maturity = 20% (SaaS) / 15% (platform) / 10% (marketplace)
Forward earnings = Forward Revenue × Steady-state margin
Fair value = Forward earnings × 25x (growth premium PE)
Discounted back 3 years at 12% = Fair value / 1.12^3
```

Compare discounted fair value vs current market cap.

## Step 5: Composite Score

```
Growth Quality (from ch01): 0-25
TAM & Position (from ch02): 0-25
Capital Efficiency (from ch03): 0-25
Valuation: 0-25
  Growth-adjusted UNDERVALUED + PEG < 1.0 = 25
  UNDERVALUED or PEG < 1.5 = 20
  FAIR valuation = 15
  FULLY_VALUED = 10
  OVERVALUED = 5
  EXTREME = 0

Total = Growth + TAM + Efficiency + Valuation
```

## Step 6: Recommendation

| Score | Valuation | Recommendation | Position |
|-------|----------|---------------|----------|
| >= 80 | UNDER/FAIR | **BUY** | 5-8% |
| 65-79 | UNDER/FAIR | **ACCUMULATE** | 3-5% |
| 65-79 | STRETCHED | **HOLD** | Hold existing |
| 50-64 | Any | **HOLD** | Hold existing |
| 35-49 | STRETCHED+ | **REDUCE** | Trim to 2% |
| < 35 | Any | **AVOID** | 0% |
| Any | EXTREME | **AVOID** | 0% |

## Step 7: Exit Triggers

Growth thesis fails when:
1. Revenue growth drops below 15% for 2 consecutive periods
2. Gross margin declines > 5pp from peak
3. Rule of 40 drops below 20
4. Net dollar retention drops below 100% (if SaaS)
5. Management turnover (CEO/CTO departure)
6. P/S exceeds 2x the "fair" range for current growth rate

## Step 8: Falsifiable Thesis

Write ONE sentence:
- What growth rate is expected and why
- What margin trajectory is assumed
- What condition proves it wrong
- Time frame (typically 2-3 years for growth stocks)

```json
{
  "peg_ratio": 1.2,
  "ev_revenue_vs_growth": 0.45,
  "ps_percentile": "FAIR",
  "growth_adjusted_value": "UNDERVALUED",
  "recommendation": "BUY",
  "position_size_pct": 5.0,
  "total_score": 78,
  "conviction": "HIGH",
  "exit_triggers": "Revenue growth < 15% for 2 periods OR GM < 55% OR Rule of 40 < 20",
  "falsifiable_thesis": "Revenue sustains 25%+ CAGR through 2028 as cloud migration accelerates TAM penetration; fails if growth drops below 15% or GM compresses below 55%."
}
```
