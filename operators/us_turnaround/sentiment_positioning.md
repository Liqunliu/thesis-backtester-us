---
id: sentiment_positioning
name: "Sentiment & Market Positioning"
category: qualitative
tags: [sentiment, short-interest, insider, institutional, positioning]
data_needed: [market_data, balancesheet]
outputs:
  - field: sentiment_signal
    type: str
    desc: "CAPITULATION / PESSIMISTIC / NEUTRAL / OPTIMISTIC / EUPHORIA"
  - field: insider_signal
    type: str
    desc: "BUYING_CLUSTER / BUYING / NEUTRAL / SELLING / SELLING_HEAVY"
  - field: price_vs_52w
    type: str
    desc: "NEAR_LOW / LOWER_HALF / MID / UPPER_HALF / NEAR_HIGH"
  - field: valuation_percentile
    type: str
    desc: "COMPRESSED / BELOW_MEDIAN / MEDIAN / ABOVE_MEDIAN / STRETCHED"
  - field: sentiment_score
    type: float
    desc: "0-20 sub-score"
---

# Sentiment & Market Positioning

For turnaround stocks, sentiment often reaches extremes. Contrarian signals
at capitulation can be highly profitable; euphoria signals at peaks warn of danger.

## Step 1: Price Position

From the snapshot's price history and market data:

Calculate where current price sits vs 52-week range:

| Position | Price vs 52W | Signal |
|----------|-------------|--------|
| NEAR_LOW | Bottom 10% of range | Capitulation zone |
| LOWER_HALF | 10-40% of range | Pessimistic |
| MID | 40-60% | Neutral |
| UPPER_HALF | 60-90% | Optimistic |
| NEAR_HIGH | Top 10% | Euphoria risk |

Also check: How far has price fallen from all-time high?
- > 70% from ATH = deep capitulation (potential trough)
- > 50% from ATH = significant distress
- < 20% from ATH = no real distress

## Step 2: Valuation Percentile (P/S based)

For pre-profit companies, P/S is the primary valuation metric.
From pre-computed metrics: `price_to_sales`

| P/S | For High-Growth (>30%) | For Moderate Growth (<30%) | Assessment |
|-----|----------------------|--------------------------|------------|
| < 1x | Extremely compressed | Very compressed | COMPRESSED |
| 1-3x | Compressed | Below median | BELOW_MEDIAN |
| 3-7x | Reasonable | Median | MEDIAN |
| 7-15x | Above median | Stretched | ABOVE_MEDIAN |
| > 15x | Stretched | Extreme | STRETCHED |

## Step 3: Insider Activity (from EDGAR or Bloomberg)

If SEC Filing Footnotes or holder data available:
- Look for insider purchasing in the last 6 months
- Cluster buying (3+ insiders buying within 30 days) = strong signal
- Large single purchase (> $500K by CEO/CFO) = strong signal

If no insider data available, assess from financial statements:
- Share count changes: decreasing = buybacks (management confident)
- Share count increasing rapidly = dilution (desperate for cash)

| Signal | Assessment |
|--------|-----------|
| Cluster insider buying + share count stable/declining | BUYING_CLUSTER (strongest) |
| Some insider buying | BUYING |
| No notable activity | NEUTRAL |
| Insider selling + share count increasing | SELLING |
| Heavy insider selling + large dilution | SELLING_HEAVY |

## Step 4: Macro Context

From the Macro Environment section:
- Are credit conditions tightening (bad for growth stocks) or easing?
- HY spread > 500bp = risk-off environment (headwind for turnarounds)
- VIX > 30 = fear (contrarian opportunity if company-specific thesis strong)
- Fed funds trending down = tailwind for growth stock multiples

## Scoring (0-20)

| Condition | Score |
|-----------|-------|
| CAPITULATION + insider BUYING_CLUSTER + P/S COMPRESSED | 20 |
| PESSIMISTIC + some positive insider + P/S below median | 15 |
| NEUTRAL sentiment + neutral positioning | 10 |
| OPTIMISTIC + no insider buying + P/S above median | 5 |
| EUPHORIA + insider selling + P/S stretched | 0 |

```json
{
  "sentiment_signal": "PESSIMISTIC",
  "insider_signal": "BUYING",
  "price_vs_52w": "LOWER_HALF",
  "valuation_percentile": "BELOW_MEDIAN",
  "sentiment_score": 15
}
```
