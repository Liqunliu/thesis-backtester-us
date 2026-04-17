---
id: management_assessment
name: "Management & Governance (D4)"
category: qualitative
tags: [d4, management, governance, capital-allocation, veto]
data_needed: [income, balancesheet, cashflow]
outputs:
  - field: management_rating
    type: str
    desc: "Excellent / Adequate / Destroying value / Observation"
  - field: capital_allocation_summary
    type: str
    desc: "One-sentence summary of capital allocation track record"
  - field: related_party_concern
    type: bool
    desc: "True if frequent related-party transactions detected"
  - field: management_veto
    type: bool
    desc: "True if management is actively destroying value"
---

# D4: Management & Governance

## Analysis

1. **Core management tenure**: CEO/Chairman/CFO years in role
2. **Major management changes** in past 5 years

3. **Capital allocation track record** (annotate by management tenure):
   - Destination of retained earnings: organic expansion / acquisitions / investments / debt repayment / idle
   - Ex-post returns: Large goodwill impairments? Investment losses? Failed projects?
   - If management changed: has predecessor's capital misallocation been cleared?

4. **Observable signals for current management** (if management changed):
   - Positive: proactively wrote down impairments, increased dividends, initiated buybacks
   - Negative: continued investing in predecessor's failed projects
   - Neutral: initiated new acquisitions (needs observation)

5. **Related-party transaction check** (regardless of management era):
   - Frequent related-party transactions? Is pricing arm's-length?

## Decision Logic

```
No management change:
  → Excellent / Adequate / Destroying value (VETO)

Management changed AND tenure < 2 years:
  Predecessor poor + current signals positive → Observation (no veto yet)
  Predecessor poor + current unclear → VETO
  Predecessor legacy not cleared → VETO

Management changed AND tenure >= 2 years:
  → Judge on current track record: Excellent / Adequate / Destroying value
```

```json
{
  "management_rating": "Adequate",
  "capital_allocation_summary": "Consistent dividend growth + selective buybacks; one large acquisition (2021) still being integrated",
  "related_party_concern": false,
  "management_veto": false
}
```
