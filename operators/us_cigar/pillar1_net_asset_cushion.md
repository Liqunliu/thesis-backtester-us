---
id: pillar1_net_asset_cushion
name: "Pillar 1 — Net Asset Cushion (T0/T1/T2)"
category: valuation
tags: [pillar1, nav, deep-value, cigar, balance-sheet]
data_needed: [balancesheet, indicator]
outputs:
  - field: t0_nav
    type: float
    desc: "T0 NAV per share: (Cash - Total Liabilities) / Shares"
  - field: t1_nav
    type: float
    desc: "T1 NAV per share: (Cash - Interest-Bearing Debt) / Shares"
  - field: t2_nav
    type: float
    desc: "T2 NAV per share: (Adjusted Current Assets - Total Liabilities) / Shares"
  - field: best_tier
    type: str
    desc: "Best qualifying tier: T0, T1, T2, or NONE"
  - field: entry_price
    type: float
    desc: "Maximum entry price based on best tier NAV and required discount"
  - field: nav_discount_pct
    type: float
    desc: "Current price discount to best-tier NAV (%)"
  - field: pillar1_pass
    type: bool
    desc: "true if at least one tier qualifies (price < entry threshold)"
---

# Pillar 1: Net Asset Cushion

Determine whether the stock's static net asset value exceeds its market capitalization.
This is the core margin-of-safety test for the cigar butt strategy.

Three tiers of increasing conservatism:

| Tier | Formula | Meaning |
|------|---------|---------|
| **T0** | (Cash - Total Liabilities) / Shares | Net cash far exceeds all obligations; ultra-conservative |
| **T1** | (Cash - Interest-Bearing Debt) / Shares | Cash covers hard debt; moderate conservatism |
| **T2** | (Adjusted Current Assets - Total Liabilities) / Shares | Wider asset base with liquidation haircuts |

## T0 NAV: Pure Net Cash

```
T0_NAV_Total = Cash_and_Equivalents - Total_Liabilities
T0_NAV_Per_Share = T0_NAV_Total / Shares_Outstanding
Entry Price < T0_NAV_Per_Share * 0.85
```

**Include in Cash**: Cash, money market funds, Treasury bills (< 3 months), short-term investments, certificates of deposit.
**Exclude from Cash**: Restricted cash (see fact check), pledged deposits, margin accounts.

## T1 NAV: Cash vs Interest-Bearing Debt

```
T1_NAV_Total = Cash_and_Equivalents - Interest_Bearing_Debt
T1_NAV_Per_Share = T1_NAV_Total / Shares_Outstanding
Entry Price < T1_NAV_Per_Share * 0.80
```

**Interest-Bearing Debt (IBD)** includes: Short-term borrowings, current portion of LT debt, long-term debt, finance lease liabilities, convertible debt.
**Exclude from IBD**: Accounts payable, accrued expenses, deferred revenue, operating leases.

## T2 NAV: Adjusted Current Assets

```
T2_NAV_Total = Cash * 1.00 + AR * 0.85 + Inventory * Sector_Discount
             + Other_Current_Assets * 0.50 - Total_Liabilities
T2_NAV_Per_Share = T2_NAV_Total / Shares_Outstanding
Entry Price < T2_NAV_Per_Share * 0.70
```

### Haircut Coefficients

| Asset | Coefficient | Rationale |
|-------|-------------|-----------|
| Cash & Equivalents | 1.00 | Face value, most liquid |
| Accounts Receivable | 0.85 | 15% haircut for bad debt, collection risk |
| Inventory - Consumer/Retail | 0.80 | Branded goods retain value |
| Inventory - Manufacturing/Industrial | 0.70 | WIP and raw materials less liquid |
| Inventory - Electronics/Technology | 0.50 | Rapid obsolescence |
| Inventory - Pharmaceutical | 0.40 | Regulatory, expiry risk |
| Inventory - Default | 0.65 | Conservative mid-point |
| Other Current Assets | 0.50 | Prepaid, deposits -- partially recoverable |

### Additional AR Adjustments

- **AR > 90 days**: Apply 0.70 coefficient instead of 0.85
- **Related-party AR > 20%**: Apply 0.50 coefficient to related-party portion
- **Single customer > 30% of AR**: Apply 0.75 coefficient

### Additional Inventory Adjustments

- **DIO rising 3+ consecutive years**: Apply sector discount * 0.80
- **DIO > 50% above peer median**: Apply sector discount * 0.70
- **Write-downs in last 2 years**: Apply sector discount * 0.85

## Special Treatments

1. **Deferred Revenue**: Do NOT subtract from liabilities. It represents an obligation to deliver, not a cash liability. Keeping it in Total Liabilities is conservative.

2. **Restricted Cash**: Must be subtracted from Cash & Equivalents. VETO if restricted cash > 20% of total cash (handled in fact check).

3. **Operating Leases (ASC 842)**: Under ASC 842, operating lease liabilities are on the balance sheet. For T0/T1, they are already in Total Liabilities (conservative). For T2, do NOT double-count.

4. **ROU Assets**: Do NOT include right-of-use assets in T2 numerator (non-liquid).

5. **Pledged Assets**: Subtract pledged asset value from T2 numerator. Pledged assets cannot be liquidated freely.

## Analysis Steps

1. Extract all balance sheet line items needed for T0, T1, and T2 calculations.
2. Identify the appropriate inventory discount based on the company's sector.
3. Calculate T0_NAV, T1_NAV, and T2_NAV per share.
4. Compare current price against each tier's entry threshold.
5. Classify the best qualifying tier.
6. Note any special adjustments (restricted cash, pledged assets, lease adjustments).

## Entry Price Thresholds

| Tier | Discount Required | Entry Price |
|------|-------------------|-------------|
| T0 | 15% | < T0_NAV * 0.85 |
| T1 | 20% | < T1_NAV * 0.80 |
| T2 | 30% | < T2_NAV * 0.70 |

Higher tiers require smaller discounts because the underlying assets are more liquid and certain.

## Output Format

```json
{
  "t0_nav": -2.50,
  "t1_nav": 12.30,
  "t2_nav": 18.75,
  "best_tier": "T1",
  "entry_price": 9.84,
  "nav_discount_pct": 35.2,
  "pillar1_pass": true
}
```
