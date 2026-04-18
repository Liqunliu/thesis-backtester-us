---
id: cigar_fact_check
name: "Cigar Butt Fact Check (6 Veto Checks)"
category: screening
tags: [fact-check, veto, cigar, risk, deep-value]
data_needed: [balancesheet, income, cashflow, indicator]
outputs:
  - field: fact_check_pass
    type: bool
    desc: "true if no veto items triggered (rating A, B, or B+)"
  - field: veto_reason
    type: str
    desc: "Description of veto trigger if failed, empty string if passed"
  - field: warnings
    type: str
    desc: "Comma-separated list of warning items, empty string if none"
  - field: fact_check_rating
    type: str
    desc: "Rating: A (all pass), B (1-2 warnings), B+ (B + bonus >= 2), C (3+ warnings), D (veto)"
  - field: goodwill_pct
    type: float
    desc: "Goodwill / Total Assets (%)"
  - field: veto_items_count
    type: int
    desc: "Number of veto items triggered"
  - field: warning_items_count
    type: int
    desc: "Number of warning items flagged"
---

# Cigar Butt Fact Check: 6 Core Veto Checks

Screen for hidden risks not captured by the 3-pillar quantitative framework.
Any single veto = automatic D rating = **DO NOT INVEST**.

## Rating Summary

| Rating | Criteria | Position Impact |
|--------|----------|----------------|
| **A** | All items pass, no warnings | Full position per tier rules |
| **B** | Core items pass, 1-2 warning items | 80% of max position |
| **B+** | Base B + bonus items score >= 2 points | Full position per tier rules |
| **C** | 3+ warning items OR 1 item approaching veto | 50% of max position |
| **D** | Any automatic-veto item triggered | **DO NOT INVEST** |

## Veto Check 1: Goodwill Ratio

| Metric | Formula | Threshold |
|--------|---------|-----------|
| Goodwill Ratio | Goodwill / Total Assets | WARNING: 15-30%; VETO: > 30% |

**Context by sector**:
- Financial services: 5-10% typical
- Technology: 20-40% common (acquisitive)
- Manufacturing: 10-20% typical
- If goodwill > 30%, check for impairment history (material impairment in last 3 years amplifies concern)

**Impact on NAV**: Goodwill is not realizable in liquidation. High goodwill means the balance sheet overstates tangible asset value, undermining the entire cigar butt thesis.

## Veto Check 2: Restricted Cash Ratio

| Metric | Formula | Threshold |
|--------|---------|-----------|
| Restricted Cash Ratio | Restricted Cash / Total Cash | VETO: > 20% |

**Data source**: 10-K Balance Sheet footnotes, Note on Cash & Equivalents. Search for "restricted cash", "pledged", "segregated".

**Impact on NAV**: Restricted cash must be subtracted from Cash & Equivalents in ALL T-level calculations. If > 20%, the cash figures used in Pillar 1 are materially overstated.

## Veto Check 3: Off-Balance-Sheet Liabilities

| Metric | Formula | Threshold |
|--------|---------|-----------|
| Off-BS Liabilities / Market Cap | Off-BS obligations / Market Cap | VETO: > 15% |

**Data source**: 10-K footnotes on commitments, contingencies, VIEs. Search for "off-balance sheet", "variable interest entity", "special purpose", "guarantees".

**Common off-BS items**: Purchase obligations, guarantees, unconsolidated entities, pending litigation with quantifiable exposure.

## Veto Check 4: Pension Deficit

| Metric | Formula | Threshold |
|--------|---------|-----------|
| Pension Deficit / Market Cap | (PBO - Plan Assets) / Market Cap | VETO: > 10% |

**Data source**: 10-K pension footnote (ASC 715). Search for "defined benefit", "pension", "projected benefit obligation".

**Impact on NAV**: A pension deficit is an off-balance-sheet liability that reduces the true net asset value. For cigar butt stocks (already trading near NAV), even a moderate pension deficit can eliminate the margin of safety.

## Veto Check 5: Revenue Concentration

| Metric | Formula | Threshold |
|--------|---------|-----------|
| Top-5 Customer Concentration | Top 5 customers / Total Revenue | VETO: > 60% (without long-term contracts) |

**Data source**: 10-K revenue disaggregation, customer concentration footnote. Search for "major customers", "significant customers", "concentration".

**Why this matters for cigar butts**: High customer concentration means revenue (and therefore cash flow) is fragile. Loss of a single customer could accelerate NAV erosion, violating the Pillar 2 operating maintenance assumption.

## Veto Check 6: Q4 Revenue Spike

| Metric | Formula | Threshold |
|--------|---------|-----------|
| Q4 Revenue Share | Q4 Revenue / Annual Revenue | VETO: > 40% |

**Data source**: 10-Q quarterly revenue comparison. Can be computed from quarterly financials if available.

**Concern**: Extreme Q4 seasonality may indicate channel stuffing or aggressive revenue recognition. For a cigar butt, this means reported revenue (and derived NAV components like receivables) may be inflated.

## Additional Warning Items

Beyond the 6 core veto checks, flag the following as warnings (contribute to rating but do not independently veto):

| Item | Threshold | Status |
|------|-----------|--------|
| Other Payables / Total Liabilities | > 30% without explanation | WARNING |
| Related-party Revenue / Total Revenue | > 30% | WARNING |
| Qualified / Adverse audit opinion | Any non-clean opinion | WARNING |
| Recent auditor change (past 2 years) | Without clear reason | WARNING |
| DIO rising 3 consecutive years | AND > 50% above peers | WARNING |
| Goodwill impairment in last 3 years | > 5% of goodwill | WARNING |

## Bonus Items (can upgrade B to B+)

### Bonus 1: Listed Subsidiary / Associate Value

| Coverage Ratio | Points |
|---------------|--------|
| > 100% of parent market cap | +3 pts |
| 50-100% | +2 pts |
| 20-50% | +1 pt |
| < 20% | +0 pts |

### Bonus 2: Ownership & Governance Quality

| Factor | Points |
|--------|--------|
| High insider ownership (> 10%) | +3 pts |
| Institutional ownership > 70% | +2 pts |
| Activist investor involved (13D filing) | +1 pt |

**B+ upgrade rule**: If base rating is B AND total bonus points >= 2, upgrade to B+.

## Analysis Steps

1. For each of the 6 veto checks, compute the metric and compare to the threshold.
2. If ANY veto triggers: set `fact_check_pass = false`, `fact_check_rating = "D"`, and record the veto reason.
3. Count warning items from the additional checks.
4. If no veto but 3+ warnings: set rating to "C".
5. If no veto and 1-2 warnings: set rating to "B". Check bonus items for B+ upgrade.
6. If no veto and no warnings: set rating to "A".
7. Record `goodwill_pct` for cross-reference with Pillar 1.

## Output Format

```json
{
  "fact_check_pass": true,
  "veto_reason": "",
  "warnings": "DIO rising 3 years, other payables 32% of liabilities",
  "fact_check_rating": "B",
  "goodwill_pct": 8.5,
  "veto_items_count": 0,
  "warning_items_count": 2
}
```
