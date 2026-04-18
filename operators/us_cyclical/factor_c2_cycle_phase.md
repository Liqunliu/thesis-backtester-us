---
id: factor_c2_cycle_phase
name: "C2: Cycle Phase Detection"
category: cyclical
tags: [c2, cycle-phase, composite-score, sector, macro]
data_needed: [income, cashflow, balancesheet, market_data]
outputs:
  - field: composite_score
    type: float
    desc: "Composite cycle score (0.0 = peak, 1.0 = deep trough)"
  - field: phase
    type: int
    desc: "Cycle phase number (1-5)"
  - field: phase_name
    type: str
    desc: "Phase label: Deep Trough / Early Recovery / Mid-Cycle / Late Cycle / Peak"
  - field: company_score
    type: float
    desc: "Company fundamentals sub-score (0.0-1.0)"
  - field: sector_score
    type: float
    desc: "Sector indicator sub-score (0.0-1.0)"
  - field: macro_score
    type: float
    desc: "Macro overlay sub-score (0.0-1.0)"
  - field: price_score
    type: float
    desc: "Price position sub-score (0.0-1.0)"
  - field: action
    type: str
    desc: "Recommended action: BUY_MAX / BUY_STD / HOLD / REDUCE / SELL"
---

# C2: Cycle Phase Detection

> Determines where the stock sits in its business cycle using a 4-component
> composite scoring model. The phase classification drives position sizing
> and entry/exit decisions.
>
> **Key insight**: Higher score = more trough-like = better buying opportunity.

---

## 5-Phase Model

| Phase | Score Range | Name | Action |
|-------|------------|------|--------|
| 1 | >= 0.80 | Deep Trough | BUY (max position) |
| 2 | 0.65 - 0.80 | Early Recovery | BUY (standard) |
| 3 | 0.40 - 0.65 | Mid-Cycle | HOLD only |
| 4 | 0.20 - 0.40 | Late Cycle | REDUCE |
| 5 | < 0.20 | Peak | SELL / AVOID |

---

## Composite Score Formula

```
Composite = 0.40 x Company + 0.35 x Sector + 0.15 x Macro + 0.10 x Price
```

Each component produces a score from 0.0 (peak conditions) to 1.0 (deep trough).

---

## Component 1: Company Fundamentals (40%)

Score the company's current financial position relative to its own 5-year history.

### Revenue Position (45% of company score)

```
Revenue_Percentile = (Current_Revenue - Min_5yr) / (Max_5yr - Min_5yr)
Revenue_Score = 1.0 - Revenue_Percentile
```

Low revenue relative to 5-year range = trough signal.

### EBITDA Margin Position (35% of company score)

```
Current_Margin = Current_EBITDA / Current_Revenue
Margin_Percentile = (Current_Margin - Min_5yr_Margin) / (Max_5yr_Margin - Min_5yr_Margin)
Margin_Score = 1.0 - Margin_Percentile
```

Compressed margins = trough signal.

### Capex Trend (20% of company score)

| Capex YoY Change | Score | Interpretation |
|-------------------|-------|---------------|
| < -15% | 0.85 | Deep cuts -- trough behavior |
| -15% to -5% | 0.70 | Cutting -- approaching trough |
| -5% to +5% | 0.50 | Stable -- mid-cycle |
| +5% to +15% | 0.30 | Growing -- expansion |
| > +15% | 0.15 | Rapid growth -- peak behavior |

Companies cut capex at troughs and increase it at peaks.

### Company Score Calculation

```
Company_Score = 0.45 x Revenue_Score + 0.35 x Margin_Score + 0.20 x Capex_Score
```

---

## Component 2: Sector Indicators (35%)

Use commodity prices and sector indices as cycle indicators.

### Sector Indicator Mapping

| Sector | Primary Indicator | Symbol |
|--------|-------------------|--------|
| Energy (Oil & Gas) | WTI Crude Oil | CL=F |
| Semiconductors | PHLX Semiconductor Index | ^SOX |
| Shipping | Baltic Dry Index (BDRY proxy) | BDRY |
| Mining / Metals | Copper Futures | HG=F |
| Steel | VanEck Steel ETF | SLX |
| Chemicals | Dow Jones US Chemicals | (sector ETF) |
| Airlines | JETS ETF | JETS |

### Indicator Percentile Score (65% of sector score)

