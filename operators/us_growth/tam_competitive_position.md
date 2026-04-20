---
id: tam_competitive_position
name: "TAM & Competitive Position"
category: qualitative
tags: [tam, market-share, competition, moat, network-effects]
data_needed: [income, balancesheet]
outputs:
  - field: tam_assessment
    type: str
    desc: "LARGE_EXPANDING / LARGE_STABLE / MODERATE / SMALL_NICHE"
  - field: market_position
    type: str
    desc: "LEADER / CHALLENGER / NICHE / COMMODITIZED"
  - field: share_trend
    type: str
    desc: "GAINING / STABLE / LOSING"
  - field: moat_source
    type: str
    desc: "network-effects / switching-costs / data-moat / scale / brand / tech-lead / none"
  - field: competitive_risk
    type: str
    desc: "LOW / MEDIUM / HIGH — risk of disruption or share loss"
  - field: tam_score
    type: float
    desc: "0-25 sub-score"
---

# TAM & Competitive Position

For growth stocks, the addressable market and competitive dynamics matter
more than current earnings. A company growing 30% in a shrinking market
is very different from one growing 30% with 2% penetration of a $100B TAM.

## Step 1: Total Addressable Market Assessment

From the company's industry, revenue scale, and growth rate, assess:

| Revenue ($M) | Growth Rate | TAM Implication |
|-------------|------------|-----------------|
| < $1B | > 40% | Early penetration of large TAM |
| $1-5B | > 25% | Mid-penetration, still large runway |
| $5-20B | > 15% | Maturing but substantial market |
| > $20B | > 15% | Massive TAM (platform business) |
| Any | < 10% | TAM nearly fully penetrated or shrinking |

Key question: Is the company creating a new market (best case) or fighting
for share in an existing one (harder)?

## Step 2: Market Position

Assess from revenue scale, growth vs industry, and competitive landscape:

| Position | Characteristics |
|----------|----------------|
| **LEADER** | #1-2 in category, >20% market share, setting industry pace |
| **CHALLENGER** | Top 5, growing faster than leader, gaining share |
| **NICHE** | Dominant in a subsegment, <10% of total market |
| **COMMODITIZED** | No differentiation, competing on price |

## Step 3: Share Trend

From revenue growth relative to industry/competitors:
- Company growing significantly faster than peers = GAINING
- Company growing at industry rate = STABLE
- Company growing slower than peers = LOSING

Also check from financial data:
- Revenue per unit of invested capital increasing = efficiency gains
- Gross margin stable/expanding while growing = pricing power (share gains sustainable)
- Gross margin compressing while growing = buying share with discounts (unsustainable)

## Step 4: Moat Source for Growth Companies

Growth company moats differ from value company moats:

| Moat Type | Signal | Durability |
|-----------|--------|-----------|
| **Network effects** | Value grows with users. Marketplace, social, payments | STRONG — winner-take-most |
| **Switching costs** | Deep workflow integration. Enterprise SaaS, data platforms | STRONG — sticky customers |
| **Data moat** | Proprietary data improves product. AI/ML, lending models | MODERATE — data accumulates but can be replicated |
| **Scale** | Cost advantages from size. Cloud infrastructure, logistics | MODERATE — capex-intensive |
| **Brand** | Consumer preference. Consumer tech, luxury | VARIABLE — can erode quickly |
| **Tech lead** | First-mover technology advantage. Chips, biotech | TEMPORARY — competitors catch up |
| **None** | No structural advantage | WEAK — growth depends on execution only |

## Step 5: Competitive Risk

Assess the risk that growth stalls due to competition:

| Risk Level | Characteristics |
|-----------|----------------|
| LOW | Dominant position + strong moat + expanding TAM |
| MEDIUM | Good position but credible competitors gaining ground |
| HIGH | Commoditizing market, or large incumbent entering the space |

## Scoring (0-25)

| Condition | Score |
|-----------|-------|
| LARGE_EXPANDING TAM + LEADER + GAINING share + strong moat | 25 |
| LARGE TAM + CHALLENGER + GAINING + moat present | 20 |
| MODERATE TAM + LEADER/NICHE + STABLE share | 15 |
| Any TAM + LOSING share or COMMODITIZED | 10 |
| SMALL TAM + no moat + HIGH competitive risk | 5 |

```json
{
  "tam_assessment": "LARGE_EXPANDING",
  "market_position": "CHALLENGER",
  "share_trend": "GAINING",
  "moat_source": "network-effects",
  "competitive_risk": "MEDIUM",
  "tam_score": 20
}
```
