---
id: factor_c1_survival
name: "C1: Survival & Quality Gate"
category: cyclical
tags: [c1, survival, liquidity, leverage, cyclicality, gate]
data_needed: [income, cashflow, balancesheet]
gate:
  veto: true
outputs:
  - field: c1_pass
    type: bool
    desc: "True if all survival gates passed and stock confirmed cyclical"
  - field: current_ratio
    type: float
    desc: "Current Assets / Current Liabilities"
  - field: interest_coverage
    type: float
    desc: "Trough EBITDA / Interest Expense (using min 5yr EBITDA)"
  - field: debt_to_ebitda
    type: float
    desc: "Net Debt / Mid-Cycle EBITDA (median 5yr)"
  - field: cash_runway_months
    type: float
    desc: "Months of cash runway at trough burn rate"
  - field: revenue_cv
    type: float
    desc: "Coefficient of variation of 5yr revenue (StdDev/Mean)"
  - field: is_cyclical
    type: bool
    desc: "True if CV(Revenue) >= 15% OR CV(EBITDA) >= 30%"
---

# C1: Survival & Quality Gate

> Binary PASS/VETO gate. Stocks that fail C1 are excluded from further
> cyclical analysis. The goal is to ensure the company can survive the
> current cycle trough and emerge stronger.

---

## C1-A: Current Ratio (Liquidity)

**Gate**: Current Ratio >= 1.0

```
Current Ratio = Current Assets / Current Liabilities
```

From the balance sheet, compute the ratio. Companies below 1.0 may not have
enough liquid assets to cover near-term obligations during a trough.

| Current Ratio | Verdict |
|---------------|---------|
| >= 1.5        | PASS (comfortable) |
| 1.0 - 1.5    | PASS (adequate) |
| < 1.0         | VETO |

---

## C1-B: Interest Coverage at Trough

**Gate**: Interest Coverage >= 1.5x (using trough EBITDA)

```
Trough EBITDA = MIN(5yr annual EBITDA)
Interest Coverage = Trough EBITDA / Annual Interest Expense
```

Use the minimum EBITDA from the last 5 years. If the company cannot cover
interest at its worst point, it risks default during a downturn.

| Coverage | Verdict |
|----------|---------|
| >= 3.0   | PASS (strong) |
| 1.5 - 3.0 | PASS (adequate) |
| < 1.5    | VETO |

---

## C1-C: Net Debt / Mid-Cycle EBITDA

**Gate**: Net Debt / Mid-Cycle EBITDA <= 3.0x

```
Net Debt = Total Debt - Cash & Equivalents
Mid-Cycle EBITDA = Median(5yr EBITDA)
Leverage = Net Debt / Mid-Cycle EBITDA
```

Use the 5-year median EBITDA as the "normal" earnings power. This strips
out cyclical extremes. Companies with leverage > 3.0x at normalized earnings
carry excessive risk during prolonged downturns.

| Leverage | Verdict |
|----------|---------|
| <= 1.5   | PASS (conservative) |
| 1.5 - 3.0 | PASS (moderate) |
| > 3.0    | VETO |

---

## C1-D: Cash Runway

**Gate**: Cash Runway >= 18 months at trough burn rate

```
Monthly Burn = (Trough Revenue - Trough EBITDA) / 12
  Use worst-year Revenue and EBITDA from last 5 years
Cash Buffer = Current Cash + MIN(5yr OCF, 0)
  If OCF was negative at trough, subtract it from cash
Runway Months = Cash Buffer / Monthly Burn
```

If Monthly Burn is negative (company is profitable even at trough), PASS
automatically with infinite runway.

| Runway | Verdict |
|--------|---------|
| >= 24 months | PASS (strong buffer) |
| 18 - 24 months | PASS (adequate) |
| < 18 months | VETO |

---

## C1-E: Cyclicality Confirmation

The stock must actually be cyclical. Non-cyclical stocks should use the
Quality Yield framework instead.

**At least ONE criterion must be met**:

| Metric | Threshold | Calculation |
|--------|-----------|-------------|
| CV(Revenue) | >= 0.15 (15%) | StdDev(5yr Revenue) / Mean(5yr Revenue) |
| CV(EBITDA) | >= 0.30 (30%) | StdDev(5yr EBITDA) / Mean(5yr EBITDA) |

### Classification

| CV(Revenue) | CV(EBITDA) | Classification |
|-------------|------------|----------------|
| >= 0.15 | >= 0.30 | Strongly cyclical |
| >= 0.15 | < 0.30 | Moderately cyclical (revenue-driven) |
| < 0.15 | >= 0.30 | Moderately cyclical (margin-driven) |
| < 0.15 | < 0.30 | Non-cyclical -> redirect to Quality Yield |

---

## C1-F: Basic Quality Filters

Qualitative checks (soft filters -- flag concerns but do not auto-veto unless fraud):

| # | Check | Action |
|---|-------|--------|
| 1 | No fraud history | Check filings for fraud flags, restatements |
| 2 | Understandable business | Can you explain the business in 2 sentences? |
| 3 | Survived prior cycle | Has the company existed >= 10 years? Survived 2008 or 2020? |
| 4 | Adequate governance | No major related-party concerns, reasonable insider ownership |

---

## C1 Final Verdict

```
Factor C1 Survival & Quality: [PASS / VETO]

  C1-A Liquidity:           [PASS (CR=X.XX)] / [VETO (CR=X.XX < 1.0)]
  C1-B Interest Coverage:   [PASS (X.Xx >= 1.5)] / [VETO (X.Xx < 1.5)]
  C1-C Leverage:            [PASS (X.Xx <= 3.0)] / [VETO (X.Xx > 3.0)]
  C1-D Cash Runway:         [PASS (XX months >= 18)] / [VETO (XX months < 18)]
  C1-E Cyclicality:         [PASS (CV_Rev=XX%, CV_EBITDA=XX%)] / [REDIRECT TO QY]
  C1-F Quality:             [PASS] / [CAUTION (reason)]

  Conclusion: [This stock passes the survival gate and is confirmed cyclical.
               Proceed to C2 Cycle Phase Detection.]
              OR
              [VETO: (reason). Exclude from cyclical strategy.]
```

```json
{
  "c1_pass": true,
  "current_ratio": 1.85,
  "interest_coverage": 3.2,
  "debt_to_ebitda": 1.8,
  "cash_runway_months": 36.0,
  "revenue_cv": 0.22,
  "is_cyclical": true
}
```
