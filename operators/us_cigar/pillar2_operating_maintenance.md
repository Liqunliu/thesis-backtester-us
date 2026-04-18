---
id: pillar2_operating_maintenance
name: "Pillar 2 — Operating Maintenance (FCF + ABR)"
category: quantitative
tags: [pillar2, fcf, abr, cash-burn, operating, cigar]
data_needed: [cashflow, balancesheet, income]
outputs:
  - field: abr_pct
    type: float
    desc: "Asset Burn Rate: (Cash_t - Cash_t-1) / Cash_t-1, as percentage"
  - field: abr_pass
    type: str
    desc: "ABR verdict for the assigned tier: PASS, WARNING, or VETO"
  - field: fcf_positive
    type: bool
    desc: "true if latest fiscal year FCF > 0"
  - field: years_of_cash_runway
    type: float
    desc: "Estimated years of cash remaining at current burn rate (Inf if ABR >= 0)"
  - field: pillar2_conditions_met
    type: int
    desc: "Number of conditions met out of 3"
  - field: pillar2_pass
    type: bool
    desc: "true if 2/3 or 3/3 conditions are met"
  - field: fcf_conversion_ratio
    type: float
    desc: "FCF / Net Income ratio"
  - field: consecutive_ocf_years
    type: int
    desc: "Number of consecutive most-recent years with positive OCF"
---

# Pillar 2: Operating Maintenance

Assess whether the company can maintain its asset base without rapidly burning cash.
A stock trading below NAV is only a good cigar butt if the company is not hemorrhaging
cash -- otherwise the NAV floor erodes before the value can be realized.

**Must pass 2 of 3 conditions** to proceed.

## Condition 1: Free Cash Flow > 0

### Formula
```
FCF = Operating Cash Flow - Capital Expenditures
```

- **FCF > 0**: Company generates more cash from operations than it spends on capex. PASS.
- **FCF < 0**: Company is a net cash consumer. Does not automatically VETO -- check if
  negative FCF is due to one-time growth capex vs structural unprofitability.

### FCF Conversion Ratio (supplementary)
```
FCF_Conversion = FCF / Net_Income
```

| Ratio | Interpretation |
|-------|---------------|
| > 1.0 | Excellent -- cash generation exceeds reported earnings |
| 0.8 - 1.0 | Good -- strong cash conversion |
| 0.5 - 0.8 | Acceptable -- some working capital consumption |
| < 0.5 | Warning -- earnings quality concern |

## Condition 2: Asset Burn Rate (ABR)

### Formula
```
ABR = (Cash_t - Cash_t-1) / Cash_t-1
```

Where:
- `Cash_t` = Most recent year-end cash & equivalents
- `Cash_t-1` = Prior year-end cash & equivalents

### Tiered Thresholds

| Tier | PASS | WARNING | VETO |
|------|------|---------|------|
| T0 | ABR >= 0% | -5% <= ABR < 0% | ABR < -5% |
| T1 | ABR >= 5% | -5% <= ABR < 5% | ABR < -5% |
| T2 | ABR >= 10% | 0% <= ABR < 10% | ABR < 0% |

### Rationale for Tiered Thresholds

- **T0** (net cash exceeds market cap): Can tolerate mild cash burn since the safety cushion is enormous.
- **T1** (cash exceeds IBD): Moderate tolerance -- needs cash to service remaining obligations.
- **T2** (adjusted current assets): Strictest -- needs positive cash generation because the asset base includes illiquid items (AR, inventory) that can deteriorate.

### ABR Adjustments

When ABR is negative (cash declining), investigate the source of cash reduction:
- **Share buybacks**: If cash declined due to buybacks, add back buyback amount. Buybacks are value-accretive for below-book stocks.
- **Debt repayment**: If cash declined due to debt reduction, partially acceptable (improves T1 NAV).
- **Operating losses**: Genuine concern -- check if temporary (one-time charges) or structural.
- **Acquisitions**: May be concerning if paid premium; check goodwill creation.

Adjusted ABR formula (when applicable):
```
ABR_Adjusted = (Cash_t - Cash_t-1 + Buybacks_t + DebtRepaid_t) / Cash_t-1
```

## Condition 3: Consecutive Positive OCF

```
OCF > 0 for at least 3 consecutive most-recent years
```

| Years Positive | Assessment |
|---------------|-----------|
| 5+ years | Excellent operating consistency |
| 3-4 years | Acceptable -- meets minimum |
| 2 years | Warning -- borderline |
| 0-1 years | Fail -- unreliable operations |

## Supplementary: SG&A Trend Analysis

```
SGA_Ratio = SG&A_Expenses / Total_Revenue
```

| Trend (3-year) | Assessment |
|----------------|-----------|
| Declining | Positive -- improving efficiency |
| Stable (+-2pp) | Neutral |
| Rising | Warning -- potential cost bloat |

## Supplementary: Working Capital Changes

```
Working_Capital = Current_Assets - Current_Liabilities
WC_Change = WC_t - WC_t-1
```

Concerning patterns:
- Rising AR with flat/declining revenue: Collection problems
- Rising inventory with declining revenue: Potential write-down risk
- Rising payables disproportionate to revenue: Stretching suppliers (liquidity stress)

## Cash Runway Calculation

If ABR is negative:
```
Years_of_Cash_Runway = Cash_t / abs(Cash_t - Cash_t-1)
```

If ABR >= 0, set `years_of_cash_runway` to a large number (e.g., 99) indicating no burn concern.

## Analysis Steps

1. Calculate FCF for the latest fiscal year. Record FCF conversion ratio.
2. Calculate ABR using the two most recent year-end cash positions.
3. Apply ABR to the tier identified in Pillar 1. Record verdict (PASS/WARNING/VETO).
4. If ABR is negative, investigate the source and calculate adjusted ABR if warranted.
5. Count consecutive years of positive OCF going back from the latest year.
6. Tally conditions met (0-3). If >= 2, set `pillar2_pass = true`.
7. Calculate cash runway if ABR is negative.

## Output Format

```json
{
  "abr_pct": -3.2,
  "abr_pass": "WARNING",
  "fcf_positive": true,
  "years_of_cash_runway": 15.6,
  "pillar2_conditions_met": 2,
  "pillar2_pass": true,
  "fcf_conversion_ratio": 0.85,
  "consecutive_ocf_years": 4
}
```
