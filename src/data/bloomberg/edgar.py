"""EDGAR filing date integration for backtest time-boundary enforcement.

Fetches SEC filing dates (when a 10-K/10-Q was actually filed) so the
backtest engine can filter financial data by announcement date, not
just period end date. This prevents look-ahead bias.

Requires:
    SEC_EDGAR_USER_AGENT environment variable (e.g., "Name email@example.com")
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

logger = logging.getLogger(__name__)

_CACHE_DIR = Path("data") / "bloomberg" / "filing_dates"
_SEC_BASE = "https://data.sec.gov"
_CIK_URL = f"{_SEC_BASE}/files/company_tickers.json"
_RATE_LIMIT_SECS = 0.15  # SEC asks for max 10 requests/sec

# CIK lookup cache (populated once)
_cik_cache: Optional[dict] = None


def _get_headers() -> dict:
    agent = os.environ.get("SEC_EDGAR_USER_AGENT", "")
    if not agent:
        raise EnvironmentError(
            "SEC_EDGAR_USER_AGENT not set. "
            "Set to 'YourName your@email.com' per SEC guidelines."
        )
    return {"User-Agent": agent, "Accept-Encoding": "gzip, deflate"}


def _lookup_cik(ticker: str) -> Optional[str]:
    """Look up CIK number for a ticker from SEC's company_tickers.json."""
    global _cik_cache
    if _cik_cache is None:
        resp = requests.get(_CIK_URL, headers=_get_headers(), timeout=10)
        resp.raise_for_status()
        data = resp.json()
        _cik_cache = {}
        for entry in data.values():
            t = entry.get("ticker", "").upper()
            cik = str(entry.get("cik_str", ""))
            _cik_cache[t] = cik.zfill(10)
        time.sleep(_RATE_LIMIT_SECS)

    return _cik_cache.get(ticker.upper())


def fetch_filing_dates(
    ticker: str,
    form_types: tuple = ("10-K", "10-Q", "20-F"),
) -> Optional[pd.DataFrame]:
    """Fetch filing dates from SEC EDGAR for a ticker.

    Returns DataFrame with columns: end_date, filing_date, form_type
    Cached in Parquet after first fetch.
    """
    # Check cache
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = _CACHE_DIR / f"{ticker.upper()}.parquet"
    if cache_file.exists():
        cached = pd.read_parquet(cache_file)
        # Use cache if < 30 days old
        mtime = cache_file.stat().st_mtime
        age_days = (time.time() - mtime) / 86400
        if age_days < 30:
            return cached

    cik = _lookup_cik(ticker)
    if not cik:
        logger.warning("CIK not found for %s", ticker)
        return None

    # Fetch submissions
    url = f"{_SEC_BASE}/submissions/CIK{cik}.json"
    try:
        resp = requests.get(url, headers=_get_headers(), timeout=15)
        resp.raise_for_status()
        data = resp.json()
        time.sleep(_RATE_LIMIT_SECS)
    except Exception as e:
        logger.warning("EDGAR submissions fetch failed for %s: %s", ticker, e)
        return None

    # Parse recent filings
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    periods = recent.get("reportDate", [])

    rows = []
    for form, filing_date, period in zip(forms, dates, periods):
        if form in form_types and period:
            rows.append({
                "end_date": period,
                "filing_date": filing_date,
                "form_type": form,
            })

    if not rows:
        logger.warning("No %s filings found for %s", form_types, ticker)
        return None

    df = pd.DataFrame(rows)
    df["end_date"] = pd.to_datetime(df["end_date"]).dt.strftime("%Y-%m-%d")
    df["filing_date"] = pd.to_datetime(df["filing_date"]).dt.strftime("%Y-%m-%d")

    # Cache
    df.to_parquet(cache_file, index=False)
    logger.info("Cached %d filing dates for %s", len(df), ticker)

    return df
