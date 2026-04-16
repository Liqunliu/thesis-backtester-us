"""yfinance DataProvider for thesis-backtester (Bloomberg fallback).

Uses yfinance API directly — no external collector dependency.
Adds EDGAR filing dates for time-boundary enforcement.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
    _HAS_YF = True
except ImportError:
    _HAS_YF = False
    logger.warning("yfinance not installed. Run: pip install yfinance")


class YFinanceProvider:
    """DataProvider implementation using yfinance (free, no API key).

    Usage:
        from src.data.yfinance_us import YFinanceProvider
        provider = YFinanceProvider()
        income = provider.fetch_income("AAPL")
    """

    def __init__(self, years: int = 5):
        if not _HAS_YF:
            raise ImportError("yfinance not installed")
        self._years = years
        self._ticker_cache: dict[str, yf.Ticker] = {}
        self._filing_dates: dict[str, Optional[pd.DataFrame]] = {}

    @property
    def name(self) -> str:
        return "yfinance"

    def _get_ticker(self, ts_code: str) -> yf.Ticker:
        if ts_code not in self._ticker_cache:
            self._ticker_cache[ts_code] = yf.Ticker(ts_code)
        return self._ticker_cache[ts_code]

    # ---- Basic data ----

    def fetch_stock_list(self) -> pd.DataFrame:
        sp500_path = Path(__file__).parent.parent / "bloomberg" / "sp500_constituents.csv"
        if sp500_path.exists():
            return pd.read_csv(sp500_path)

        # Fallback: fetch from Wikipedia
        try:
            table = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
            df = table[0][["Symbol", "Security", "GICS Sector"]].copy()
            df.columns = ["ts_code", "name", "industry"]
            df["ts_code"] = df["ts_code"].str.replace(".", "-", regex=False)
            df["list_status"] = "L"
            df["list_date"] = ""
            return df
        except Exception as e:
            logger.warning("Failed to fetch S&P 500 list: %s", e)
            return pd.DataFrame({
                "ts_code": ["AAPL", "MSFT", "GOOGL", "AMZN", "META"],
                "name": ["Apple", "Microsoft", "Alphabet", "Amazon", "Meta"],
                "industry": ["Technology"] * 5,
                "list_status": ["L"] * 5,
                "list_date": [""] * 5,
            })

    def fetch_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        try:
            import pandas_market_calendars as mcal
            nyse = mcal.get_calendar("NYSE")
            schedule = nyse.schedule(start_date=start_date, end_date=end_date)
            dates = schedule.index.strftime("%Y-%m-%d").tolist()
        except ImportError:
            dr = pd.date_range(start_date, end_date, freq="B")
            dates = dr.strftime("%Y-%m-%d").tolist()

        return pd.DataFrame({"cal_date": dates, "is_open": [1] * len(dates)})

    # ---- Daily data (bulk) ----

    def fetch_daily_bulk(self, trade_date: str) -> pd.DataFrame:
        stocks = self.fetch_stock_list()
        tickers = stocks["ts_code"].tolist()

        try:
            data = yf.download(
                tickers, start=trade_date, end=trade_date,
                group_by="ticker", progress=False, threads=True,
            )
        except Exception as e:
            logger.warning("yf.download failed for %s: %s", trade_date, e)
            return pd.DataFrame()

        rows = []
        for t in tickers:
            try:
                row_data = data[t] if len(tickers) > 1 else data
                if row_data.empty:
                    continue
                r = row_data.iloc[0]
                rows.append({
                    "ts_code": t, "trade_date": trade_date,
                    "open": r.get("Open"), "high": r.get("High"),
                    "low": r.get("Low"), "close": r.get("Close"),
                    "volume": r.get("Volume"),
                })
            except Exception:
                continue

        return pd.DataFrame(rows) if rows else pd.DataFrame()

    def fetch_adj_factor_bulk(self, trade_date: str) -> pd.DataFrame:
        stocks = self.fetch_stock_list()
        return pd.DataFrame({
            "ts_code": stocks["ts_code"],
            "trade_date": trade_date,
            "adj_factor": 1.0,
        })

    def fetch_daily_indicator_bulk(self, trade_date: str) -> pd.DataFrame:
        stocks = self.fetch_stock_list()
        rows = []
        for t in stocks["ts_code"]:
            try:
                info = self._get_ticker(t).info
                rows.append({
                    "ts_code": t, "trade_date": trade_date,
                    "pe_ttm": info.get("trailingPE"),
                    "pb": info.get("priceToBook"),
                    "dv_ttm": info.get("dividendYield", 0) * 100 if info.get("dividendYield") else 0,
                    "total_mv": info.get("marketCap", 0) / 1e6,  # to millions
                })
            except Exception:
                continue
            time.sleep(0.1)

        return pd.DataFrame(rows) if rows else pd.DataFrame()

    # ---- Financial statements (per stock) ----

    def _financials_to_df(self, raw: pd.DataFrame, ts_code: str,
                          col_map: dict) -> pd.DataFrame:
        """Convert yfinance transposed financials to protocol format."""
        if raw is None or raw.empty:
            return pd.DataFrame()

        # yfinance returns columns as dates, rows as metrics
        df = raw.T.copy()
        df.index.name = "end_date"
        df = df.reset_index()
        df["end_date"] = pd.to_datetime(df["end_date"]).dt.strftime("%Y-%m-%d")
        df["ts_code"] = ts_code

        # Rename columns: yfinance metric name → protocol name
        rename = {}
        for yf_name, proto_name in col_map.items():
            if yf_name in df.columns:
                rename[yf_name] = proto_name
        df = df.rename(columns=rename)

        # Convert to millions
        numeric_cols = [c for c in df.columns if c not in ("end_date", "ts_code")]
        for c in numeric_cols:
            df[c] = pd.to_numeric(df[c], errors="coerce") / 1e6

        # Add filing dates
        df = self._add_ann_dates(df, ts_code)
        return df

    def fetch_income(self, ts_code: str) -> pd.DataFrame:
        t = self._get_ticker(ts_code)
        try:
            raw = t.financials
        except Exception as e:
            logger.warning("fetch_income failed for %s: %s", ts_code, e)
            return pd.DataFrame()

        return self._financials_to_df(raw, ts_code, {
            "Total Revenue": "revenue",
            "Cost Of Revenue": "cost_of_revenue",
            "Gross Profit": "gross_profit",
            "Operating Income": "oper_income",
            "Pretax Income": "pretax_income",
            "Tax Provision": "income_tax",
            "Net Income": "net_income",
            "EBITDA": "ebitda",
            "Interest Expense": "interest_expense",
        })

    def fetch_balancesheet(self, ts_code: str) -> pd.DataFrame:
        t = self._get_ticker(ts_code)
        try:
            raw = t.balance_sheet
        except Exception as e:
            logger.warning("fetch_balancesheet failed for %s: %s", ts_code, e)
            return pd.DataFrame()

        return self._financials_to_df(raw, ts_code, {
            "Total Assets": "total_assets",
            "Total Liabilities Net Minority Interest": "total_liabilities",
            "Stockholders Equity": "total_equity",
            "Current Assets": "current_assets",
            "Current Liabilities": "current_liabilities",
            "Cash And Cash Equivalents": "cash_and_equivalents",
            "Accounts Receivable": "accounts_receivable",
            "Inventory": "inventory",
            "Accounts Payable": "accounts_payable",
            "Goodwill": "goodwill",
            "Other Intangible Assets": "intangible_assets",
            "Long Term Debt": "lt_debt",
            "Current Debt": "st_debt",
        })

    def fetch_cashflow(self, ts_code: str) -> pd.DataFrame:
        t = self._get_ticker(ts_code)
        try:
            raw = t.cashflow
        except Exception as e:
            logger.warning("fetch_cashflow failed for %s: %s", ts_code, e)
            return pd.DataFrame()

        return self._financials_to_df(raw, ts_code, {
            "Operating Cash Flow": "ocf",
            "Investing Cash Flow": "icf",  # yfinance uses "Investing Activities"
            "Financing Cash Flow": "fcf_financing",
            "Free Cash Flow": "free_cash_flow",
            "Capital Expenditure": "capex",
            "Depreciation And Amortization": "dep_amort",
            "Cash Dividends Paid": "dividends_paid",
            "Repurchase Of Capital Stock": "share_repurchases",
            "Stock Based Compensation": "sbc",
        })

    def fetch_financial_indicator(self, ts_code: str) -> pd.DataFrame:
        t = self._get_ticker(ts_code)
        try:
            info = t.info
        except Exception:
            return pd.DataFrame()

        return pd.DataFrame([{
            "ts_code": ts_code,
            "end_date": datetime.now().strftime("%Y-%m-%d"),
            "roe": info.get("returnOnEquity", 0) * 100 if info.get("returnOnEquity") else None,
            "roa": info.get("returnOnAssets", 0) * 100 if info.get("returnOnAssets") else None,
            "gross_margin": info.get("grossMargins", 0) * 100 if info.get("grossMargins") else None,
            "net_margin": info.get("profitMargins", 0) * 100 if info.get("profitMargins") else None,
            "current_ratio": info.get("currentRatio"),
            "debt_to_equity": info.get("debtToEquity"),
        }])

    def fetch_dividend(self, ts_code: str) -> pd.DataFrame:
        t = self._get_ticker(ts_code)
        try:
            divs = t.dividends
        except Exception:
            return pd.DataFrame()

        if divs is None or divs.empty:
            return pd.DataFrame()

        df = divs.reset_index()
        df.columns = ["ex_date", "amount"]
        df["ex_date"] = pd.to_datetime(df["ex_date"]).dt.strftime("%Y-%m-%d")
        df["ts_code"] = ts_code
        return df

    def fetch_top10_holders(self, ts_code: str) -> pd.DataFrame:
        t = self._get_ticker(ts_code)
        try:
            holders = t.institutional_holders
            if holders is not None and not holders.empty:
                holders["ts_code"] = ts_code
                return holders
        except Exception:
            pass
        return pd.DataFrame()

    # ---- EDGAR filing dates ----

    def _add_ann_dates(self, df: pd.DataFrame, ticker: str) -> pd.DataFrame:
        if "end_date" not in df.columns:
            return df

        filing_dates = self._get_filing_dates(ticker)
        if filing_dates is not None and not filing_dates.empty:
            df = df.merge(
                filing_dates[["end_date", "filing_date"]],
                on="end_date", how="left",
            )
            df["ann_date"] = df["filing_date"].fillna(
                pd.to_datetime(df["end_date"]) + timedelta(days=90)
            )
            df["ann_date"] = pd.to_datetime(df["ann_date"]).dt.strftime("%Y-%m-%d")
            df = df.drop(columns=["filing_date"], errors="ignore")
        else:
            df["ann_date"] = (
                pd.to_datetime(df["end_date"]) + timedelta(days=90)
            ).dt.strftime("%Y-%m-%d")
        return df

    def _get_filing_dates(self, ticker: str) -> Optional[pd.DataFrame]:
        if ticker in self._filing_dates:
            return self._filing_dates[ticker]
        try:
            from src.data.bloomberg.edgar import fetch_filing_dates
            dates = fetch_filing_dates(ticker)
            self._filing_dates[ticker] = dates
            return dates
        except Exception as e:
            logger.debug("EDGAR filing dates unavailable for %s: %s", ticker, e)
            self._filing_dates[ticker] = None
            return None

    # ---- Stub methods ----

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
        return pd.DataFrame()

    def fetch_disclosure_date(self, end_date: Optional[str] = None) -> pd.DataFrame:
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
        return pd.DataFrame()

    def fetch_balancesheet_by_period(self, period: str) -> pd.DataFrame:
        return pd.DataFrame()

    def fetch_cashflow_by_period(self, period: str) -> pd.DataFrame:
        return pd.DataFrame()

    def fetch_fina_indicator_by_period(self, period: str) -> pd.DataFrame:
        return pd.DataFrame()
