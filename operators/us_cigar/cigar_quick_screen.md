---
id: cigar_quick_screen
name: "Cigar Butt Quick Screen"
category: screening
tags: [screening, veto, cigar, pb-gate, tier-eligibility]
data_needed: [balancesheet, indicator]
outputs:
  - field: cigar_pass
    type: bool
    desc: "true if stock passes quick screen and qualifies for at least one NAV tier"
  - field: eligible_tier
    type: str
    desc: "Best eligible tier: T0, T1, T2, or none"
  - field: pb_zone
    type: str
    desc: "P/B classification: deep-value (<=0.50), value (0.51-0.70), neutral (0.71-1.00), premium (>1.00)"
  - field: quick_screen_notes
    type: str
    desc: "One-sentence summary of eligibility assessment"
---

# Cigar Butt Quick Screen

Rapid gate check to determine if a stock qualifies for cigar butt deep value analysis.
This operator performs a P/B gate and preliminary NAV tier eligibility before committing
to the full 3-pillar framework.

## Step 1: P/B Gate

Classify the stock's P/B ratio into zones:

| Zone | P/B Range | Assessment |
|------|-----------|------------|
| Deep Value | <= 0.50 | Strong cigar butt candidate |
| Value | 0.51 - 0.70 | Moderate discount, may qualify |
| Neutral | 0.71 - 1.00 | Near book, unlikely candidate |
| Premium | > 1.00 | Above book, not a cigar butt |

**Gate rule**: P/B must be <= 0.70 to proceed. If P/B > 0.70, set `cigar_pass = false`
and `eligible_tier = "none"`.

## Step 2: Industry Exclusion Check

The following industries are excluded because NAV-based analysis is not meaningful:
- Banks (deposit-taking distorts liabilities)
- Insurance (float distorts liabilities)
- Asset Management / Capital Markets (need fund NAV, not balance sheet NAV)
- Mortgage Finance / Credit Services (leverage-heavy like banks)
- REIT - Mortgage (leverage-heavy)

If the stock is in an excluded industry, set `cigar_pass = false`.

## Step 3: Preliminary NAV Tier Check

Using available balance sheet data, perform a quick directional check:

1. **T0 feasibility**: Does `Cash & Equivalents > Total Liabilities`?
   - If yes, T0 tier is potentially available (strongest)

2. **T1 feasibility**: Does `Cash & Equivalents > Interest-Bearing Debt`?
   - If yes, T1 tier is potentially available

3. **T2 feasibility**: Does `Current Assets > Total Liabilities`?
   - If yes, T2 tier is potentially available (weakest but still qualifies)

Set `eligible_tier` to the highest feasible tier (T0 > T1 > T2).
If none qualify, set `eligible_tier = "none"` and `cigar_pass = false`.

## Step 4: Basic Viability Checks

Quick sanity checks (any failure = `cigar_pass = false`):

1. **Market cap >= $300M**: Ensures minimum liquidity and institutional relevance
2. **Not a shell company**: Revenue must be > $0 in latest year
3. **Shares outstanding available**: Required for per-share NAV calculations
4. **Financial data available**: Must have at least 3 years of balance sheet history

## Decision

- If P/B gate passes AND industry is not excluded AND at least one tier is feasible AND viability checks pass:
  - Set `cigar_pass = true`
  - Set `eligible_tier` to the best feasible tier
- Otherwise:
  - Set `cigar_pass = false`
  - Set `eligible_tier = "none"`

## Output Format

```json
{
  "cigar_pass": true,
  "eligible_tier": "T1",
  "pb_zone": "deep-value",
  "quick_screen_notes": "P/B 0.42, cash exceeds IBD, T1 tier feasible, manufacturing sector"
}
```
