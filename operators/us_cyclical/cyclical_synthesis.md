---
id: cyclical_synthesis
name: "C4: Cyclical Synthesis & Recommendation"
category: cyclical
tags: [c4, synthesis, position-sizing, risk-management, recommendation]
data_needed: [income, cashflow, balancesheet, market_data]
outputs:
  - field: recommendation
    type: str
    desc: "BUY / HOLD / REDUCE / SELL / AVOID"
  - field: position_size_pct
    type: float
    desc: "Recommended position size as % of portfolio"
  - field: entry_phase
    type: str
    desc: "Phase at entry: Deep Trough / Early Recovery / N/A"
  - field: exit_trigger
    type: str
    desc: "Primary exit trigger: Phase 5 / 3-year time stop / N/A"
  - field: total_score
    type: int
    desc: "Overall conviction score (0-100)"
  - field: conviction
    type: str
    desc: "HIGH / MEDIUM / LOW / NONE"
---

# C4: Cyclical Synthesis & Recommendation

> Combines C1 (Survival), C2 (Phase), and C3 (Normalized Valuation) into a
> final recommendation with phase-based position sizing and risk management.

---

## Decision Matrix

### Entry Requirements (ALL must be met for BUY)

| # | Requirement | Source | Threshold |
|---|-------------|--------|-----------|
| 1 | Survival gates | C1 | c1_pass = true |
| 2 | Cyclicality confirmed | C1 | is_cyclical = true |
| 3 | Favorable phase | C2 | Phase 1 or Phase 2 |
| 4 | Normalized GG | C3 | >= 7.30% (Threshold II) |
| 5 | Discount to mid-cycle | C3 | >= 15% |

If any requirement fails, downgrade to HOLD/WATCH/AVOID depending on severity.

---

## Position Sizing by Phase

### Phase 1: Deep Trough (Composite Score >= 0.80)

Max single position = **15%** of portfolio.

| Tier | Normalized GG | Position % of Max | Actual Position |
|------|---------------|-------------------|-----------------|
| Tier A | >= 3x Threshold (21.9%+) | 100% | 15.0% |
| Tier B | >= 2x Threshold (14.6%+) | 80% | 12.0% |
| Tier C | >= 1x Threshold (7.3%+) | 60% | 9.0% |

Action: **BUY -- max conviction**

### Phase 2: Early Recovery (Composite Score 0.65 - 0.80)

Max single position = **10%** of portfolio.

| Tier | Normalized GG | Position % of Max | Actual Position |
|------|---------------|-------------------|-----------------|
| Tier A | >= 3x Threshold (21.9%+) | 70% | 7.0% |
| Tier B | >= 2x Threshold (14.6%+) | 50% | 5.0% |
| Tier C | >= 1x Threshold (7.3%+) | 35% | 3.5% |

Action: **BUY -- standard**

### Phase 3: Mid-Cycle (Composite Score 0.40 - 0.65)

**HOLD only -- no new positions.**

If already holding, maintain position. Do not add.

### Phase 4: Late Cycle (Composite Score 0.20 - 0.40)

**REDUCE -- trim 50% of existing position.**

If not holding, AVOID.

### Phase 5: Peak (Composite Score < 0.20)

**SELL / AVOID -- close all positions.**

---

## Portfolio Risk Limits

| Rule | Limit | Action if Breached |
|------|-------|--------------------|
| Max single position | 15% | Do not add; trim to limit |
| Max sector exposure | 35% | Skip new entries in same sector |
| Max commodity group | 30% | Skip new entries in same commodity group |
| Min cash reserve | 20% | No new entries until cash restored |
| Portfolio stop-loss | -25% from peak | Full portfolio review; consider liquidating weakest |

### Commodity Group Definitions

| Group | Industries |
|-------|-----------|
| Oil & Gas | E&P, Integrated, Refining, Midstream, Services |
| Shipping | Tankers, Dry Bulk, Container |
| Semiconductors | Design, Equipment, Foundry |
| Mining / Metals | Copper, Gold, Diversified Mining |
| Steel | Integrated Steel, Mini-mills, Specialty Steel |
| Industrials | Heavy Equipment, Construction, Farm Machinery |

---

## Exit Triggers

Reduce or exit position when **any** of these occur:

| # | Trigger | Action |
|---|---------|--------|
| 1 | Phase moves to 3 (Mid-Cycle) | Reduce to 50% of position |
| 2 | Phase moves to 4 (Late Cycle) | Reduce to 25% of position |
| 3 | Phase reaches 5 (Peak) | Close position entirely |
| 4 | 3-year holding period elapsed | Review and likely exit |
| 5 | Portfolio stop-loss hit (-25%) | Review all positions |
| 6 | Company-specific event (fraud, covenant breach) | Immediate exit |
| 7 | C1 survival gate fails on re-check | Immediate exit |

---

## Scoring Framework (0-100)

### Component Scores

| Component | Weight | Score Range | Anchor |
|-----------|--------|-------------|--------|
| C1 Survival | Gate | PASS/VETO | VETO -> score capped at 25 |
| C2 Phase | 35% | 0-35 | Phase 1=35, Phase 2=25, Phase 3=15, Phase 4=8, Phase 5=0 |
| C3 Normalized GG | 35% | 0-35 | GG>15%=35, GG>10%=28, GG>7.3%=20, GG>5%=10, else=0 |
| Sector Alignment | 15% | 0-15 | Company+Sector within 1 phase=15, 2 phases=8, 3+=0 |
| Quality / Governance | 15% | 0-15 | No concerns=15, minor=10, major=5, fraud=0 |

### Score to Recommendation

| Score | Recommendation | Conviction |
|-------|---------------|------------|
| 85-100 | BUY | HIGH |
| 70-84 | BUY | MEDIUM |
| 50-69 | HOLD / WATCH | LOW |
| 30-49 | WATCH / REDUCE | NONE |
| 0-29 | AVOID / SELL | NONE |

---

## Output Format

```
C4 Cyclical Synthesis

Total Score: XX / 100
Recommendation: [BUY / HOLD / REDUCE / SELL / AVOID]
Conviction: [HIGH / MEDIUM / LOW / NONE]

Score Breakdown:
| Component | Score | Notes |
|-----------|-------|-------|
| C1 Survival | PASS/VETO | [details] |
| C2 Phase (35%) | XX/35 | Phase X -- [Name] |
| C3 Normalized GG (35%) | XX/35 | GG = X.XX% |
| Sector Alignment (15%) | XX/15 | [details] |
| Quality (15%) | XX/15 | [details] |
| Total | XX/100 | |

Position Sizing:
  Phase: X -- [Name]
  GG Tier: [A/B/C]
  Max Allocation: XX%
  Recommended Position: X.X%

Risk Limits:
  Single position: X.X% [<= 15%: OK]
  Sector exposure: X.X% [<= 35%: OK]
  Commodity group: X.X% [<= 30%: OK]

Entry Phase: [Phase Name or N/A]
Exit Trigger: [Primary trigger]
Time Horizon: [Expected holding period]
```

```json
{
  "recommendation": "BUY",
  "position_size_pct": 9.0,
  "entry_phase": "Early Recovery",
  "exit_trigger": "Phase 5 or 3-year time stop",
  "total_score": 75,
  "conviction": "MEDIUM"
}
```
