---
id: growth_quality_gate
name: "Growth Quality Gate"
category: screening
tags: [growth, revenue, margins, gate, veto]
data_needed: [income, cashflow]
gate:
  veto: true
outputs:
  - field: growth_pass
    type: bool
    desc: "True if growth quality meets minimum bar"
  - field: revenue_cagr_2y
    type: float
    desc: "2-year revenue CAGR (%)"
  - field: revenue_acceleration
    type: str
    desc: "accelerating / stable / decelerating"
  - field: gross_margin_pct
    type: float
    desc: "Latest gross margin (%)"
  - field: rule_of_40
    type: float
    desc: "Revenue Growth % + Operating Margin %"
  - field: rule_of_40_grade
    type: str
    desc: "ELITE (>60) / SOLID (40-60) / MARGINAL (20-40) / FAIL (<20)"
  - field: growth_quality_score
    type: float
    desc: "0-25 sub-score"
---

# Growth Quality Gate

Determines if this stock qualifies as a growth compounder.

Use pre-computed metrics from the snapshot. Do NOT recalculate.

## Step 1: Revenue Growth Test

From pre-computed metrics:
- `revenue_growth_yoy`: Latest year-over-year growth
- `revenue_growth_2y_cagr`: 2-year CAGR (smoothed)
- `revenue_trajectory`: accelerating / stable / decelerating

| 2Y CAGR | Trajectory | Assessment |
|---------|-----------|-----------|
| > 30% | Accelerating | Elite — rare, high confidence |
| > 30% | Stable | Strong — sustainable high growth |
| > 20% | Any | Solid growth compounder |
| 15-20% | Accelerating | Acceptable — improving trajectory |
| 15-20% | Decelerating | Warning — growth slowing |
| < 15% | Any | **VETO** — not a growth stock |

## Step 2: Gross Margin Quality

From pre-computed: `gross_margin_latest`, `gross_margin_direction`

| Gross Margin | Direction | Assessment |
|-------------|----------|-----------|
| > 70% | Expanding | Software-tier — excellent |
| 50-70% | Stable+ | Platform/SaaS — strong |
| 40-50% | Expanding | Hardware+services mix — acceptable |
| 35-40% | Expanding | Marginal — needs operating leverage |
| < 35% | Any | **VETO** — not a high-margin growth business |

## Step 3: Rule of 40

```
Rule of 40 = Revenue Growth % + Operating Margin %

From income statement:
  Operating margin = Operating Income / Revenue × 100
  (Negative operating margin is OK if growth compensates)
```

| Rule of 40 | Grade | Example |
|-----------|-------|---------|
| > 60 | ELITE | 40% growth + 20% margin, or 25% growth + 35% margin |
| 40-60 | SOLID | 30% growth + 15% margin, or 20% growth + 25% margin |
| 20-40 | MARGINAL | 25% growth - 5% margin, or 15% growth + 10% margin |
| < 20 | FAIL | Growth not compensating for losses |

## Step 4: Revenue Quality Checks

Additional quality signals from financial statements:
- **Organic vs acquired growth**: Large goodwill increases = acquisition-driven (lower quality)
- **Customer concentration**: If available, top customer > 20% = risk
- **Revenue consistency**: QoQ volatility — consistent is better than lumpy
- **Deferred revenue growth**: Growing backlog = future revenue visibility (SaaS)

## Scoring (0-25)

| Condition | Score |
|-----------|-------|
| CAGR > 30% + GM > 50% + Rule of 40 ELITE + accelerating | 25 |
| CAGR > 25% + GM > 40% + Rule of 40 SOLID | 22 |
| CAGR > 20% + GM > 40% + Rule of 40 SOLID | 18 |
| CAGR > 15% + GM > 35% + Rule of 40 MARGINAL | 12 |
| Barely passing growth gate | 8 |
| **VETO** (growth or margin below minimum) | 0 |

```json
{
  "growth_pass": true,
  "revenue_cagr_2y": 28.5,
  "revenue_acceleration": "stable",
  "gross_margin_pct": 62.0,
  "rule_of_40": 45.0,
  "rule_of_40_grade": "SOLID",
  "growth_quality_score": 18
}
```
