---
id: distribution_capacity
name: "Distribution Capacity Verification (F2 Step 2)"
category: quantitative
tags: [f2, distribution, fcf, veto, buyback]
data_needed: [cashflow]
outputs:
  - field: distribution_capacity_pass
    type: bool
    desc: "False = VETO (cannot sustain distributions)"
  - field: fcf_3yr_positive
    type: bool
    desc: "True if FCF positive for at least 3 of 5 years"
  - field: financing_cf_pattern
    type: str
    desc: "Net borrower / Net repayer / Mixed"
  - field: buyback_sustainability
    type: str
    desc: "Sustainable / Unsustainable / N/A"
  - field: net_shareholder_return
    type: float
    desc: "Buybacks + Dividends - SBC dilution cost ($M)"
---

# F2 Step 2: Distribution Capacity Verification (Veto Gate)

Can this company actually pay out what the numbers say?

## Cash Flow Pattern Analysis

List past 3-5 years:

| Year | Operating CF | Investing CF | Free CF | Financing CF | Ending Cash |
|------|-------------|-------------|---------|-------------|-------------|

## Veto Rules

```
IF FCF consistently negative AND financing CF consistently positive
  → Company is borrowing to fund operations → Pseudo-distribution → VETO
```

## US-Specific: Share Buyback Sustainability

```
Annual buybacks = [value] $M
Annual SBC expense = [value] $M
Net shareholder return = Buybacks + Dividends - SBC dilution cost

IF net_shareholder_return < 0
  → Company is extracting value via SBC, not returning it
  → Flag "Value extraction via SBC" (warning, not auto-veto)
```

## Judgment

- FCF consistently positive (3+ of 5 years)? → PASS
- FCF mixed but OCF strong? → Marginal (proceed with caution)
- FCF negative + debt-funded distributions? → VETO

```json
{
  "distribution_capacity_pass": true,
  "fcf_3yr_positive": true,
  "financing_cf_pattern": "Net repayer",
  "buyback_sustainability": "Sustainable",
  "net_shareholder_return": 3200.0
}
```
