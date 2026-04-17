---
id: false_advantages
name: "False Advantage Detection (D2-4)"
category: qualitative
tags: [d2, moat, false-moat, validation]
data_needed: [income, balancesheet]
outputs:
  - field: false_advantage_flags
    type: str
    desc: "List of confirmed false advantages, or 'None identified'"
  - field: false_advantage_count
    type: int
    desc: "Number of confirmed false advantages (0-6)"
  - field: moat_downgrade_needed
    type: bool
    desc: "True if moat rating from D2-3 should be downgraded"
---

# D2-4: False Advantage Identification

Prevent overrating non-moats. Check each item — "Yes" means the perceived advantage is NOT a true moat.

## 6-Item Checklist

| # | False Advantage | Check | 
|---|----------------|-------|
| 1 | Cyclical peak masquerading as moat | Is high ROE driven by cycle top rather than structural advantage? |
| 2 | Government protection without organic advantage | Do subsidies, tariffs, or exclusive licenses create the advantage rather than the business itself? |
| 3 | First-mover without switching costs | Is the company early to market but customers face no cost to switch? |
| 4 | Technology lead without data flywheel | Could competitors replicate the technology within 2 years? |
| 5 | Brand awareness without pricing power | Is the brand well-known but unable to command price premiums? |
| 6 | Scale without cost advantage | Is the company large but unit costs similar to smaller competitors? |

## Instructions

1. For each item, state YES or NO with one-line evidence
2. Count confirmed false advantages
3. If any confirmed → consider whether moat rating from D2-3 should be downgraded
4. Note the impact on overall moat assessment

```json
{
  "false_advantage_flags": "None identified",
  "false_advantage_count": 0,
  "moat_downgrade_needed": false
}
```
