---
id: moat_framework_a
name: "Moat Framework A: Two-Tier Layered (D2-3a)"
category: qualitative
tags: [d2, moat, framework-a, network-effects, switching-costs]
data_needed: [income, balancesheet]
outputs:
  - field: layer1_scale_economies
    type: str
    desc: "absent / weak / moderate / strong"
  - field: layer1_network_effects
    type: str
    desc: "absent / weak / moderate / strong"
  - field: layer1_switching_costs
    type: str
    desc: "absent / weak / moderate / strong"
  - field: layer1_intangible_assets
    type: str
    desc: "absent / weak / moderate / strong"
  - field: layer1_cost_advantage
    type: str
    desc: "absent / weak / moderate / strong"
  - field: layer2_data_barriers
    type: str
    desc: "absent / weak / moderate / strong / not-applicable"
  - field: layer2_algorithm_barriers
    type: str
    desc: "absent / weak / moderate / strong / not-applicable"
  - field: layer2_supply_chain_barriers
    type: str
    desc: "absent / weak / moderate / strong / not-applicable"
  - field: layer2_ai_frontier
    type: str
    desc: "absent / weak / moderate / strong / not-applicable"
  - field: compound_flywheel
    type: bool
    desc: "True if technical layer reinforces business layer AND vice versa"
  - field: moat_sources_summary
    type: str
    desc: "Summary of identified moat sources"
---

# D2-3a: Moat Framework A (Two-Tier Layered Analysis)

Primary moat classification system.

## Layer 1: Business Barriers (Non-Technical Moat)

Rate each: **absent / weak / moderate / strong**

| Barrier | What to look for |
|---------|-----------------|
| Scale economies | Unit costs decrease meaningfully with scale? Fixed costs spread? |
| Network effects | Value to each user increases as more users join? (direct or indirect) |
| Switching costs | What does it cost a customer (time, money, data migration) to switch? |
| Intangible assets | Brand premium? Patents? Regulatory licenses? |
| Cost advantage | Structural cost advantage vs competitors (not just current efficiency)? |

## Layer 2: Technical Barriers (Data & Algorithm Moat)

Rate each: **absent / weak / moderate / strong / not-applicable**

| Barrier | What to look for |
|---------|-----------------|
| Data asset barriers | Proprietary datasets? Data flywheel (more usage → more data → better product)? |
| Core algorithm/model | Long-iterated systems (recommendation, search, pricing, risk control)? |
| Supply chain systems | Highly customized real-time fulfillment systems? |
| AI/frontier tech | Proprietary closed-loop data advantage in AI/ML? |

Not all companies have Layer 2. Traditional manufacturing/consumer goods: mark "not-applicable."

## Cross-Layer Interaction

- Does technical layer reinforce business layer?
- Does business layer feed back into technical layer?
- If closed-loop flywheel forms → `compound_flywheel = true`
- Technical moat durability depends on R&D spending ratio stability

```json
{
  "layer1_scale_economies": "strong",
  "layer1_network_effects": "moderate",
  "layer1_switching_costs": "strong",
  "layer1_intangible_assets": "moderate",
  "layer1_cost_advantage": "weak",
  "layer2_data_barriers": "strong",
  "layer2_algorithm_barriers": "moderate",
  "layer2_supply_chain_barriers": "not-applicable",
  "layer2_ai_frontier": "moderate",
  "compound_flywheel": true,
  "moat_sources_summary": "Platform with strong switching costs + data flywheel creating compound moat"
}
```
