# S&P 500 Long-Term Return Analysis

*Date: 2026-04-19*
*Method: 10-year and 5-year price CAGR (price-only, excludes dividends)*
*Universe: 503 S&P 500 constituents, Bloomberg Terminal data*

## Key Finding

**73% of stocks that delivered 15%+ annual returns over 10 years are growth stocks (PE > 25).** Information Technology alone accounts for 42% of the 20%+ CAGR tier. The traditional value approach (low PE, high yield) structurally misses the best long-term compounders.

## How Many Stocks Beat 15% and 20% Annually?

| Period | >= 15% CAGR | >= 20% CAGR | Universe |
|--------|-------------|-------------|----------|
| 10-Year | 131 (28%) | 74 (16%) | 464 |
| 5-Year | 120 (24%) | 75 (15%) | 490 |

Roughly **1 in 4** S&P 500 stocks delivers 15%+ annual price appreciation over a decade. Only **1 in 6** sustains 20%+.

## Where Do the Winners Come From?

### By Sector (10Y CAGR >= 20%)

| Sector | Count | Share | Median 10Y CAGR |
|--------|-------|-------|-----------------|
| **Information Technology** | **31** | **42%** | **15.8%** |
| Industrials | 14 | 19% | 12.8% |
| Consumer Discretionary | 7 | 9% | 10.7% |
| Communication Services | 6 | 8% | 13.8% |
| Financials | 6 | 8% | 11.9% |
| Health Care | 3 | 4% | 8.7% |
| Energy | 2 | 3% | 6.1% |
| Materials | 2 | 3% | 11.1% |
| Consumer Staples | 2 | 3% | 3.0% |

IT + Industrials = **61%** of all 20%+ CAGR stocks.

Consumer Staples (3.0% median), Real Estate (1.3%), and Utilities (6.5%) almost never produce high-return compounders.

### By Style

| Style | Count | % of >= 15% | Median CAGR |
|-------|-------|-------------|-------------|
| **Growth** (PE > 25) | 95 | **73%** | 22.5% |
| Value (PE <= 25) | 31 | 24% | 18.9% |
| Cyclical sectors | 35 | 27% | 20.7% |
| Non-cyclical | 96 | 73% | 21.8% |

### Top 20 Compounders (10Y CAGR)

| Ticker | Name | Sector | 10Y CAGR | 5Y CAGR |
|--------|------|--------|----------|---------|
| NVDA | Nvidia | IT | 71.9% | 66.7% |
| AMD | Advanced Micro Devices | IT | 58.6% | 17.3% |
| FIX | Comfort Systems USA | Industrials | 48.0% | 83.6% |
| MU | Micron Technology | IT | 45.8% | 37.6% |
| ANET | Arista Networks | IT | 45.1% | 52.9% |
| LRCX | Lam Research | IT | 41.8% | 32.9% |
| PWR | Quanta Services | Industrials | 39.3% | 45.0% |
| AVGO | Broadcom | IT | 38.6% | 53.0% |
| TPL | Texas Pacific Land | Energy | 38.3% | 25.9% |
| KLAC | KLA Corporation | IT | 37.9% | 39.1% |
| TSLA | Tesla | Consumer Disc | 37.4% | 10.1% |
| MPWR | Monolithic Power | IT | 36.9% | 12.1% |
| AXON | Axon Enterprise | Industrials | 36.1% | 29.3% |
| AMAT | Applied Materials | IT | 34.2% | 19.6% |
| JBL | Jabil | IT | 33.3% | 43.2% |
| EME | Emcor | Industrials | 32.8% | 47.0% |
| FTNT | Fortinet | IT | 29.9% | 11.1% |
| URI | United Rentals | Industrials | 29.6% | 18.6% |
| LLY | Eli Lilly | Health Care | 28.8% | 38.4% |
| DECK | Deckers Brands | Consumer Disc | 28.4% | 24.2% |

## Patterns in the Data

### 1. Semiconductors dominate
7 of the top 20 are semiconductor or semi-equipment companies (NVDA, AMD, MU, LRCX, AVGO, KLAC, AMAT). This reflects the AI/cloud capex supercycle.

### 2. Industrials are the surprise category
FIX (#3), PWR (#7), AXON (#13), EME (#16), URI (#18) — these are not glamorous tech companies. They're construction, electrical, equipment rental, and defense. They benefit from infrastructure spend and pricing power with less competition.

### 3. Value stocks CAN compound but less often
31 value stocks (PE <= 25) delivered 15%+ CAGR — companies like DECK (PE 16), URI (PE 26), JBL (PE 34). These tend to be "value compounders" — cheap entry + sustained earnings growth.

### 4. Energy and Materials are episodic
Only 4 energy stocks and 5 materials stocks made the 15%+ list. Their returns come in bursts (commodity supercycles) rather than steady compounding.

### 5. Consumer Staples and Real Estate are return deserts
Median 10Y CAGR of 3.0% (staples) and 1.3% (REITs). These sectors are yield plays, not growth plays. Including dividends would add ~3-4pp, but still well below 15%.

## Implications for Strategy Design

### Why QY underperformed SPY in US backtest (-3pp alpha)
The QY strategy filters for PE < 30 and GG > 7.3%. This mechanically excludes:
- NVDA (PE 44), AVGO (PE 72), ANET (PE 60) — the biggest compounders
- Most Industrials compounders (PE 30-80 range)
- All "growth at reasonable price" (GARP) stocks

QY works in A-shares (+7.1pp alpha) because the Chinese market rewards value/yield more consistently. The US market is driven by compounding growth.

### Strategy coverage gap analysis

| Stock Type | Best Strategy | Current Coverage |
|-----------|--------------|-----------------|
| Value + yield (GIS, CMCSA) | **quality_yield** | Good |
| Commodity cyclicals (OXY, FCX) | **cyclical** | Good |
| Deep discount (P/B < 0.6) | **cigar_butt** | Created, untested |
| Crashed growth (AFRM, UPST) | **turnaround** | Created, tested |
| High-growth compounders (NVDA, AVGO) | **growth** | Created, untested |
| Value compounders (DECK, URI) | **gap** | Falls between QY and growth |

### The "value compounder" gap
Stocks like DECK (PE 16, 28% CAGR), URI (PE 26, 30% CAGR), and JBL (PE 34, 33% CAGR) are too expensive for QY but not "growth" enough for the growth strategy. These are the best risk-adjusted investments — cheap entry + durable competitive advantages + sustained earnings growth. A future strategy could target this niche.

---

*Note: All CAGRs are price-only and understate total returns for dividend-paying stocks by ~2-4pp annually. The relative rankings and sector patterns remain valid.*
