---
id: inflection_synthesis
name: "Inflection Detection & Recommendation"
category: valuation
tags: [inflection, turning-point, trough, peak, synthesis, scoring]
data_needed: [income, cashflow, balancesheet, market_data]
outputs:
  - field: inflection_type
    type: str
    desc: "TROUGH_CONFIRMED / TROUGH_FORMING / NO_INFLECTION / PEAK_FORMING / PEAK_CONFIRMED"
  - field: trough_signals_count
    type: int
    desc: "Number of trough signals triggered (0-6)"
  - field: peak_signals_count
    type: int
    desc: "Number of peak signals triggered (0-6)"
  - field: recommendation
    type: str
    desc: "BUY / WATCH / HOLD / REDUCE / AVOID"
  - field: position_size_pct
    type: float
    desc: "Suggested position size (% of portfolio)"
  - field: total_score
    type: float
    desc: "0-100 composite score"
  - field: conviction
    type: str
    desc: "HIGH / MEDIUM / LOW"
  - field: entry_price_target
    type: float
    desc: "Suggested entry price if WATCH"
  - field: exit_trigger
    type: str
    desc: "Condition that invalidates the thesis"
  - field: falsifiable_thesis
    type: str
    desc: "One-sentence investment thesis that can be proven wrong"
---

# Inflection Detection & Recommendation

The core question: Is this stock at a turning point?

Use pre-computed metrics and upstream chapter outputs. Do NOT recalculate.

## Step 1: Trough Signal Checklist

Count how many trough signals are present:

| # | Signal | Source | Check |
|---|--------|--------|-------|
| 1 | Revenue re-accelerating | `revenue_trajectory` = "accelerating" | |
| 2 | Gross margin expanding | `gross_margin_direction` = "expanding" | |
| 3 | OCF improving | OCF less negative or turning positive vs prior year | |
| 4 | P/S compressed | `price_to_sales` < 2x (or below 2yr median if available) | |
| 5 | Insider buying | From ch03 sentiment: insider_signal = BUYING or BUYING_CLUSTER | |
| 6 | Price near 52-week low | From ch03: price_vs_52w = NEAR_LOW or LOWER_HALF | |

## Step 2: Peak Signal Checklist

| # | Signal | Source | Check |
|---|--------|--------|-------|
| 1 | Revenue decelerating | `revenue_trajectory` = "decelerating" | |
| 2 | Gross margin compressing | `gross_margin_direction` = "compressing" | |
| 3 | OCF deteriorating | OCF turning more negative or declining from positive | |
| 4 | P/S stretched | `price_to_sales` > 10x (or above 2yr median) | |
| 5 | Insider selling | From ch03: insider_signal = SELLING or SELLING_HEAVY | |
| 6 | Price near 52-week high | From ch03: price_vs_52w = NEAR_HIGH | |

## Step 3: Inflection Classification

| Trough Signals | Peak Signals | Classification |
|---------------|-------------|---------------|
| >= 4 | <= 1 | **TROUGH_CONFIRMED** |
| 3 | <= 1 | TROUGH_FORMING |
| <= 2 | <= 2 | NO_INFLECTION |
| <= 1 | 3 | PEAK_FORMING |
| <= 1 | >= 4 | **PEAK_CONFIRMED** |

## Step 4: Composite Score

```
Survival score (from ch01): 0-30
Business quality score (from ch02): 0-25
Sentiment score (from ch03): 0-20
Inflection score: 0-25
  TROUGH_CONFIRMED = 25
  TROUGH_FORMING = 18
  NO_INFLECTION = 10
  PEAK_FORMING = 5
  PEAK_CONFIRMED = 0

Total = Survival + Business + Sentiment + Inflection
```

## Step 5: Recommendation

| Score | Inflection | Recommendation | Position |
|-------|-----------|---------------|----------|
| >= 75 | TROUGH_CONFIRMED | **BUY** | 5-8% |
| >= 75 | TROUGH_FORMING | **BUY (reduced)** | 3-5% |
| 60-74 | Any trough signal | **WATCH** (close to entry) | 0% (set alert) |
| 40-59 | NO_INFLECTION | **HOLD** (if already own) | Hold existing |
| 40-59 | Any peak signal | **REDUCE** | Trim 50% |
| < 40 | Any | **AVOID** | 0% |
| Any | PEAK_CONFIRMED | **AVOID/SELL** | 0% |

## Step 6: Exit Triggers

Define specific conditions that invalidate the thesis:
- Revenue declines for 2 consecutive quarters
- Gross margin drops below [specific level] 
- Z-score enters distress zone (< 1.81)
- Cash runway drops below 12 months
- P/S exceeds [2x entry P/S] (take profit)

## Step 7: Falsifiable Thesis

Write ONE sentence that:
1. States WHY this stock will recover (specific catalyst)
2. States the CONDITION that proves the thesis wrong
3. Includes a TIME FRAME

Example: "Revenue will re-accelerate to >25% YoY by Q3 2027 as AI-lending 
volumes scale, with gross margin stabilizing above 60%; thesis fails if 
revenue growth drops below 10% for two quarters or if gross margin falls 
below 50%."

```json
{
  "inflection_type": "TROUGH_FORMING",
  "trough_signals_count": 3,
  "peak_signals_count": 0,
  "recommendation": "WATCH",
  "position_size_pct": 0.0,
  "total_score": 65,
  "conviction": "MEDIUM",
  "entry_price_target": 12.50,
  "exit_trigger": "Revenue growth < 10% for 2 quarters OR gross margin < 50% OR Z-score < 1.81",
  "falsifiable_thesis": "AI-lending volumes drive revenue re-acceleration to 25%+ by Q3 2027; thesis fails if growth drops below 10% or GM below 50%."
}
```