```
Indicator_Percentile = (Current - 5yr_Low) / (5yr_High - 5yr_Low)
Sector_Percentile_Score = 1.0 - Indicator_Percentile
```

Low commodity price = trough = high score.

### Trend Score (35% of sector score)

| 12M Change | Score | Interpretation |
|------------|-------|---------------|
| < -30% | 0.90 | Crash -- deep trough |
| -30% to -15% | 0.75 | Declining -- trough forming |
| -15% to 0% | 0.55 | Weak -- possible trough |
| 0% to +15% | 0.35 | Recovering -- early cycle |
| > +15% | 0.15 | Strong -- mid/late cycle |

### Sector Score Calculation

```
Sector_Score = 0.65 x Percentile_Score + 0.35 x Trend_Score
```

---

## Component 3: Macro Overlay (15%)

Broad economic indicators that affect all cyclical stocks.

### Yield Curve (40% of macro score)

| 10Y-2Y Spread | Score | Interpretation |
|----------------|-------|---------------|
| < -0.50% | 0.85 | Deeply inverted -- recession imminent |
| -0.50% to 0% | 0.70 | Inverted -- late cycle stress |
| 0% to +0.50% | 0.50 | Flat -- uncertain |
| +0.50% to +1.50% | 0.35 | Normal -- expansion |
| > +1.50% | 0.20 | Steep -- early expansion |

### Credit Spreads (30% of macro score)

Use HYG (high-yield bond ETF) price as proxy. Low HYG price = wide spreads = stress.

```
Credit_Score = 1.0 - (HYG_5yr_Percentile / 100)
```

### Interest Rate Environment (30% of macro score)

| 10Y Yield Percentile (5yr) | Score | Interpretation |
|----------------------------|-------|---------------|
| > 80% | 0.70 | High rates -- restrictive, trough-inducing |
| 60-80% | 0.55 | Elevated -- late cycle |
| 40-60% | 0.40 | Normal |
| < 40% | 0.30 | Low rates -- expansion |

### Macro Score Calculation

```
Macro_Score = 0.40 x Yield_Curve_Score + 0.30 x Credit_Score + 0.30 x Rate_Score
```

---

## Component 4: Price Position (10%)

Simple price-based contrarian signal.

```
Price_Percentile = (Current_Price - 5yr_Low) / (5yr_High - 5yr_Low)
Price_Score = 1.0 - Price_Percentile
```

Stock near 5-year low = trough = high score. Also consider 200-day MA trend:
price below 200-day MA adds +0.10 to Price_Score (capped at 1.0).

---

## Cross-Validation Rules

1. **Divergence check**: If Company says trough but Sector says peak, flag
   as "company-specific distress" (may be structural, not cyclical).

2. **Sector confirmation**: Ideally Company + Sector agree within 1 phase.
   If they diverge by 2+ phases, reduce confidence and note in report.

3. **Macro override**: If Macro says deep recession (score > 0.80) and
   Company shows moderate trough, upgrade the assessment by 0.5 phase.

---

## Output Format

```
C2 Cycle Phase Detection

Composite Score: X.XXXX
Phase: X -- [Phase Name]
Action: [BUY_MAX / BUY_STD / HOLD / REDUCE / SELL]

Score Breakdown:
| Component | Weight | Score  | Weighted |
|-----------|--------|--------|----------|
| Company   | 40%    | X.XXXX | X.XXXX   |
| Sector    | 35%    | X.XXXX | X.XXXX   |
| Macro     | 15%    | X.XXXX | X.XXXX   |
| Price     | 10%    | X.XXXX | X.XXXX   |
| Composite | 100%   | --     | X.XXXX   |

Company Details:
  Revenue percentile: XX.X% (5yr range)
  EBITDA margin percentile: XX.X%
  Capex YoY change: +/-XX.X%

Sector Details:
  Primary indicator: [Name] at XX.X% of 5yr range
  12M change: +/-XX.X%

Macro Details:
  Yield curve spread: X.XX%
  Credit conditions: [Tight / Normal / Loose]

Price Details:
  Stock at XX.X% of 5yr range
  vs 200-day MA: [Above / Below]
```

```json
{
  "composite_score": 0.72,
  "phase": 2,
  "phase_name": "Early Recovery",
  "company_score": 0.78,
  "sector_score": 0.68,
  "macro_score": 0.55,
  "price_score": 0.82,
  "action": "BUY_STD"
}
```
