"""yfinance data provider for US equities (fallback when Bloomberg unavailable).

Wraps yfinance API into the thesis-backtester DataProvider Protocol.
No Bloomberg Terminal or API key required — free public data.

Limitations vs Bloomberg:
  - No filing dates (uses EDGAR fallback: end_date + 90 days)
  - Rate limiting less predictable
  - Some fields may be missing or stale
"""
from .provider import YFinanceProvider

__all__ = ["YFinanceProvider"]
