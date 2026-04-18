"""TTL-based disk cache for US equity data collection.

Caches Bloomberg/yfinance data in JSON files under ``data/cache/us/``
to avoid redundant API calls during screening and analysis workflows.

Cache key format: ``data/cache/us/{TICKER}/{data_type}.json``

Each cached entry stores:
  - ``timestamp``: ISO-format write time
  - ``data``: the payload (dict, list, or DataFrame-as-dict)

DataFrame serialization uses split format for compact, lossless round-trip:
  ``{"index": [...], "columns": [...], "data": [...]}``
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default TTLs (seconds)
# ---------------------------------------------------------------------------
DEFAULT_TTLS: Dict[str, int] = {
    # Financial statements (change infrequently)
    "income": 7 * 86400,           # 7 days
    "balancesheet": 7 * 86400,     # 7 days
    "cashflow": 7 * 86400,         # 7 days
    "fina_indicator": 7 * 86400,   # 7 days
    "dividend": 7 * 86400,         # 7 days
    "holders": 7 * 86400,          # 7 days
    # Filing metadata (rare changes)
    "filing_dates": 30 * 86400,    # 30 days
    "filing_sections": 90 * 86400, # 90 days
    # Market data (stale quickly)
    "market_snapshot": 86400,      # 1 day
    "price_history": 86400,        # 1 day
    "snapshot": 86400,             # 1 day
}


class DataCache:
    """TTL-based disk cache with DataFrame serialization."""

    def __init__(
        self,
        cache_dir: str = "data/cache/us",
        ttls: Optional[Dict[str, int]] = None,
    ):
        self.cache_dir = Path(cache_dir)
        self.ttls = {**DEFAULT_TTLS, **(ttls or {})}
        # Session stats
        self._hits = 0
        self._misses = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, ticker: str, data_type: str) -> Optional[Any]:
        """Return cached data if fresh, None if stale/missing."""
        path = self._path(ticker, data_type)
        if not path.exists():
            self._misses += 1
            return None

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self._misses += 1
            return None

        ts = raw.get("timestamp")
        if ts is None:
            self._misses += 1
            return None

        age = time.time() - _parse_iso(ts)
        ttl = self.ttls.get(data_type, DEFAULT_TTLS.get(data_type, 86400))
        if age > ttl:
            self._misses += 1
            return None

        self._hits += 1
        data = raw.get("data")
        return _deserialize(data)

    def put(self, ticker: str, data_type: str, data: Any) -> None:
        """Store data with timestamp."""
        path = self._path(ticker, data_type)
        path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "timestamp": datetime.now().isoformat(),
            "ticker": ticker.upper(),
            "data_type": data_type,
            "data": _serialize(data),
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, default=_json_default),
            encoding="utf-8",
        )

    def get_or_fetch(
        self,
        ticker: str,
        data_type: str,
        fetch_fn: Callable[[], Any],
    ) -> Any:
        """Return cached data if fresh, otherwise call fetch_fn, cache, and return.

        Args:
            ticker: Stock ticker (e.g. 'AAPL')
            data_type: Cache key type (e.g. 'income', 'price_history')
            fetch_fn: Zero-argument callable that fetches fresh data

        Returns:
            The cached or freshly fetched data.
        """
        cached = self.get(ticker, data_type)
        if cached is not None:
            logger.debug("Cache hit: %s/%s", ticker, data_type)
            return cached

        logger.debug("Cache miss: %s/%s — fetching", ticker, data_type)
        result = fetch_fn()
        self.put(ticker, data_type, result)
        return result

    def invalidate(self, ticker: str, data_type: Optional[str] = None) -> None:
        """Remove cached data for a ticker (optionally specific type)."""
        if data_type:
            path = self._path(ticker, data_type)
            if path.exists():
                path.unlink()
        else:
            ticker_dir = self.cache_dir / ticker.upper()
            if ticker_dir.is_dir():
                for f in ticker_dir.iterdir():
                    f.unlink()
                ticker_dir.rmdir()

    def stats(self) -> dict:
        """Return cache hit/miss stats for current session."""
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "total": total,
            "hit_rate": f"{self._hits / total:.0%}" if total > 0 else "N/A",
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _path(self, ticker: str, data_type: str) -> Path:
        return self.cache_dir / ticker.upper() / f"{data_type}.json"


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _serialize(obj: Any) -> Any:
    """Convert Python objects to JSON-safe structures.

    DataFrames are stored in split format for compact, lossless round-trip.
    """
    if isinstance(obj, pd.DataFrame):
        # Convert index to strings for JSON
        idx = obj.index.tolist()
        cols = obj.columns.tolist()
        # Convert Timestamps in columns to ISO strings
        cols_serial = [
            c.isoformat() if hasattr(c, "isoformat") else str(c) for c in cols
        ]
        idx_serial = [
            i.isoformat() if hasattr(i, "isoformat") else str(i) for i in idx
        ]
        return {
            "__dataframe__": True,
            "index": idx_serial,
            "columns": cols_serial,
            "data": _nan_to_none(obj.values.tolist()),
        }
    if isinstance(obj, pd.Series):
        return _serialize(obj.to_frame().T)
    return obj


def _deserialize(obj: Any) -> Any:
    """Reconstruct Python objects from JSON-safe structures."""
    if isinstance(obj, dict) and obj.get("__dataframe__"):
        df = pd.DataFrame(
            data=obj["data"],
            index=obj["index"],
            columns=obj["columns"],
        )
        # Try to parse column strings as datetime
        try:
            import warnings as _w
            with _w.catch_warnings():
                _w.simplefilter("ignore", UserWarning)
                df.columns = pd.to_datetime(df.columns)
        except (ValueError, TypeError):
            pass
        return df
    return obj


def _nan_to_none(data):
    """Recursively replace NaN/inf with None for JSON serialization."""
    if isinstance(data, list):
        return [_nan_to_none(item) for item in data]
    if isinstance(data, float) and (np.isnan(data) or np.isinf(data)):
        return None
    return data


def _json_default(obj):
    """JSON fallback serializer for numpy/pandas types."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return None if np.isnan(obj) else float(obj)
    if isinstance(obj, np.ndarray):
        return _nan_to_none(obj.tolist())
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    if isinstance(obj, np.bool_):
        return bool(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _parse_iso(ts_str: str) -> float:
    """Parse ISO timestamp string to epoch seconds."""
    try:
        return datetime.fromisoformat(ts_str).timestamp()
    except (ValueError, TypeError):
        return 0.0
