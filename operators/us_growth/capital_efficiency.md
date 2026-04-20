---
id: capital_efficiency
name: "Capital Efficiency & Growth Durability"
category: quantitative
tags: [efficiency, sbc, dilution, fcf, profitability-path, durability]
data_needed: [income, cashflow, balancesheet]
outputs:
  - field: revenue_per_employee_growth
    type: str
    desc: "IMPROVING / STABLE / DECLINING (if employee data available)"
  - field: sbc_dilution_rate
    type: float
    desc: "SBC as % of revenue — real cost of growth"
  - field: sbc_verdict
    type: str
    desc: "ACCEPTABLE (<15%) / ELEVATED (15-25%) / EXCESSIVE (>25%)"
  - field: fcf_margin
    type: float
    desc: "FCF / Revenue % (negative for pre-profit companies)"
  - field: fcf_trend
    type: str
    desc: "IMPROVING / STABLE / DETERIORATING"
  - field: cash_conversion
    type: str
    desc: "HIGH / MEDIUM / LOW — how efficiently growth converts to cash"
  - field: growth_durability
    type: str
    desc: "SELF_FUNDING / NEAR_SELF_FUNDING / DEPENDENT / DILUTIVE"
  - field: efficiency_score
    type: float
    desc: "0-25 sub-score"
---

# Capital Efficiency & Growth Durability

The critical question for growth stocks: Is this growth **self-sustaining**
or does it require continuous dilution/fundraising?

Use pre-computed metrics where available.

## Step 1: SBC Dilution Analysis

Stock-Based Compensation is the hidden cost of growth. From financial data:

```
SBC / Revenue = dilution rate
```

From pre-computed: `sbc`, `revenue`

| SBC / Revenue | Verdict | Implication |
|--------------|---------|-------------|
| < 10% | ACCEPTABLE | Growth is cheap — shareholders benefit |
| 10-15% | ACCEPTABLE | Normal for high-growth tech |
| 15-25% | ELEVATED | Meaningful dilution — discount accordingly |
| > 25% | EXCESSIVE | Growth is being "bought" with equity |

Also check share count trend from balance sheet:
- Shares outstanding growing > 3% annually = significant dilution
- Shares outstanding stable = buybacks offsetting SBC
- Shares outstanding declining = net buybacks (rare for growth companies)

## Step 2: FCF Margin & Trend

From pre-computed metrics: `free_cash_flow`, `revenue`

```
FCF Margin = Free Cash Flow / Revenue × 100
```

| FCF Margin | Assessment |
|-----------|-----------|
| > 20% | Exceptional — self-funding growth + returning capital |
| 10-20% | Strong — self-funding growth |
| 0-10% | Breakeven — growth funded from operations |
| -10% to 0% | Near breakeven — approaching self-funding |
| < -10% | Cash-burning — dependent on external capital |

FCF trend from `fcf_history`:
- Margins improving each year = IMPROVING (path to profitability visible)
- Margins stable = STABLE
- Margins worsening = DETERIORATING (red flag)

## Step 3: Growth Efficiency Metrics

From income statement and cash flow:

**Operating Leverage**: Is revenue growing faster than costs?
```
Revenue growth vs OpEx growth:
  Revenue +30%, OpEx +20% → Positive leverage (margins expanding)
  Revenue +30%, OpEx +35% → Negative leverage (margins compressing)
```

**Incremental Margin**: What margin do NEW dollars of revenue earn?
```
Incremental Margin = ΔOperating Income / ΔRevenue
  > 30% = excellent unit economics at scale
  10-30% = good leverage
  < 10% = growth doesn't scale profitably
```

## Step 4: Growth Durability Classification

Combining all efficiency signals:

| Classification | Criteria |
|---------------|---------|
| **SELF_FUNDING** | FCF positive + SBC < 15% + shares stable. Can grow indefinitely without external capital |
| **NEAR_SELF_FUNDING** | FCF near breakeven + improving margins. 1-2 years from self-funding |
| **DEPENDENT** | FCF negative but cash runway > 24m + margins improving. Needs capital but has time |
| **DILUTIVE** | FCF negative + SBC > 25% + shares increasing rapidly. Growth comes at shareholder expense |

## Scoring (0-25)

| Condition | Score |
|-----------|-------|
| SELF_FUNDING + SBC ACCEPTABLE + positive operating leverage | 25 |
| NEAR_SELF_FUNDING + SBC ACCEPTABLE + improving FCF | 20 |
| DEPENDENT but margins improving + moderate SBC | 15 |
| DEPENDENT with stable/compressing margins | 10 |
| DILUTIVE — excessive SBC + no path to profitability | 5 |

```json
{
  "revenue_per_employee_growth": "IMPROVING",
  "sbc_dilution_rate": 12.5,
  "sbc_verdict": "ACCEPTABLE",
  "fcf_margin": 8.5,
  "fcf_trend": "IMPROVING",
  "cash_conversion": "MEDIUM",
  "growth_durability": "NEAR_SELF_FUNDING",
  "efficiency_score": 20
}
```
