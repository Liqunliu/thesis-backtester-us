"""Bloomberg data provider for US equities.

Wraps the existing BloombergClient from bloomberg-datacollector repo
into the thesis-backtester DataProvider Protocol.

Requires:
  - Bloomberg Terminal access via SSH tunnel (ssh -L 8194:127.0.0.1:8194 user@vm)
  - OR Bloomberg HAPI credentials

Environment:
  BLOOMBERG_HOST       default: localhost
  BLOOMBERG_PORT       default: 8194
  BLOOMBERG_API_MODE   default: terminal (terminal | hapi)
  BLOOMBERG_COLLECTOR_PATH  path to bloomberg-datacollector/scripts/
  SEC_EDGAR_USER_AGENT      for filing date lookups
"""
from .provider import BloombergProvider

__all__ = ["BloombergProvider"]
