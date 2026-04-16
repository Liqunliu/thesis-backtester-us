"""
US Equity Snapshot Generator

Generates time-bounded data snapshots for US stocks, formatted in English
with USD amounts in millions. Strict ann_date filtering prevents look-ahead bias.

Time boundary rules (Layer 1 - data layer hard filter):
  - Financials: filtered by ann_date (SEC filing date), NOT end_date
  - Prices: trade_date <= cutoff_date
  - Dividends: ex_date <= cutoff_date

CLI:
    python -m src.data.snapshot_us AAPL 2024-06-30
    python -m src.data.snapshot_us AAPL 2024-06-30 --blind

Python:
    from src.data.snapshot_us import create_us_snapshot, us_snapshot_to_markdown
    snap = create_us_snapshot('AAPL', '2024-06-30')
    md = us_snapshot_to_markdown(snap, blind_mode=True)
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd

from .provider import get_provider
from .settings import SNAPSHOT_DIR

logger = logging.getLogger(__name__)


@dataclass
class USStockSnapshot:
    """Time-bounded data snapshot for a US equity."""
    ts_code: str
    stock_name: str
    cutoff_date: str
    generated_at: str
    industry: str = ""
    list_date: str = ""

    # Market data
    price_history: pd.DataFrame = field(default_factory=pd.DataFrame)
    daily_indicators: pd.DataFrame = field(default_factory=pd.DataFrame)

    # Fundamentals
    balancesheet: pd.DataFrame = field(default_factory=pd.DataFrame)
    income: pd.DataFrame = field(default_factory=pd.DataFrame)
    cashflow: pd.DataFrame = field(default_factory=pd.DataFrame)
    fina_indicator: pd.DataFrame = field(default_factory=pd.DataFrame)
    dividend: pd.DataFrame = field(default_factory=pd.DataFrame)
    holders: pd.DataFrame = field(default_factory=pd.DataFrame)

    # Metadata
    latest_report_period: str = ""
    data_sources: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def snapshot_id(self) -> str:
        raw = f"{self.ts_code}_{self.cutoff_date}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]


def create_us_snapshot(
    ts_code: str,
    cutoff_date: str,
    price_lookback_days: int = 365 * 3,
    provider_name: str = None,
) -> USStockSnapshot:
    """Generate a time-bounded snapshot for a US stock.

    Args:
        ts_code: Ticker symbol (e.g., 'AAPL')
        cutoff_date: Cutoff date 'YYYY-MM-DD' — no data after this
        price_lookback_days: Price history lookback (default 3 years)
        provider_name: 'bloomberg' or 'yfinance' (default from env)
    """
    provider = get_provider(provider_name or "bloomberg")

    # Stock info
    stock_list = provider.fetch_stock_list()
    stock_name, industry, list_date = ts_code, "", ""
    if not stock_list.empty:
        row = stock_list[stock_list["ts_code"] == ts_code]
        if not row.empty:
            r = row.iloc[0]
            stock_name = str(r.get("name", ts_code))
            industry = str(r.get("industry", ""))
            list_date = str(r.get("list_date", ""))

    snap = USStockSnapshot(
        ts_code=ts_code,
        stock_name=stock_name,
        industry=industry,
        list_date=list_date,
        cutoff_date=cutoff_date,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

    # --- Financials (filtered by ann_date) ---
    for attr, fetch_fn in [
        ("income", provider.fetch_income),
        ("balancesheet", provider.fetch_balancesheet),
        ("cashflow", provider.fetch_cashflow),
    ]:
        try:
            df = fetch_fn(ts_code)
            if not df.empty and "ann_date" in df.columns:
                df = df[df["ann_date"] <= cutoff_date]
            elif not df.empty and "end_date" in df.columns:
                # Fallback: keep reports ending 90+ days before cutoff
                safe = (pd.to_datetime(cutoff_date) - pd.Timedelta(days=90)).strftime("%Y-%m-%d")
                df = df[df["end_date"] <= safe]
            setattr(snap, attr, df)
            if not df.empty:
                snap.data_sources.append(attr)
        except Exception as e:
            logger.warning("Failed to fetch %s for %s: %s", attr, ts_code, e)

    # Financial indicators
    try:
        snap.fina_indicator = provider.fetch_financial_indicator(ts_code)
        if not snap.fina_indicator.empty:
            snap.data_sources.append("fina_indicator")
    except Exception:
        pass

    # Dividends
    try:
        div = provider.fetch_dividend(ts_code)
        if not div.empty and "ex_date" in div.columns:
            div = div[div["ex_date"] <= cutoff_date]
        snap.dividend = div
        if not div.empty:
            snap.data_sources.append("dividend")
    except Exception:
        pass

    # Holders
    try:
        snap.holders = provider.fetch_top10_holders(ts_code)
        if not snap.holders.empty:
            snap.data_sources.append("holders")
    except Exception:
        pass

    # Latest report period
    if not snap.income.empty and "end_date" in snap.income.columns:
        snap.latest_report_period = snap.income["end_date"].max()

    # Warnings
    if snap.income.empty:
        snap.warnings.append("No income statement data")
    if snap.balancesheet.empty:
        snap.warnings.append("No balance sheet data")
    if snap.cashflow.empty:
        snap.warnings.append("No cash flow data")

    return snap


# ---------------------------------------------------------------------------
# US holder anonymization
# ---------------------------------------------------------------------------

_US_INDEX_FUNDS = ["vanguard", "blackrock", "state street", "fidelity", "schwab"]
_US_HEDGE_FUNDS = ["citadel", "renaissance", "bridgewater", "millennium", "two sigma"]
_US_PENSIONS = ["calpers", "calstrs", "pension", "retirement"]


def _classify_us_holder(name: str) -> str:
    if not name:
        return "Unknown"
    lower = name.lower()
    for kw in _US_INDEX_FUNDS:
        if kw in lower:
            return "Large Index Fund Manager"
    for kw in _US_HEDGE_FUNDS:
        if kw in lower:
            return "Hedge Fund"
    for kw in _US_PENSIONS:
        if kw in lower:
            return "Pension Fund"
    if any(kw in lower for kw in ["bank", "trust", "capital", "asset", "investment"]):
        return "Institutional Investor"
    return "Other Institutional"


# ---------------------------------------------------------------------------
# Markdown output
# ---------------------------------------------------------------------------

def us_snapshot_to_markdown(snap: USStockSnapshot, blind_mode: bool = False) -> str:
    """Convert US snapshot to markdown for AI analysis."""
    lines = []

    # Header
    if blind_mode:
        lines.append("# Company Data Snapshot")
    else:
        lines.append(f"# {snap.stock_name} ({snap.ts_code}) Data Snapshot")

    lines.append("")
    lines.append(f"**Cutoff Date**: {snap.cutoff_date}")
    lines.append(f"**Currency**: USD (millions)")
    if snap.industry:
        lines.append(f"**Industry**: {snap.industry}")
    if snap.list_date:
        lines.append(f"**Listed**: {snap.list_date}")
    lines.append(f"**Latest Report Period**: {snap.latest_report_period}")
    lines.append(f"**Data Sources**: {', '.join(snap.data_sources)}")
    if snap.warnings:
        lines.append(f"**Warnings**: {'; '.join(snap.warnings)}")
    lines.append("")

    # Income Statement
    if not snap.income.empty:
        lines.append("## Income Statement")
        lines.append(_format_us_table(snap.income, [
            ("revenue", "Revenue"),
            ("cost_of_revenue", "Cost of Revenue"),
            ("gross_profit", "Gross Profit"),
            ("oper_income", "Operating Income"),
            ("ebitda", "EBITDA"),
            ("pretax_income", "Pretax Income"),
            ("income_tax", "Income Tax"),
            ("net_income", "Net Income"),
            ("interest_expense", "Interest Expense"),
        ]))

    # Balance Sheet
    if not snap.balancesheet.empty:
        lines.append("## Balance Sheet")
        lines.append(_format_us_table(snap.balancesheet, [
            ("total_assets", "Total Assets"),
            ("current_assets", "Current Assets"),
            ("cash_and_equivalents", "Cash & Equivalents"),
            ("accounts_receivable", "Accounts Receivable"),
            ("inventory", "Inventory"),
            ("total_liabilities", "Total Liabilities"),
            ("current_liabilities", "Current Liabilities"),
            ("st_debt", "Short-Term Debt"),
            ("lt_debt", "Long-Term Debt"),
            ("accounts_payable", "Accounts Payable"),
            ("total_equity", "Shareholders' Equity"),
            ("goodwill", "Goodwill"),
            ("intangible_assets", "Intangible Assets"),
        ]))

    # Cash Flow Statement
    if not snap.cashflow.empty:
        lines.append("## Cash Flow Statement")
        lines.append(_format_us_table(snap.cashflow, [
            ("ocf", "Operating Cash Flow"),
            ("icf", "Investing Cash Flow"),
            ("fcf_financing", "Financing Cash Flow"),
            ("free_cash_flow", "Free Cash Flow"),
            ("capex", "Capital Expenditure"),
            ("dep_amort", "Depreciation & Amortization"),
            ("dividends_paid", "Dividends Paid"),
            ("share_repurchases", "Share Repurchases"),
            ("sbc", "Stock-Based Compensation"),
        ]))

    # Financial Ratios
    if not snap.fina_indicator.empty:
        lines.append("## Financial Ratios (Latest)")
        fi = snap.fina_indicator.iloc[-1] if len(snap.fina_indicator) > 1 else snap.fina_indicator.iloc[0]
        for col, label in [
            ("roe", "ROE (%)"), ("roa", "ROA (%)"),
            ("gross_margin", "Gross Margin (%)"), ("net_margin", "Net Margin (%)"),
            ("current_ratio", "Current Ratio"), ("debt_to_equity", "Debt/Equity"),
        ]:
            val = fi.get(col)
            if pd.notna(val):
                lines.append(f"- {label}: {val:.2f}")
        lines.append("")

    # Dividend History
    if not snap.dividend.empty:
        lines.append("## Dividend History")
        div = snap.dividend.sort_values("ex_date", ascending=False).head(10)
        lines.append("| Ex-Date | Amount per Share |")
        lines.append("|---------|----------------|")
        for _, row in div.iterrows():
            lines.append(f"| {row.get('ex_date', 'N/A')} | ${row.get('amount', 0):.4f} |")
        lines.append("")

    # Institutional Holders
    if not snap.holders.empty:
        lines.append("## Institutional Holders")
        h = snap.holders.head(10)
        if blind_mode:
            lines.append("| Rank | Holder Type | Shares |")
            lines.append("|------|-----------|--------|")
            for i, (_, row) in enumerate(h.iterrows(), 1):
                name = str(row.get("Holder", row.get("holder_name", "")))
                attr = _classify_us_holder(name)
                shares = row.get("Shares", row.get("hold_amount", 0))
                lines.append(f"| {i} | {attr} | {shares:,.0f} |")
        else:
            lines.append("| Rank | Holder | Shares |")
            lines.append("|------|--------|--------|")
            for i, (_, row) in enumerate(h.iterrows(), 1):
                name = row.get("Holder", row.get("holder_name", "N/A"))
                shares = row.get("Shares", row.get("hold_amount", 0))
                lines.append(f"| {i} | {name} | {shares:,.0f} |")
        lines.append("")

    # Time boundary declaration
    lines.append("---")
    lines.append(f"> **Strict time boundary**: All data above is as of **{snap.cutoff_date}**.")
    lines.append(f"> Do NOT use any information after this date in your analysis.")
    lines.append(f"> Missing sections mean data was not available at this point in time.")
    if blind_mode:
        lines.append("> **Blind mode**: Company name and ticker are hidden. Analyze based on data only.")

    return "\n".join(lines)


def _format_us_table(
    df: pd.DataFrame,
    key_cols: list,
    n_periods: int = 5,
) -> str:
    """Format financial data as a markdown table with English labels and USD millions."""
    if df.empty or "end_date" not in df.columns:
        return "(No data)\n"

    df = df.drop_duplicates(subset=["end_date"], keep="last")
    df = df.sort_values("end_date").tail(n_periods)
    periods = df["end_date"].tolist()

    if not periods:
        return "(No data)\n"

    lines = []
    header = "| Metric | " + " | ".join(str(p) for p in periods) + " |"
    sep = "|--------|" + "|".join(["-------:"] * len(periods)) + "|"
    lines.append(header)
    lines.append(sep)

    for col, label in key_cols:
        if col not in df.columns:
            continue
        vals = []
        for _, row in df.iterrows():
            v = row.get(col)
            if pd.isna(v):
                vals.append("N/A")
            else:
                vals.append(f"{v:,.2f}")
        lines.append(f"| {label} | " + " | ".join(vals) + " |")

    lines.append("")
    return "\n".join(lines)


def save_us_snapshot(snap: USStockSnapshot) -> Path:
    """Save snapshot to disk."""
    out_dir = SNAPSHOT_DIR / "us"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{snap.ts_code}_{snap.cutoff_date}.md"
    path.write_text(us_snapshot_to_markdown(snap), encoding="utf-8")
    return path


# CLI
def main():
    import sys
    if len(sys.argv) < 3:
        print("Usage: python -m src.data.snapshot_us <ticker> <cutoff_date> [--blind]")
        print("Example: python -m src.data.snapshot_us AAPL 2024-06-30")
        sys.exit(1)

    ticker = sys.argv[1]
    cutoff = sys.argv[2]
    blind = "--blind" in sys.argv

    print(f"Generating US snapshot: {ticker} @ {cutoff}")
    snap = create_us_snapshot(ticker, cutoff)
    md = us_snapshot_to_markdown(snap, blind_mode=blind)
    print(md)

    path = save_us_snapshot(snap)
    print(f"\nSnapshot saved: {path}")


if __name__ == "__main__":
    main()
