---
id: cigar_valuation_synthesis
name: "Cigar Butt Valuation & Synthesis"
category: valuation
tags: [synthesis, valuation, nav, position-sizing, cigar, deep-value]
data_needed: [balancesheet, income, cashflow, indicator]
outputs:
  - field: recommendation
    type: str
    desc: "BUY / HOLD / WATCH / AVOID"
  - field: position_size
    type: float
    desc: "Recommended position size as percentage of portfolio"
  - field: entry_price
    type: float
    desc: "Maximum entry price based on best tier NAV and required discount"
  - field: exit_target
    type: float
    desc: "Profit-taking target price (first tranche, NAV * tier multiplier)"
  - field: stop_loss
    type: float
    desc: "Stop-loss price (-25% from entry)"
  - field: total_score
    type: float
    desc: "Composite score 0-100 (P1 + P2 + P3 + FC, 25 pts each)"
  - field: pillar1_score
    type: float
    desc: "Pillar 1 sub-score (0-25)"
  - field: pillar2_score
    type: float
    desc: "Pillar 2 sub-score (0-25)"
  - field: pillar3_score
    type: float
    desc: "Pillar 3 sub-score (0-25)"
  - field: fact_check_score
    type: float
    desc: "Fact Check sub-score (0-25)"
  - field: gradient_entry_plan
    type: str
    desc: "3-tranche entry plan with price levels and allocation percentages"
  - field: exit_rules_summary
    type: str
    desc: "Summary of profit-taking and stop-loss rules"
  - field: value_trap_risk
    type: str
    desc: "Value trap risk assessment: LOW / MEDIUM / HIGH"
---

# Cigar Butt Valuation & Synthesis

Final integration of all three pillars and fact check into an actionable recommendation
with NAV-based position sizing, gradient entry, and explicit exit rules.

## Step 1: Veto Gate Consolidation

Before scoring, check for any upstream vetoes. If ANY of the following is true,
set `total_score <= 20` and `recommendation = "AVOID"`:

1. `cigar_pass = false` (quick screen failed)
2. `pillar1_pass = false` (no NAV tier qualifies)
3. `pillar2_pass = false` (fewer than 2/3 operating conditions met)
4. `fact_check_pass = false` (veto item triggered, rating D)

If a veto is triggered, still complete the synthesis but note the disqualifying factor.

## Step 2: Pillar Scoring (0-25 each)

### Pillar 1 Score: Net Asset Cushion

| Condition | Score |
|-----------|-------|
| T0 qualifies (Cash - Total Liabilities > 0, price < T0_NAV * 0.85) | 25 |
| T1 qualifies (Cash - IBD > 0, price < T1_NAV * 0.80) | 20 |
| T2 qualifies (Adj Current Assets - Total Liab > 0, price < T2_NAV * 0.70) | 15 |
| Near-miss (qualifies at reduced discount) | 8 |
| No tier qualifies | 0 |

### Pillar 2 Score: Operating Maintenance

| Condition | Score |
|-----------|-------|
| 3/3 conditions met + FCF conversion > 1.0 | 25 |
| 3/3 conditions met | 22 |
| 2/3 conditions met + ABR = PASS | 18 |
| 2/3 conditions met + ABR = WARNING | 15 |
| 1/3 conditions met | 5 |
| 0/3 conditions met | 0 |

### Pillar 3 Score: Realization Logic

| Condition | Score |
|-----------|-------|
| Strong catalyst: Type A (score 8+/10) or Type B (discount > 40%) | 25 |
| Moderate catalyst: Type A (score 6-7) or Type B (discount 30-40%) | 20 |
| Event catalyst: Type C1 with probability >= B | 20 |
| Regulatory catalyst: Type C2 with score >= 6 | 15 |
| Weak catalyst: C2- or low-probability C1 | 8 |
| No realization mechanism identified | 0 |

### Fact Check Score

| Rating | Score |
|--------|-------|
| A (all pass, no warnings) | 25 |
| B+ (B with bonus >= 2) | 22 |
| B (1-2 warnings) | 18 |
| C (3+ warnings) | 10 |
| D (veto triggered) | 0 |

### Total Score

```
Total = Pillar1_Score + Pillar2_Score + Pillar3_Score + FactCheck_Score
```

## Step 3: Value Trap Risk Assessment

Evaluate the risk that the NAV discount persists indefinitely:

| Risk Level | Conditions |
|------------|-----------|
| LOW | Strong catalyst (P3 score >= 20) + clean fact check (FC >= 18) |
| MEDIUM | Moderate catalyst (P3 score 8-19) OR fact check warnings |
| HIGH | No catalyst (P3 score = 0) OR ABR = WARNING + no catalyst |

## Step 4: Position Sizing

