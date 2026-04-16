# US-QY Operators

25 atomic operators implementing the Quality Yield 4-factor framework for US equities.

## Operator Index

### Screening (1)
| ID | Veto? | Description |
|----|-------|-------------|
| `f1a_quick_screen` | Yes | 6 binary veto checks (audit, fraud, model clarity, insider) |

### Qualitative — D1 Business Model (5)
| ID | Dimension | Description |
|----|-----------|-------------|
| `capital_intensity` | D1-A | Capital-light vs capital-hungry |
| `payment_pattern` | D1-B | Cash flow timing of transactions |
| `revenue_quality` | D1-C | Core vs noise revenue decomposition |
| `profit_quality` | D1-D | Core operating vs non-operational profit |
| `biz_model_classification` | D1-F | 7-type business model label |

### Qualitative — D2 Moat (6)
| ID | Dimension | Description |
|----|-----------|-------------|
| `moat_quant_gate` | D2-2 | ROE 5yr validation before deep dive |
| `moat_framework_a` | D2-3a | Two-tier layered (business + technical) |
| `moat_greenwald` | D2-3b | Three-dimensional cross-check |
| `false_advantages` | D2-4 | 6-item false moat checklist |
| `competitor_comparison` | D2-5 | Peer comparison + competitive gap |
| `moat_sustainability` | D2-6 | Erosion vectors + monitoring KPIs |

### Qualitative — D3-D6 (3)
| ID | Dimension | Description |
|----|-----------|-------------|
| `cyclicality_assessment` | D3 | Cycle classification + position |
| `management_assessment` | D4 | Capital allocation + governance |
| `mda_interpretation` | D5+D6 | MD&A narrative + complex structure |

### Quantitative — F2 Coarse Return (3)
| ID | Veto? | Description |
|----|-------|-------------|
| `owner_earnings_us` | No | OE = NI + D&A - Maint CapEx (SBC-adjusted) |
| `distribution_capacity` | Yes | FCF/financing CF pattern check |
| `coarse_penetration_return` | Yes | R = yield at current price vs Rf/Threshold II |

### Quantitative — F3 Refined Return (6)
| ID | Veto? | Description |
|----|-------|-------------|
| `cash_revenue_reconstruction` | No | Strip accrual noise from revenue |
| `non_recurring_classification` | No | Retained vs deducted cash flows |
| `operating_outflows` | No | Operating + CapEx decomposition |
| `gaap_audit` | No | US GAAP distortion detection |
| `refined_return_aa` | Yes | Bottom-up AA + GG calculation |
| `sensitivity_cross_validation` | No | Sensitivity + credibility assessment |

### Valuation — F4 (1)
| ID | Description |
|----|-------------|
| `valuation_synthesis_us` | DCF + DDM + multiples + value trap + scoring |

## Versioning

All operators in `operators/us_qy/` are **v1** (initial release).
Do not modify after backtesting — create `operators/us_qy_v2/` for improvements.
