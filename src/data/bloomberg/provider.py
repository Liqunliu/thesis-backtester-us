"""Bloomberg DataProvider for thesis-backtester.

Thin adapter wrapping the existing BloombergClient (from bloomberg-datacollector)
into the DataProvider Protocol used by the thesis-backtester engine.

Bloomberg field mappings (57 mnemonics) and API logic live in bloomberg-datacollector.
This module only translates DataFrames to the Protocol's expected column names.
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

from src.data.cache import DataCache

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Import BloombergClient from bloomberg-datacollector
# ---------------------------------------------------------------------------

_COLLECTOR_PATH = os.environ.get(
    "BLOOMBERG_COLLECTOR_PATH",
    str(Path.home() / "ai_research" / "bloomberg-datacollector" / "scripts"),
)

if _COLLECTOR_PATH not in sys.path:
    sys.path.insert(0, _COLLECTOR_PATH)

try:
    from bloomberg_collector import BloombergClient
    from bloomberg_modules.constants import (
        FIELD_DISPLAY_NAMES,
        INCOME_FIELDS,
        BALANCE_FIELDS,
        CASHFLOW_FIELDS,
        SHAREHOLDER_FIELDS,
        MARKET_FIELDS,
    )
    _HAS_BLOOMBERG = True
except ImportError:
    _HAS_BLOOMBERG = False
    logger.warning(
        "bloomberg-datacollector not found at %s. "
        "Set BLOOMBERG_COLLECTOR_PATH or install bloomberg-datacollector.",
        _COLLECTOR_PATH,
    )

# ---------------------------------------------------------------------------
# Column name mappings: Bloomberg display names → Protocol columns
# ---------------------------------------------------------------------------

# Income statement: Bloomberg display name → protocol column name
_INCOME_MAP = {
    "Revenue": "revenue",
    "Cost of Revenue": "cost_of_revenue",
    "Gross Profit": "gross_profit",
    "Operating Income": "oper_income",
    "Pretax Income": "pretax_income",
    "Income Tax": "income_tax",
    "Net Income": "net_income",
    "EBITDA": "ebitda",
    "Interest Expense": "interest_expense",
}

# Balance sheet
_BALANCE_MAP = {
    "Total Assets": "total_assets",
    "Total Liabilities": "total_liabilities",
    "Shareholders' Equity": "total_equity",
    "Current Assets": "current_assets",
    "Current Liabilities": "current_liabilities",
    "Cash & Equivalents": "cash_and_equivalents",
    "Accounts Receivable": "accounts_receivable",
    "Inventory": "inventory",
    "Accounts Payable": "accounts_payable",
    "Goodwill": "goodwill",
    "Intangible Assets": "intangible_assets",
    "Long-Term Debt": "lt_debt",
    "Short-Term Debt": "st_debt",
}

# Cash flow
_CASHFLOW_MAP = {
    "Operating Cash Flow": "ocf",
    "Investing Cash Flow": "icf",
    "Financing Cash Flow": "fcf_financing",
    "Free Cash Flow": "free_cash_flow",
    "Capital Expenditure": "capex",
    "Depreciation & Amortization": "dep_amort",
    "Dividends Paid": "dividends_paid",
    "Share Repurchases": "share_repurchases",
    "Stock-Based Compensation": "sbc",
}

# Market / indicator
_MARKET_MAP = {
    "Last Price": "close",
    "Market Cap": "total_mv",
    "P/E Ratio": "pe_ttm",
    "P/B Ratio": "pb",
    "EPS (TTM)": "eps_ttm",
    "Dividend Yield": "dv_ttm",
    "ROA": "roa",
    "ROE": "roe",
    "Shares Outstanding": "shares_outstanding",
}


def _rename_df(df: pd.DataFrame, mapping: dict, ticker: str) -> pd.DataFrame:
    """Rename Bloomberg display-name columns to protocol names, add ts_code."""
    # Bloomberg uses display names as column headers after fetching
    rename = {}
    for bbg_name, proto_name in mapping.items():
        if bbg_name in df.columns:
            rename[bbg_name] = proto_name
    out = df.rename(columns=rename)
    out["ts_code"] = ticker
    # Standardize date column
    if "date" in out.columns:
        out = out.rename(columns={"date": "end_date"})
        out["end_date"] = pd.to_datetime(out["end_date"]).dt.strftime("%Y-%m-%d")
    return out


# ---------------------------------------------------------------------------
# BloombergProvider
# ---------------------------------------------------------------------------

class BloombergProvider:
    """DataProvider implementation using Bloomberg Terminal / HAPI.

    Usage:
        from src.data.bloomberg import BloombergProvider
        provider = BloombergProvider()
        income = provider.fetch_income("AAPL")
    """

    def __init__(
        self,
        api_mode: str = None,
        host: str = None,
        port: int = None,
        years: int = 5,
    ):
        if not _HAS_BLOOMBERG:
            raise ImportError(
                "bloomberg-datacollector not available. "
                f"Check BLOOMBERG_COLLECTOR_PATH={_COLLECTOR_PATH}"
            )

        self._api_mode = api_mode or os.environ.get("BLOOMBERG_API_MODE", "terminal")
        self._host = host or os.environ.get("BLOOMBERG_HOST", "localhost")
        self._port = port or int(os.environ.get("BLOOMBERG_PORT", "8194"))
        self._years = years
        self._client: Optional[BloombergClient] = None
        self._cache = DataCache()
        self._filing_dates: dict[str, pd.DataFrame] = {}  # cache

    @property
    def name(self) -> str:
        return "bloomberg"

    def _ensure_client(self) -> BloombergClient:
        """Lazy-connect to Bloomberg."""
        if self._client is None:
            logger.info("Connecting to Bloomberg (%s:%d)...", self._host, self._port)
            self._client = BloombergClient(
                api_mode=self._api_mode,
                host=self._host,
                port=self._port,
            )
        return self._client

    def _bbg_security(self, ticker: str) -> str:
        """Convert plain ticker to Bloomberg security ID."""
        if " " in ticker:
            return ticker  # already formatted
        return f"{ticker} US Equity"

    # ---- Basic data ----

    def fetch_stock_list(self) -> pd.DataFrame:
        """S&P 500 constituent list.

        Returns DataFrame with: ts_code, name, industry, list_status, list_date
        """
        # Use a static S&P 500 list. Bloomberg MEMBERS request could be used
        # but is slow and rate-limited.
        sp500_path = Path(__file__).parent / "sp500_constituents.csv"
        if sp500_path.exists():
            return pd.read_csv(sp500_path)

        # Fallback: minimal list for testing
        logger.warning("sp500_constituents.csv not found, using minimal test list")
        return pd.DataFrame({
            "ts_code": ["AAPL", "MSFT", "GOOGL", "AMZN", "META"],
            "name": ["Apple", "Microsoft", "Alphabet", "Amazon", "Meta"],
            "industry": ["Technology"] * 5,
            "list_status": ["L"] * 5,
            "list_date": ["1980-12-12", "1986-03-13", "2004-08-19",
                          "1997-05-15", "2012-05-18"],
        })

    def fetch_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        """NYSE trading calendar."""
        try:
            import pandas_market_calendars as mcal
            nyse = mcal.get_calendar("NYSE")
            schedule = nyse.schedule(start_date=start_date, end_date=end_date)
            dates = schedule.index.strftime("%Y-%m-%d").tolist()
        except ImportError:
            # Fallback: weekdays only
            dr = pd.date_range(start_date, end_date, freq="B")
            dates = dr.strftime("%Y-%m-%d").tolist()

        return pd.DataFrame({
            "cal_date": dates,
            "is_open": [1] * len(dates),
        })

    # ---- Daily data (bulk) ----

    def fetch_daily_bulk(self, trade_date: str) -> pd.DataFrame:
        """Fetch daily OHLCV for all universe stocks on a given date.

        For backtesting, data is typically pre-fetched and cached in Parquet.
        This method fetches on-demand for single dates.
        """
        client = self._ensure_client()
        stocks = self.fetch_stock_list()
        rows = []
        for ticker in stocks["ts_code"]:
            sec = self._bbg_security(ticker)
            df = client._terminal_historical_request(
                sec,
                ["PX_OPEN", "PX_HIGH", "PX_LOW", "PX_LAST", "PX_VOLUME"],
                trade_date.replace("-", ""),
                trade_date.replace("-", ""),
                "DAILY",
            )
            if not df.empty:
                row = df.iloc[0].to_dict()
                row["ts_code"] = ticker
                row["trade_date"] = trade_date
                rows.append(row)

        if not rows:
            return pd.DataFrame()

        result = pd.DataFrame(rows)
        rename = {
            "PX_OPEN": "open", "PX_HIGH": "high", "PX_LOW": "low",
            "PX_LAST": "close", "PX_VOLUME": "volume",
        }
        return result.rename(columns=rename)

    def fetch_adj_factor_bulk(self, trade_date: str) -> pd.DataFrame:
        """Bloomberg prices are already adjusted. Return factor=1.0."""
        stocks = self.fetch_stock_list()
        return pd.DataFrame({
            "ts_code": stocks["ts_code"],
            "trade_date": trade_date,
            "adj_factor": 1.0,
        })

    def fetch_daily_indicator_bulk(self, trade_date: str) -> pd.DataFrame:
        """Fetch PE, PB, DY, market cap, price, shares for all stocks."""
        client = self._ensure_client()
        stocks = self.fetch_stock_list()
        securities = [self._bbg_security(t) for t in stocks["ts_code"]]

        df = client._terminal_reference_request(
            securities,
            ["PE_RATIO", "PX_TO_BOOK_RATIO", "DIVIDEND_YIELD",
             "CUR_MKT_CAP", "PX_LAST", "EQY_SH_OUT", "RETURN_COM_EQY"],
        )
        if df.empty:
            return pd.DataFrame()

        df["ts_code"] = df["security"].str.replace(" US Equity", "")
        df["trade_date"] = trade_date
        df = df.rename(columns={
            "PE_RATIO": "pe_ttm",
            "PX_TO_BOOK_RATIO": "pb",
            "DIVIDEND_YIELD": "dv_ttm",
            "CUR_MKT_CAP": "total_mv_raw",   # raw USD
            "PX_LAST": "close",
            "EQY_SH_OUT": "shares_out",        # millions
            "RETURN_COM_EQY": "roe",
        })
        # Convert market cap to millions for filter compatibility
        df["total_mv"] = pd.to_numeric(df["total_mv_raw"], errors="coerce") / 1e6
        df["market_cap"] = df["total_mv"]      # alias used by YAML filter
        return df[["ts_code", "trade_date", "close", "pe_ttm", "pb",
                   "dv_ttm", "total_mv", "market_cap", "shares_out", "roe"]]

    # ---- Market data (per stock) ----

    def fetch_market_snapshot(self, ts_code: str) -> pd.DataFrame:
        """Fetch current market data: price, market cap, PE, PB, DY, ROE, ROA."""
        cached = self._cache.get(ts_code, "market_snapshot")
        if cached is not None:
            logger.debug("Cache hit: %s/market_snapshot", ts_code)
            return cached
        client = self._ensure_client()
        sec = self._bbg_security(ts_code)
        client.fetch_market_data(sec)
        raw = client._store.get("market", pd.DataFrame())
        if raw.empty:
            return pd.DataFrame()
        raw = raw.rename(columns=FIELD_DISPLAY_NAMES)
        out = _rename_df(raw, _MARKET_MAP, ts_code)
        self._cache.put(ts_code, "market_snapshot", out)
        return out

    def fetch_price_history(self, ts_code: str, years: int = 2) -> pd.DataFrame:
        """Fetch daily OHLCV price history for a single stock."""
        cached = self._cache.get(ts_code, "price_history")
        if cached is not None:
            logger.debug("Cache hit: %s/price_history", ts_code)
            return cached
        client = self._ensure_client()
        sec = self._bbg_security(ts_code)
        client.fetch_daily_prices(sec, years=years)
        raw = client._store.get("daily_prices", pd.DataFrame())
        if raw.empty:
            return pd.DataFrame()
        out = raw.rename(columns={
            "PX_OPEN": "open", "PX_HIGH": "high", "PX_LOW": "low",
            "PX_LAST": "close", "PX_VOLUME": "volume",
        })
        out["ts_code"] = ts_code
        if "date" in out.columns:
            out = out.rename(columns={"date": "trade_date"})
        self._cache.put(ts_code, "price_history", out)
        return out

    # ---- Financial statements (per stock) ----

    def fetch_income(self, ts_code: str) -> pd.DataFrame:
        """Income statement for a single stock, all available years."""
        cached = self._cache.get(ts_code, "income")
        if cached is not None:
            logger.debug("Cache hit: %s/income", ts_code)
            return cached
        client = self._ensure_client()
        sec = self._bbg_security(ts_code)
        client.fetch_income_statement(sec, years=self._years)
        raw = client._store.get("income", pd.DataFrame())
        if raw.empty:
            return pd.DataFrame()

        # Rename Bloomberg fields to display names first
        raw = raw.rename(columns=FIELD_DISPLAY_NAMES)
        out = _rename_df(raw, _INCOME_MAP, ts_code)

        # Add ann_date from EDGAR if available
        out = self._add_ann_dates(out, ts_code)
        self._cache.put(ts_code, "income", out)
        return out

    def fetch_balancesheet(self, ts_code: str) -> pd.DataFrame:
        cached = self._cache.get(ts_code, "balancesheet")
        if cached is not None:
            logger.debug("Cache hit: %s/balancesheet", ts_code)
            return cached
        client = self._ensure_client()
        sec = self._bbg_security(ts_code)
        client.fetch_balance_sheet(sec, years=self._years)
        raw = client._store.get("balance", pd.DataFrame())
        if raw.empty:
            return pd.DataFrame()
        raw = raw.rename(columns=FIELD_DISPLAY_NAMES)
        out = _rename_df(raw, _BALANCE_MAP, ts_code)
        out = self._add_ann_dates(out, ts_code)
        self._cache.put(ts_code, "balancesheet", out)
        return out

    def fetch_cashflow(self, ts_code: str) -> pd.DataFrame:
        cached = self._cache.get(ts_code, "cashflow")
        if cached is not None:
            logger.debug("Cache hit: %s/cashflow", ts_code)
            return cached
        client = self._ensure_client()
        sec = self._bbg_security(ts_code)
        client.fetch_cashflow_statement(sec, years=self._years)
        client.fetch_shareholder_returns(sec, years=self._years)

        cf = client._store.get("cashflow", pd.DataFrame())
        sh = client._store.get("shareholder", pd.DataFrame())

        if cf.empty:
            return pd.DataFrame()

        # Merge shareholder returns (SBC, buybacks) into cashflow
        if not sh.empty and "date" in cf.columns and "date" in sh.columns:
            cf = cf.merge(sh[["date"] + [c for c in sh.columns if c not in cf.columns and c != "security"]],
                          on="date", how="left")

        cf = cf.rename(columns=FIELD_DISPLAY_NAMES)
        out = _rename_df(cf, _CASHFLOW_MAP, ts_code)
        out = self._add_ann_dates(out, ts_code)
        self._cache.put(ts_code, "cashflow", out)
        return out

    def fetch_financial_indicator(self, ts_code: str) -> pd.DataFrame:
        """Derived financial ratios (margins, leverage, efficiency)."""
        cached = self._cache.get(ts_code, "fina_indicator")
        if cached is not None:
            logger.debug("Cache hit: %s/fina_indicator", ts_code)
            return cached
        client = self._ensure_client()
        sec = self._bbg_security(ts_code)

        # Ensure financials are loaded
        client.fetch_all_financials(sec, years=self._years)
        metrics = client.calculate_all_derived_metrics()

        # calculate_all_derived_metrics returns a dict of DataFrames
        # Merge them into a single DataFrame on the "date" column
        dfs = [df for df in metrics.values()
               if isinstance(df, pd.DataFrame) and not df.empty]
        if not dfs:
            return pd.DataFrame()

        merged = dfs[0]
        for df in dfs[1:]:
            if "date" in merged.columns and "date" in df.columns:
                merged = merged.merge(df, on="date", how="outer")
            else:
                # Fallback: concat by position
                for col in df.columns:
                    if col not in merged.columns:
                        merged[col] = df[col].values[:len(merged)]

        merged["ts_code"] = ts_code
        if "date" in merged.columns:
            merged = merged.rename(columns={"date": "end_date"})
        self._cache.put(ts_code, "fina_indicator", merged)
        return merged

    def fetch_dividend(self, ts_code: str) -> pd.DataFrame:
        cached = self._cache.get(ts_code, "dividend")
        if cached is not None:
            logger.debug("Cache hit: %s/dividend", ts_code)
            return cached
        client = self._ensure_client()
        sec = self._bbg_security(ts_code)
        client.fetch_dividends(sec, years=self._years)
        raw = client._store.get("dividends", pd.DataFrame())
        if raw.empty:
            return pd.DataFrame()
        raw["ts_code"] = ts_code
        if "date" in raw.columns:
            raw = raw.rename(columns={"date": "ex_date"})
        self._cache.put(ts_code, "dividend", raw)
        return raw

    def fetch_top10_holders(self, ts_code: str) -> pd.DataFrame:
        """Bloomberg doesn't provide structured holder data via BDH.
        Return empty — agent can use web search if needed.
        """
        cached = self._cache.get(ts_code, "holders")
        if cached is not None:
            logger.debug("Cache hit: %s/holders", ts_code)
            return cached
        # No Bloomberg source for holders; cache the empty result to
        # avoid repeated lookups within the TTL window.
        out = pd.DataFrame()
        self._cache.put(ts_code, "holders", out)
        return out

    # ---- EDGAR filing date integration ----

    def _add_ann_dates(self, df: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """Add ann_date column using EDGAR filing dates.

        Critical for backtest time-boundary enforcement.
        Falls back to end_date + 90 days if EDGAR unavailable.
        """
        if "end_date" not in df.columns:
            return df

        filing_dates = self._get_filing_dates(ticker)

        if filing_dates is not None and not filing_dates.empty:
            # Merge on end_date
            df = df.merge(
                filing_dates[["end_date", "filing_date"]],
                on="end_date",
                how="left",
            )
            df["ann_date"] = df["filing_date"].fillna(
                pd.to_datetime(df["end_date"]) + timedelta(days=90)
            )
            df["ann_date"] = pd.to_datetime(df["ann_date"]).dt.strftime("%Y-%m-%d")
            df = df.drop(columns=["filing_date"], errors="ignore")
        else:
            # Conservative fallback: assume 90 days after period end
            df["ann_date"] = (
                pd.to_datetime(df["end_date"]) + timedelta(days=90)
            ).dt.strftime("%Y-%m-%d")

        return df

    def _get_filing_dates(self, ticker: str) -> Optional[pd.DataFrame]:
        """Fetch SEC filing dates from EDGAR for time-boundary enforcement."""
        if ticker in self._filing_dates:
            return self._filing_dates[ticker]

        try:
            from .edgar import fetch_filing_dates
            dates = fetch_filing_dates(ticker)
            self._filing_dates[ticker] = dates
            return dates
        except Exception as e:
            logger.warning("EDGAR filing dates unavailable for %s: %s", ticker, e)
            self._filing_dates[ticker] = None
            return None

    # ---- Stub methods for Protocol compliance ----
    # These are China-specific methods not applicable to US equities.

    def fetch_top10_floatholders(self, ts_code: str) -> pd.DataFrame:
        return pd.DataFrame()

    def fetch_pledge_stat(self, ts_code: str) -> pd.DataFrame:
        return pd.DataFrame()

    def fetch_pledge_detail(self, ts_code: str) -> pd.DataFrame:
        return pd.DataFrame()

    def fetch_fina_audit(self, ts_code: str) -> pd.DataFrame:
        return pd.DataFrame()

    def fetch_fina_mainbz(self, ts_code: str) -> pd.DataFrame:
        return pd.DataFrame()

    def fetch_stk_holdernumber(self, ts_code: str) -> pd.DataFrame:
        return pd.DataFrame()

    def fetch_stk_holdertrade(self, ts_code: str) -> pd.DataFrame:
        return pd.DataFrame()

    def fetch_share_float(self, ts_code: str) -> pd.DataFrame:
        return pd.DataFrame()

    def fetch_repurchase(self, ts_code: str) -> pd.DataFrame:
        """Buyback data is included in fetch_cashflow via SHAREHOLDER_FIELDS."""
        return pd.DataFrame()

    def fetch_disclosure_date(self, end_date: Optional[str] = None) -> pd.DataFrame:
        """Filing dates for all stocks. Uses EDGAR."""
        stocks = self.fetch_stock_list()
        rows = []
        for ticker in stocks["ts_code"]:
            dates = self._get_filing_dates(ticker)
            if dates is not None:
                for _, row in dates.iterrows():
                    rows.append({
                        "ts_code": ticker,
                        "end_date": row.get("end_date", ""),
                        "ann_date": row.get("filing_date", ""),
                    })
        return pd.DataFrame(rows) if rows else pd.DataFrame()

    def fetch_income_by_period(self, period: str) -> pd.DataFrame:
        """Not used in US provider (fetch per-stock instead)."""
        return pd.DataFrame()

    def fetch_balancesheet_by_period(self, period: str) -> pd.DataFrame:
        return pd.DataFrame()

    def fetch_cashflow_by_period(self, period: str) -> pd.DataFrame:
        return pd.DataFrame()

    def fetch_fina_indicator_by_period(self, period: str) -> pd.DataFrame:
        return pd.DataFrame()

    # ---- Cleanup ----

    def cleanup(self):
        if self._client is not None:
            self._client.cleanup()
            self._client = None
