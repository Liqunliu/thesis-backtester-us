---
id: business_quality
name: "Business Quality & Unit Economics"
category: qualitative
tags: [revenue, growth, margins, unit-economics, quality]
data_needed: [income, cashflow, balancesheet]
outputs:
  - field: revenue_quality
    type: str
    desc: "HIGH / MEDIUM / LOW — based on growth rate, consistency, diversification"
  - field: unit_economics_viable
    type: bool
    desc: "True if gross margin > 30% and improving or stable"
  - field: path_to_profitability
    type: str
    desc: "CLEAR / VISIBLE / UNCERTAIN / NONE"
  - field: moat_type
    type: str
    desc: "network-effects / switching-costs / data-moat / brand / none"
  - field: business_quality_score
    type: float
    desc: "0-25 sub-score"
---

# Business Quality & Unit Economics

For fallen growth stocks, the question is: "Does the business model work at scale?"

Use pre-computed metrics where available. Focus on trajectory, not absolute levels.

## Step 1: Revenue Quality

From pre-computed metrics:
- `revenue_growth_yoy`: Current growth rate
- `revenue_growth_2y_cagr`: 2-year CAGR (smoothed)
- `revenue_trajectory`: accelerating / stable / decelerating

| Revenue Growth | Revenue Trajectory | Quality |
|---------------|-------------------|---------|
| > 30% | Accelerating | HIGH |
| > 15% | Stable/Accelerating | MEDIUM |
| > 0% | Decelerating | LOW |
| Negative | Any | CRITICAL |

Also check from income statement:
- Is revenue concentrated in one product/segment? (concentration risk)
- Is growth organic or acquisition-driven? (look for large goodwill increases)

## Step 2: Unit Economics (Gross Margin)

The most important metric for pre-profit companies. From pre-computed:
- `gross_margin_latest`: Current GM%
- `gross_margin_avg_3y`: 3-year average
- `gross_margin_direction`: expanding / stable / compressing
- `gross_margin_trend_2y`: Change in pp over 2 years

| Gross Margin | Trend | Unit Economics |
|-------------|-------|---------------|
| > 50% | Expanding | Excellent — software-like |
| 30-50% | Stable+ | Viable — can reach profitability |
| 15-30% | Expanding | Possible — needs operating leverage |
| < 15% | Any | Challenging — structural issue |
| Any | Compressing > 5pp | Red flag — competitive pressure |

## Step 3: Path to Profitability

Assess how close the company is to operating breakeven:

From financial statements:
- Operating income trend: Is the loss narrowing?
- Operating leverage: Revenue growth >> cost growth?
- SBC as % of revenue: If SBC > 30% of revenue, "profitability" may be illusory

| Signal | Assessment |
|--------|-----------|
| Operating income positive | CLEAR — already profitable |
| Loss narrowing + GM expanding + OpEx leverage | VISIBLE — 1-2 years |
| Loss stable + GM stable | UNCERTAIN — needs catalyst |
| Loss widening + GM compressing | NONE — structural problem |

## Step 4: Competitive Position

For growth stocks, moat matters even more because they need to grow into valuation:

- **Network effects**: More users → more value → more users (fintech platforms)
- **Switching costs**: Embedded in customer workflows (SaaS, data platforms)
- **Data moat**: Proprietary data that improves with scale (ML/AI-driven lending)
- **Brand**: Strong brand premium (consumer tech)
- **None**: Commodity service competing on price

## Scoring (0-25)

| Condition | Score |
|-----------|-------|
| HIGH revenue quality + viable unit economics + CLEAR profitability path | 25 |
| MEDIUM revenue + viable economics + VISIBLE path | 20 |
| Growth positive + viable economics but path UNCERTAIN | 15 |
| Growth but economics unproven or path NONE | 10 |
| Declining revenue or compressing margins | 5 |

```json
{
  "revenue_quality": "MEDIUM",
  "unit_economics_viable": true,
  "path_to_profitability": "VISIBLE",
  "moat_type": "data-moat",
  "business_quality_score": 18
}
```
