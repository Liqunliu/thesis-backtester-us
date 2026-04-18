---
id: factor_c3_normalized_value
name: "C3: Normalized Valuation & Entry"
category: cyclical
tags: [c3, normalized-gg, mid-cycle, valuation, entry-signal]
data_needed: [income, cashflow, balancesheet, market_data]
outputs:
  - field: normalized_gg
    type: float
    desc: "Normalized GG yield (%) using median OCF/CapEx over 5 years"
  - field: gg_vs_threshold
    type: float
    desc: "Normalized GG minus Threshold II (7.3%), in percentage points"
  - field: discount_to_midcycle_pct
    type: float
    desc: "Discount to mid-cycle fair value (%)"
  - field: normalized_oe
    type: float
    desc: "Normalized Owner Earnings ($M) using median cash flows"
---

# C3: Normalized Valuation & Entry

> Uses mid-cycle (normalized) cash flows instead of TTM to value cyclical
> stocks fairly regardless of where they are in the cycle. TTM values for
> cyclical stocks are misleading -- they reflect the current phase, not
> the company's sustainable earning power.

---

## Normalized GG Formula

```
Normalized_AA = Median(5yr OCF) - Median(5yr CapEx)
              + Avg(3yr Buybacks) - Avg(3yr Dividends) - Avg(3yr SBC)

Normalized_GG = Normalized_AA / Current_Market_Cap x 100
```

### Why Median Instead of Average?

- **Median** is robust to outlier years (a single boom or bust year does not
  distort the result).
- OCF and CapEx can swing wildly in cyclical industries. Median captures
  the "normal" operating level.
- Uses **5-year window** for OCF/CapEx (captures at least one mini-cycle).
- Uses **3-year window** for shareholder returns (more stable, policy-driven).

### SBC Adjustment

SBC is subtracted because it dilutes shareholders. Use the 3-year average
to smooth any one-time equity grants.

---

## Calculation Detail

```
From 5-year cashflow history (sorted by fiscal year):

  OCF values: [Y1, Y2, Y3, Y4, Y5]
  Median OCF = [value] $M

  CapEx values: [Y1, Y2, Y3, Y4, Y5]
  Median CapEx = [value] $M

From 3-year cashflow history:

  Buybacks: [Y3, Y4, Y5]
  Avg Buybacks = [value] $M

  Dividends Paid: [Y3, Y4, Y5]
  Avg Dividends = [value] $M

  Stock-Based Compensation: [Y3, Y4, Y5]
  Avg SBC = [value] $M

Normalized AA:
  = Median_OCF - Median_CapEx + Avg_Buybacks - Avg_Dividends - Avg_SBC
  = [value] $M

Current Market Cap = [value] $M

Normalized GG = Normalized_AA / Market_Cap x 100 = [value]%
Threshold II = 7.30%
GG vs Threshold = [value] percentage points
```

---

## Discount to Mid-Cycle Fair Value

Compute how much the stock trades below its estimated mid-cycle price.

```
Mid_Cycle_EPS = Median(5yr EPS)
  If EPS data unavailable: Median(5yr Net Income) / Current Shares Outstanding

Mid_Cycle_PE = Median(5yr PE)
  If PE data unavailable: use sector average PE

Mid_Cycle_Price = Mid_Cycle_EPS x Mid_Cycle_PE

Discount = (1 - Current_Price / Mid_Cycle_Price) x 100
```

If Mid_Cycle_Price cannot be computed (missing data), use alternative:
```
Alternative: Current price percentile in 5yr range <= 35%
```

Entry threshold: Discount to mid-cycle >= 15%.

---

## TTM GG vs Normalized GG Comparison

Always compute both and present side by side:

```
| Method | GG | vs Threshold | Status |
|--------|------|-------------|--------|
| TTM GG (QY) | X.XX% | +/-X.XX pct | PASS/FAIL |
| Normalized GG (Cyclical) | X.XX% | +/-X.XX pct | PASS/FAIL |
| Gap (Normalized - TTM) | X.XX pct | -- | [Cyclical premium / No premium] |
```

### Gap Interpretation

| Gap | Meaning |
|-----|---------|
| > +5 pct | Stock is deeply cyclical and currently at trough |
| +2 to +5 pct | Moderately cyclical, trough impact visible |
| 0 to +2 pct | Mildly cyclical or near mid-cycle |
| < 0 pct | Stock may be at peak -- TTM overstates earning power |

---

## Entry Signal Requirements

**ALL four must be met** for a BUY signal:

| # | Requirement | Threshold |
|---|-------------|-----------|
| 1 | C1 Survival Gate | PASS |
| 2 | C2 Cycle Phase | Phase 1 (Deep Trough) or Phase 2 (Early Recovery) |
| 3 | Normalized GG | >= 7.30% (Threshold II) |
| 4 | Discount to Mid-Cycle | >= 15% below mid-cycle price |

---

## Normalized Owner Earnings

For cross-reference with QY framework:

```
Normalized_OE = Median(5yr Net Income) + Median(5yr D&A) - Median(5yr Maintenance CapEx)
```

This provides a normalized earnings view that strips cyclical distortions
from the owner earnings calculation.

---

## Output Format

```
Factor C3 Normalized Valuation & Entry

Normalized GG: X.XX%
TTM GG (QY): X.XX%
Cyclical Premium: +X.XX pct

Threshold II: 7.30%
GG vs Threshold: +/-X.XX pct -> [PASS / FAIL]

Discount to Mid-Cycle: XX.X% -> [PASS (>= 15%) / FAIL]
  Mid-Cycle EPS: $X.XX
  Mid-Cycle PE: X.Xx
  Mid-Cycle Price: $XX.XX
  Current Price: $XX.XX

Entry Signal Check:
  C1 Survival: [PASS/VETO]
  C2 Phase: X -- [Name] (Score X.XXXX)
  Normalized GG >= 7.30%: [PASS/FAIL]
  Discount >= 15%: [PASS/FAIL]

Entry Decision: [BUY / HOLD / WAIT / AVOID]

Normalized Owner Earnings: $X,XXXM
```

```json
{
  "normalized_gg": 9.45,
  "gg_vs_threshold": 2.15,
  "discount_to_midcycle_pct": 28.5,
  "normalized_oe": 3200.0
}
```
