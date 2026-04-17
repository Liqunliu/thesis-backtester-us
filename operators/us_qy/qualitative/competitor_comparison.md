---
id: competitor_comparison
name: "Competitor Comparison (D2-5)"
category: qualitative
tags: [d2, moat, competitors, market-share]
data_needed: [income, balancesheet]
outputs:
  - field: market_structure
    type: str
    desc: "monopoly / oligopoly / monopolistic competition / perfect competition"
  - field: cr4_estimate
    type: float
    desc: "Top 4 firms combined market share (%)"
  - field: competitive_position
    type: str
    desc: "1st / 2nd / 3rd in competitive ranking"
  - field: competitive_gap_trend
    type: str
    desc: "Widening / Stable / Narrowing"
  - field: competitor_list
    type: str
    desc: "Top 2-3 competitors with ticker symbols"
---

# D2-5: Competitor Comparison

## Industry Map (from D2-1)

- Market structure: monopoly / oligopoly / monopolistic competition / perfect competition
- CR4 estimate: top 4 firms combined market share

## Competitive Comparison Table

Select top 2-3 competitors. Compare:

| Metric | This Company | Competitor 1 | Competitor 2 |
|--------|-------------|-------------|-------------|
| Revenue ($M) | | | |
| Operating Margin (%) | | | |
| ROE (%) | | | |
| Market Share (%) | | | |
| Moat Type | | | |
| Key Advantage | | | |

## Relative Ranking

Rank on the most competitively relevant dimension:
1. [Company] — [reason]
2. [Company] — [reason]
3. [Company] — [reason]

## Competitive Gap Sustainability

- Is the gap **Widening** (moat strengthening), **Stable**, or **Narrowing** (moat eroding)?
- Evidence: cite trend data (market share changes, margin convergence, technology catch-up)

```json
{
  "market_structure": "oligopoly",
  "cr4_estimate": 72.0,
  "competitive_position": "1st",
  "competitive_gap_trend": "Stable",
  "competitor_list": "Company B (TICK1), Company C (TICK2)"
}
```