Position size is determined by NAV tier (from Pillar 1):

| Tier | Max Position | Rationale |
|------|-------------|-----------|
| T0 | 10% | Highest asset quality, smallest required discount |
| T1 | 8% | Moderate asset quality |
| T2 | 5% | Lower asset quality, larger required discount |

### Fact Check Adjustment

| Fact Check Rating | Position Modifier |
|-------------------|-------------------|
| A or B+ | 100% of max position |
| B | 80% of max position |
| C | 50% of max position |
| D | 0% (do not invest) |

### Final Position Size

```
Position_Size = Tier_Max_Position * FactCheck_Modifier * Probability_Modifier
```

Where `Probability_Modifier` comes from Pillar 3 event probability (A=1.0, B=0.75, C=0.50).

## Step 5: Gradient Entry Plan

Build position in 3 tranches:

| Tranche | Weight | Trigger |
|---------|--------|---------|
| 1st | 40% of position | Price hits entry threshold |
| 2nd | 30% of position | Price drops another 10% from tranche 1 |
| 3rd | 30% of position | Another 10% drop from tranche 2 OR catalyst confirmation |

### Entry Price Calculation

```
Entry_Price (T0) = T0_NAV_Per_Share * 0.85
Entry_Price (T1) = T1_NAV_Per_Share * 0.80
Entry_Price (T2) = T2_NAV_Per_Share * 0.70

Tranche_1_Price = Entry_Price
Tranche_2_Price = Entry_Price * 0.90
Tranche_3_Price = Entry_Price * 0.81  (or catalyst confirmation)
```

## Step 6: Exit Rules

### Profit-Taking (sell 50% at level 1, remaining at level 2)

| Tier | Level 1 (sell 50%) | Level 2 (sell remaining) |
|------|-------------------|------------------------|
| T0 | T0_NAV * 0.95 | T0_NAV * 1.05 |
| T1 | T1_NAV * 0.90 | T1_NAV * 1.00 |
| T2 | T2_NAV * 0.80 | T2_NAV * 0.95 |

### Stop-Loss

```
Stop_Loss_Price = Average_Entry_Price * 0.75  (i.e., -25% from entry)
```

Hard stop at -25% decline from average entry price. No exceptions.

### Time-Based Exit

Maximum holding period: 5 years. If the thesis has not materialized within 5 years,
exit regardless of current price. The opportunity cost of capital in a deep value
position without realization is too high.

### Sub-Type Specific Exit Rules

**Type A (Dividend)**:
- Dividend cut > 30%: Immediate full exit
- Payout > 100% for 2 consecutive quarters: Reassess, likely exit

**Type B (Holding Company)**:
- Discount narrows to 20%: Sell 50%
- Discount narrows to 15%: Sell remaining
- Subsidiary deterioration > 30%: Reassess thesis

**Type C1 (Event-Driven)**:
- Event completion: Exit per event-specific plan
- Event cancelled/delayed beyond 12 months: Exit at market

## Step 7: Recommendation

| Total Score | Recommendation |
|-------------|---------------|
| >= 85 | Strong BUY (T0 + strong catalyst + clean check) |
| 70-84 | BUY (T1+ + identifiable catalyst + acceptable check) |
| 50-69 | HOLD/WATCH (T2 + weak catalyst or check concerns) |
| 30-49 | WATCH (marginal NAV + value trap risk) |
| <= 29 | AVOID (veto triggered or no realization mechanism) |

## Step 8: Cross-Validation

Before finalizing, verify internal consistency:

1. Does the NAV tier (Pillar 1) support the position size recommendation?
2. Is the operating maintenance (Pillar 2) consistent with the realization timeframe (Pillar 3)?
3. Do fact check findings contradict any pillar conclusions?
4. If ABR is WARNING but catalyst is strong, is the cash runway sufficient for the catalyst timeline?

If material contradictions exist, cap `total_score` at 65 (cannot reach BUY threshold)
and note the contradiction in the recommendation.

## Output Format

```json
{
  "recommendation": "BUY",
  "position_size": 6.4,
  "entry_price": 9.84,
  "exit_target": 11.07,
  "stop_loss": 7.38,
  "total_score": 78,
  "pillar1_score": 20,
  "pillar2_score": 18,
  "pillar3_score": 20,
  "fact_check_score": 20,
  "gradient_entry_plan": "Tranche 1: 40% at $9.84, Tranche 2: 30% at $8.86, Tranche 3: 30% at $7.97 or catalyst confirmation",
  "exit_rules_summary": "Profit-take 50% at T1_NAV*0.90=$11.07, remaining at T1_NAV*1.00=$12.30. Stop-loss at -25% ($7.38). Max hold 5 years.",
  "value_trap_risk": "LOW"
}
```
