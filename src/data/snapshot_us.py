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
import pickle
import time
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

    # SEC footnotes
    footnotes_md: str = ""

    # Macro & sector cycle indicators
    macro_indicators: dict = field(default_factory=dict)
    sector_indicator: dict = field(default_factory=dict)

    # Pre-computed quantitative metrics (avoid LLM recalculation)
    computed_metrics: dict = field(default_factory=dict)

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

    # --- Market data ---
    try:
        if hasattr(provider, "fetch_market_snapshot"):
            mkt = provider.fetch_market_snapshot(ts_code)
            if not mkt.empty:
                snap.daily_indicators = mkt
                snap.data_sources.append("market_data")
    except Exception as e:
        logger.warning("Failed to fetch market data for %s: %s", ts_code, e)

    try:
        if hasattr(provider, "fetch_price_history"):
            prices = provider.fetch_price_history(ts_code, years=2)
            if not prices.empty:
                if "trade_date" in prices.columns:
                    prices = prices[prices["trade_date"] <= cutoff_date]
                snap.price_history = prices
                snap.data_sources.append("price_history")
    except Exception as e:
        logger.warning("Failed to fetch price history for %s: %s", ts_code, e)

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

    # Macro & sector indicators (optional, non-blocking)
    try:
        if hasattr(provider, "fetch_macro_snapshot"):
            snap.macro_indicators = provider.fetch_macro_snapshot()
            if snap.macro_indicators:
                snap.data_sources.append("macro")
    except Exception as e:
        logger.warning("Macro indicators unavailable: %s", e)

    try:
        if hasattr(provider, "fetch_sector_indicator") and snap.industry:
            snap.sector_indicator = provider.fetch_sector_indicator(snap.industry)
            if snap.sector_indicator:
                snap.data_sources.append("sector_indicator")
    except Exception as e:
        logger.warning("Sector indicator unavailable for %s: %s", snap.industry, e)

    # EDGAR footnotes (optional, non-blocking)
    try:
        from .bloomberg.edgar import get_footnotes_markdown
        snap.footnotes_md = get_footnotes_markdown(ts_code)
        if snap.footnotes_md:
            snap.data_sources.append("edgar_footnotes")
    except Exception as e:
        logger.warning("EDGAR footnotes unavailable for %s: %s", ts_code, e)

    # Pre-compute quantitative metrics (GG, owner earnings, etc.)
    snap.computed_metrics = _compute_quantitative_metrics(snap)
    if snap.computed_metrics:
        snap.data_sources.append("computed_metrics")

    return snap


def _compute_quantitative_metrics(snap: USStockSnapshot) -> dict:
    """Pre-compute GG, owner earnings, and related metrics from Bloomberg data.

    These are pure arithmetic — no LLM judgment needed.
    """
    import numpy as np

    metrics = {}
    cf = snap.cashflow
    inc = snap.income
    bs = snap.balancesheet
    mkt = snap.daily_indicators

    if cf.empty or inc.empty:
        return metrics

    # Sort by end_date descending
    date_col = "end_date"
    if date_col not in cf.columns:
        return metrics
    cf = cf.sort_values(date_col, ascending=False)
    inc = inc.sort_values(date_col, ascending=False)
    if not bs.empty and date_col in bs.columns:
        bs = bs.sort_values(date_col, ascending=False)

    # --- Helper: safe float extraction ---
    def _val(df, col, row=0):
        if col in df.columns and len(df) > row:
            v = df.iloc[row].get(col)
            if pd.notna(v):
                return float(v)
        return None

    def _vals(df, col, n=5):
        """Get up to n years of values."""
        if col not in df.columns:
            return []
        return [float(v) for v in df[col].head(n) if pd.notna(v)]

    # --- Market cap (normalized to millions) ---
    market_cap = None
    if not mkt.empty:
        mc = _val(mkt, "total_mv") or _val(mkt, "market_cap")
        if mc and mc > 0:
            # Normalize: if value > 1B, it's in raw USD → convert to millions
            if mc > 1_000_000:
                mc = mc / 1e6
            market_cap = mc

    if not market_cap:
        # Fallback: price × shares (shares_outstanding is in millions)
        if not snap.price_history.empty and not mkt.empty:
            price = _val(snap.price_history.sort_values(
                "trade_date" if "trade_date" in snap.price_history.columns else "date",
                ascending=False), "close")
            shares = _val(mkt, "shares_outstanding")
            if price and shares:
                market_cap = price * shares  # price × millions of shares = millions USD

    metrics["market_cap_m"] = market_cap

    # --- Core cash flow components (latest year) ---
    ocf = _val(cf, "ocf")
    capex = _val(cf, "capex")
    da = _val(cf, "dep_amort")
    sbc = _val(cf, "sbc")
    divs = _val(cf, "dividends_paid")
    buybacks = _val(cf, "share_repurchases")
    ni = _val(inc, "net_income")
    revenue = _val(inc, "revenue")
    ebitda = _val(inc, "ebitda")
    interest = _val(inc, "interest_expense")

    # Make capex/divs positive for calculations (Bloomberg reports as negative)
    if capex and capex < 0:
        capex = abs(capex)
    if divs and divs < 0:
        divs = abs(divs)
    if buybacks and buybacks < 0:
        buybacks = abs(buybacks)

    metrics["ocf"] = ocf
    metrics["capex"] = capex
    metrics["da"] = da
    metrics["sbc"] = sbc
    metrics["dividends_paid"] = divs
    metrics["buybacks"] = buybacks
    metrics["net_income"] = ni
    metrics["revenue"] = revenue
    metrics["ebitda"] = ebitda

    # --- Maintenance CapEx (conservative: D&A × 0.9) ---
    maint_capex = None
    if da:
        maint_capex = da * 0.9  # Conservative default coefficient
    elif capex:
        maint_capex = capex * 0.7  # Fallback if no D&A
    metrics["maint_capex"] = maint_capex
    metrics["maint_capex_coeff"] = 0.9

    # --- Owner Earnings ---
    if ni is not None and da is not None and maint_capex is not None:
        oe = ni + da - maint_capex
        metrics["owner_earnings"] = round(oe, 1)
        if sbc and ni and abs(ni) > 0 and sbc / abs(ni) > 0.20:
            metrics["owner_earnings_sbc_adj"] = round(oe - sbc, 1)
            metrics["sbc_material"] = True
        else:
            metrics["owner_earnings_sbc_adj"] = round(oe - (sbc or 0), 1)
            metrics["sbc_material"] = False

    # --- FCF ---
    if ocf is not None and capex is not None:
        metrics["free_cash_flow"] = round(ocf - capex, 1)

    # --- Coarse Return R ---
    if ni is not None and market_cap and market_cap > 0:
        # Payout ratio: 3-year average
        ni_vals = _vals(inc, "net_income", 3)
        div_vals = _vals(cf, "dividends_paid", 3)
        div_vals = [abs(d) for d in div_vals if d]

        if ni_vals and div_vals:
            avg_payout = sum(div_vals) / max(sum(abs(n) for n in ni_vals if n > 0), 1)
            avg_payout = min(avg_payout, 1.0)  # Cap at 100%
        else:
            avg_payout = 0.30  # Default 30%

        # 3-year average buybacks
        bb_vals = _vals(cf, "share_repurchases", 3)
        bb_vals = [abs(b) for b in bb_vals if b]
        avg_bb = sum(bb_vals) / max(len(bb_vals), 1) if bb_vals else 0

        tax_q = 0.15  # US qualified dividend tax
        R = (ni * avg_payout * (1 - tax_q) + avg_bb) / market_cap * 100
        metrics["coarse_return_R"] = round(R, 2)
        metrics["payout_ratio_avg"] = round(avg_payout * 100, 1)
        metrics["avg_buybacks_3y"] = round(avg_bb, 1)

        # SBC-adjusted R
        ni_adj = ni - (sbc or 0)
        R_adj = (ni_adj * avg_payout * (1 - tax_q) + avg_bb) / market_cap * 100
        metrics["coarse_return_R_adj"] = round(R_adj, 2)

    # --- Refined Return GG (AA / Market Cap) ---
    if ocf is not None and maint_capex is not None and market_cap and market_cap > 0:
        # AA = OCF - Maintenance CapEx
        aa = ocf - maint_capex
        metrics["aa_baseline"] = round(aa, 1)

        # GG = AA / Market Cap
        gg = aa / market_cap * 100
        metrics["gg_primary"] = round(gg, 2)

        # SBC-adjusted
        aa_ex_sbc = aa - (sbc or 0)
        gg_ex_sbc = aa_ex_sbc / market_cap * 100
        metrics["aa_ex_sbc"] = round(aa_ex_sbc, 1)
        metrics["gg_ex_sbc"] = round(gg_ex_sbc, 2)

        # Safety margin vs Threshold II (7.3%)
        threshold_ii = 7.3
        metrics["gg_vs_threshold"] = round(gg - threshold_ii, 2)

    # --- Net Shareholder Return ---
    if buybacks is not None or divs is not None:
        nsr = (buybacks or 0) + (divs or 0) - (sbc or 0)
        metrics["net_shareholder_return"] = round(nsr, 1)

    # --- FCF history (for distribution capacity check) ---
    fcf_history = []
    ocf_vals = _vals(cf, "ocf", 5)
    capex_vals = _vals(cf, "capex", 5)
    for o, c in zip(ocf_vals, capex_vals):
        fcf_history.append(round(o - abs(c), 1))
    metrics["fcf_history"] = fcf_history
    metrics["fcf_positive_years"] = sum(1 for f in fcf_history if f > 0)

    # --- Debt metrics ---
    if not bs.empty:
        total_equity = _val(bs, "total_equity")
        lt_debt = _val(bs, "lt_debt")
        st_debt = _val(bs, "st_debt")
        cash = _val(bs, "cash_and_equivalents")
        total_debt = (lt_debt or 0) + (st_debt or 0)
        metrics["total_debt"] = round(total_debt, 1)
        metrics["net_debt"] = round(total_debt - (cash or 0), 1)
        if total_equity and total_equity > 0:
            metrics["debt_to_equity"] = round(total_debt / total_equity, 2)
        # Interest coverage
        if interest and interest > 0 and ebitda:
            metrics["interest_coverage"] = round(ebitda / interest, 2)

    # --- Graham Number ---
    if ni is not None and not bs.empty:
        shares = None
        if not mkt.empty:
            shares = _val(mkt, "shares_outstanding")
        total_equity = _val(bs, "total_equity")
        if shares and shares > 0 and total_equity and total_equity > 0 and ni > 0:
            eps = ni / shares
            bvps = total_equity / shares
            if eps > 0 and bvps > 0:
                metrics["graham_number"] = round((22.5 * eps * bvps) ** 0.5, 2)
                metrics["eps_ttm"] = round(eps, 2)
                metrics["bvps"] = round(bvps, 2)

    # --- Gross margin (for screening) ---
    gp_vals = _vals(inc, "gross_profit", 5)
    rev_vals = _vals(inc, "revenue", 5)
    if gp_vals and rev_vals:
        margins = [g / r * 100 for g, r in zip(gp_vals, rev_vals) if r and r > 0]
        if margins:
            metrics["gross_margin_latest"] = round(margins[0], 1)
            metrics["gross_margin_avg_3y"] = round(sum(margins[:3]) / len(margins[:3]), 1)

    # --- Altman Z-Score (bankruptcy predictor) ---
    if not bs.empty and revenue:
        total_assets = _val(bs, "total_assets")
        total_liabilities = _val(bs, "total_liabilities")
        current_assets = _val(bs, "current_assets")
        current_liabilities = _val(bs, "current_liabilities")
        total_equity = _val(bs, "total_equity")
        retained_earnings = None  # Not directly available; approximate
        if total_assets and total_assets > 0:
            wc = (current_assets or 0) - (current_liabilities or 0)
            # Approximate retained earnings as equity - assumed paid-in capital
            # Use total_equity as proxy (conservative)
            re_proxy = total_equity if total_equity else 0

            X1 = wc / total_assets  # Working capital / Total assets
            X2 = re_proxy / total_assets  # Retained earnings / Total assets
            X3 = (ebitda or 0) / total_assets  # EBIT / Total assets
            X4 = (market_cap or 0) / total_liabilities if total_liabilities and total_liabilities > 0 else 0
            X5 = revenue / total_assets  # Sales / Total assets

            z_score = 1.2 * X1 + 1.4 * X2 + 3.3 * X3 + 0.6 * X4 + 1.0 * X5
            metrics["altman_z_score"] = round(z_score, 2)
            if z_score > 2.99:
                metrics["altman_zone"] = "safe"
            elif z_score > 1.81:
                metrics["altman_zone"] = "grey"
            else:
                metrics["altman_zone"] = "distress"

    # --- Cash burn rate & runway ---
    if ocf is not None and ocf < 0:
        cash = _val(bs, "cash_and_equivalents") if not bs.empty else None
        if cash and cash > 0:
            monthly_burn = abs(ocf) / 12
            metrics["cash_burn_monthly"] = round(monthly_burn, 1)
            metrics["cash_runway_months"] = round(cash / monthly_burn, 1)
        metrics["ocf_negative"] = True
    else:
        metrics["ocf_negative"] = False

    # --- Revenue growth (YoY and QoQ proxy) ---
    if len(rev_vals) >= 2:
        metrics["revenue_growth_yoy"] = round((rev_vals[0] / rev_vals[1] - 1) * 100, 1)
    if len(rev_vals) >= 3:
        metrics["revenue_growth_2y_cagr"] = round(((rev_vals[0] / rev_vals[2]) ** 0.5 - 1) * 100, 1)
    if len(rev_vals) >= 5:
        # Revenue trajectory: accelerating or decelerating?
        recent_growth = (rev_vals[0] / rev_vals[1] - 1) if rev_vals[1] else 0
        older_growth = (rev_vals[2] / rev_vals[3] - 1) if len(rev_vals) > 3 and rev_vals[3] else 0
        if recent_growth > older_growth + 0.05:
            metrics["revenue_trajectory"] = "accelerating"
        elif recent_growth < older_growth - 0.05:
            metrics["revenue_trajectory"] = "decelerating"
        else:
            metrics["revenue_trajectory"] = "stable"

    # --- Price/Sales ---
    if market_cap and rev_vals:
        metrics["price_to_sales"] = round(market_cap / rev_vals[0], 2) if rev_vals[0] > 0 else None

    # --- Gross margin trend ---
    if gp_vals and rev_vals and len(gp_vals) >= 3:
        gm_latest = gp_vals[0] / rev_vals[0] * 100 if rev_vals[0] > 0 else 0
        gm_2y_ago = gp_vals[2] / rev_vals[2] * 100 if len(rev_vals) > 2 and rev_vals[2] > 0 else 0
        if gm_latest and gm_2y_ago:
            gm_change = gm_latest - gm_2y_ago
            metrics["gross_margin_trend_2y"] = round(gm_change, 1)
            if gm_change > 3:
                metrics["gross_margin_direction"] = "expanding"
            elif gm_change < -3:
                metrics["gross_margin_direction"] = "compressing"
            else:
                metrics["gross_margin_direction"] = "stable"

    return metrics


def get_or_create_us_snapshot(
    ts_code: str,
    cutoff_date: str,
    max_age_hours: int = 24,
    **kwargs,
) -> USStockSnapshot:
    """Load cached snapshot if fresh, else create and cache.

    Args:
        ts_code: Ticker symbol (e.g., 'AAPL')
        cutoff_date: Cutoff date 'YYYY-MM-DD'
        max_age_hours: Maximum cache age in hours (default 24)
        **kwargs: Passed through to create_us_snapshot

    Returns:
        USStockSnapshot (from cache or freshly created)
    """
    cache_dir = Path("data") / "snapshots" / "us"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{ts_code}_{cutoff_date}.pickle"

    if cache_file.exists():
        age_hours = (time.time() - cache_file.stat().st_mtime) / 3600
        if age_hours < max_age_hours:
            logger.info(
                "Loading cached snapshot: %s @ %s (%.1fh old)",
                ts_code, cutoff_date, age_hours,
            )
            try:
                with open(cache_file, "rb") as f:
                    return pickle.load(f)
            except Exception as e:
                logger.warning("Failed to load cached snapshot, recreating: %s", e)

    # Create fresh
    snap = create_us_snapshot(ts_code, cutoff_date, **kwargs)

    # Cache
    try:
        with open(cache_file, "wb") as f:
            pickle.dump(snap, f)
        logger.info("Cached snapshot: %s @ %s", ts_code, cutoff_date)
    except Exception as e:
        logger.warning("Failed to cache snapshot: %s", e)

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

    # Market Data: price/market cap from price_history on cutoff date (accurate),
    # ratios (PE, PB, etc.) from reference data (Bloomberg point-in-time)
    if not snap.daily_indicators.empty or not snap.price_history.empty:
        lines.append("## Market Data (as of cutoff date)")

        # Get closing price on cutoff date from price history (authoritative)
        cutoff_close = None
        shares_out = None
        if not snap.price_history.empty:
            date_col = "trade_date" if "trade_date" in snap.price_history.columns else "date"
            ph_sorted = snap.price_history.sort_values(date_col, ascending=False)
            # Use most recent row at or before cutoff
            cutoff_close = float(ph_sorted["close"].iloc[0])

        # Shares outstanding from reference data
        ref_row = snap.daily_indicators.iloc[0] if not snap.daily_indicators.empty else None
        if ref_row is not None:
            so = ref_row.get("shares_outstanding")
            if pd.notna(so):
                shares_out = float(so)

        if cutoff_close is not None:
            lines.append(f"- **Last Price ($)**: {cutoff_close:,.2f}")
            if shares_out is not None:
                mktcap_m = cutoff_close * shares_out  # shares in millions
                lines.append(f"- **Market Cap ($M)**: {mktcap_m:,.0f}")

        # Ratios from reference data (less time-sensitive)
        if ref_row is not None:
            for col, label, fmt in [
                ("pe_ttm", "P/E (TTM)", ",.2f"),
                ("pb", "P/B", ",.2f"),
                ("eps_ttm", "EPS (TTM, $)", ",.2f"),
                ("dv_ttm", "Dividend Yield (%)", ",.2f"),
                ("roe", "ROE (%)", ",.2f"),
                ("roa", "ROA (%)", ",.2f"),
                ("shares_outstanding", "Shares Outstanding (M)", ",.2f"),
            ]:
                val = ref_row.get(col)
                if pd.notna(val):
                    lines.append(f"- **{label}**: {float(val):{fmt}}")
        lines.append("")

    # Price History Summary
    if not snap.price_history.empty:
        ph = snap.price_history.sort_values(
            "trade_date" if "trade_date" in snap.price_history.columns else "date",
            ascending=False,
        )
        lines.append("## Price History (recent 60 trading days)")
        date_col = "trade_date" if "trade_date" in ph.columns else "date"
        recent = ph.head(60)
        lines.append(f"| Date | Close | Volume |")
        lines.append(f"|------|------:|-------:|")
        for _, r in recent.head(20).iterrows():
            d = r.get(date_col, "")
            c = r.get("close", 0)
            v = r.get("volume", 0)
            lines.append(f"| {d} | {c:,.2f} | {v:,.0f} |")
        if len(recent) > 20:
            lines.append(f"| ... | ({len(recent)-20} more rows) | ... |")

        # 52-week high/low
        if "close" in ph.columns:
            hi = ph["close"].max()
            lo = ph["close"].min()
            last = ph["close"].iloc[0]
            lines.append(f"\n**52-Week Range**: ${lo:,.2f} - ${hi:,.2f} (Current: ${last:,.2f})")
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

    # Macro Environment
    if snap.macro_indicators:
        m = snap.macro_indicators
        lines.append("## Macro Environment")
        if m.get("us_10y") is not None:
            lines.append(f"- **US 10Y Yield**: {m['us_10y']:.2f}%")
        if m.get("us_2y") is not None:
            lines.append(f"- **US 2Y Yield**: {m['us_2y']:.2f}%")
        if m.get("yield_curve_slope") is not None:
            status = "INVERTED" if m.get("yield_curve_inverted") else "Normal"
            lines.append(f"- **Yield Curve (10Y-2Y)**: {m['yield_curve_slope']:.3f}% ({status})")
        if m.get("credit_spread_ig") is not None:
            lines.append(f"- **IG Credit Spread**: {m['credit_spread_ig']:.0f}bp")
        if m.get("credit_spread_hy") is not None:
            lines.append(f"- **HY Credit Spread**: {m['credit_spread_hy']:.0f}bp")
        if m.get("pmi_mfg") is not None:
            status = "Expansion" if m["pmi_mfg"] > 50 else "Contraction"
            lines.append(f"- **ISM Manufacturing PMI**: {m['pmi_mfg']:.1f} ({status})")
        if m.get("vix") is not None:
            lines.append(f"- **VIX**: {m['vix']:.1f}")
        if m.get("fed_funds") is not None:
            lines.append(f"- **Fed Funds Rate**: {m['fed_funds']:.2f}%")
        if m.get("capacity_util") is not None:
            lines.append(f"- **Capacity Utilization**: {m['capacity_util']:.1f}%")
        if m.get("consumer_conf") is not None:
            lines.append(f"- **Consumer Confidence**: {m['consumer_conf']:.1f}")
        if m.get("pmi_new_orders") is not None:
            lines.append(f"- **ISM New Orders**: {m['pmi_new_orders']:.1f}")
        if m.get("pmi_inventories") is not None:
            lines.append(f"- **ISM Inventories**: {m['pmi_inventories']:.1f}")
        if m.get("orders_inventory_spread") is not None:
            lines.append(f"- **Orders-Inventory Spread**: {m['orders_inventory_spread']:+.1f} ({m.get('inventory_cycle_phase', 'N/A')})")
        if m.get("us_cpi_yoy") is not None:
            lines.append(f"- **US CPI YoY**: {m['us_cpi_yoy']:.1f}%")
        if m.get("us_ppi_yoy") is not None:
            lines.append(f"- **US PPI YoY**: {m['us_ppi_yoy']:.1f}%")
        if m.get("ppi_cpi_spread") is not None:
            lines.append(f"- **PPI-CPI Spread**: {m['ppi_cpi_spread']:+.2f}pp")
        if m.get("wholesale_inv_chg") is not None:
            lines.append(f"- **Wholesale Inventories MoM**: {m['wholesale_inv_chg']:+.1f}%")
        if m.get("inv_sales_ratio") is not None:
            lines.append(f"- **Inventory/Sales Ratio**: {m['inv_sales_ratio']:.2f}")
        if m.get("china_pmi_mfg") is not None:
            status = "Expansion" if m["china_pmi_mfg"] > 50 else "Contraction"
            lines.append(f"- **China Manufacturing PMI**: {m['china_pmi_mfg']:.1f} ({status})")
        if m.get("china_ppi_yoy") is not None:
            lines.append(f"- **China PPI YoY**: {m['china_ppi_yoy']:.1f}% ({m.get('china_cycle_signal', 'N/A')})")
        if m.get("china_cpi_yoy") is not None:
            lines.append(f"- **China CPI YoY**: {m['china_cpi_yoy']:.1f}%")
        lines.append("")

    # Sector Cycle Indicator
    if snap.sector_indicator:
        si = snap.sector_indicator
        lines.append("## Sector Cycle Indicator")
        lines.append(f"- **Indicator**: {si.get('name', 'N/A')} ({si.get('ticker', '')})")
        if si.get("last") is not None:
            lines.append(f"- **Current**: {si['last']:.2f}")
        if si.get("52w_high") is not None:
            lines.append(f"- **52-Week Range**: {si['52w_low']:.2f} - {si['52w_high']:.2f}")
        if si.get("52w_percentile") is not None:
            lines.append(f"- **52-Week Percentile**: {si['52w_percentile']:.1%}")
            lines.append(f"- **Trough Score**: {si.get('trough_score', 0):.3f} (1.0 = deep trough, 0.0 = peak)")
        lines.append("")

    # Pre-Computed Quantitative Metrics
    if snap.computed_metrics:
        m = snap.computed_metrics
        lines.append("## Pre-Computed Quantitative Metrics")
        lines.append("")
        lines.append("These are calculated from Bloomberg data. Use directly — do not recalculate.")
        lines.append("")

        if m.get("market_cap_m"):
            lines.append(f"**Market Cap**: ${m['market_cap_m']:,.0f}M")
        lines.append("")

        # Owner Earnings
        if m.get("owner_earnings") is not None:
            lines.append("### Owner Earnings")
            lines.append(f"- Owner Earnings: ${m['owner_earnings']:,.1f}M")
            lines.append(f"- Owner Earnings (SBC-adj): ${m.get('owner_earnings_sbc_adj', 0):,.1f}M")
            lines.append(f"- Maintenance CapEx: ${m.get('maint_capex', 0):,.1f}M (D&A × {m.get('maint_capex_coeff', 0.9)})")
            lines.append(f"- SBC Material: {m.get('sbc_material', False)}")
            lines.append("")

        # Returns
        if m.get("coarse_return_R") is not None:
            lines.append("### Return Rates")
            lines.append(f"- **Coarse Return R**: {m['coarse_return_R']:.2f}%")
            lines.append(f"- **Coarse Return R (SBC-adj)**: {m.get('coarse_return_R_adj', 0):.2f}%")
            lines.append(f"- Payout Ratio (3yr avg): {m.get('payout_ratio_avg', 0):.1f}%")
            lines.append(f"- Avg Buybacks (3yr): ${m.get('avg_buybacks_3y', 0):,.1f}M")
            lines.append("")

        if m.get("gg_primary") is not None:
            lines.append(f"- **Refined GG**: {m['gg_primary']:.2f}%")
            lines.append(f"- **GG (ex-SBC)**: {m.get('gg_ex_sbc', 0):.2f}%")
            lines.append(f"- **GG vs Threshold II (7.3%)**: {m.get('gg_vs_threshold', 0):+.2f}pp")
            lines.append(f"- AA Baseline: ${m.get('aa_baseline', 0):,.1f}M")
            lines.append(f"- AA (ex-SBC): ${m.get('aa_ex_sbc', 0):,.1f}M")
            lines.append("")

        # Shareholder Returns
        if m.get("net_shareholder_return") is not None:
            lines.append("### Shareholder Returns")
            lines.append(f"- Net Shareholder Return: ${m['net_shareholder_return']:,.1f}M (Buybacks + Divs - SBC)")
            lines.append(f"- FCF History: {m.get('fcf_history', [])}")
            lines.append(f"- FCF Positive Years: {m.get('fcf_positive_years', 0)}/5")
            lines.append("")

        # Debt & Leverage
        if m.get("total_debt") is not None:
            lines.append("### Debt & Leverage")
            lines.append(f"- Total Debt: ${m['total_debt']:,.1f}M")
            lines.append(f"- Net Debt: ${m.get('net_debt', 0):,.1f}M")
            if m.get("debt_to_equity") is not None:
                lines.append(f"- **Debt/Equity**: {m['debt_to_equity']:.2f}")
            if m.get("interest_coverage") is not None:
                lines.append(f"- Interest Coverage: {m['interest_coverage']:.1f}x")
            lines.append("")

        # Graham Number
        if m.get("graham_number") is not None:
            lines.append("### Graham Number")
            lines.append(f"- Graham Number: ${m['graham_number']:.2f}")
            lines.append(f"- EPS (TTM): ${m.get('eps_ttm', 0):.2f}")
            lines.append(f"- BVPS: ${m.get('bvps', 0):.2f}")
            lines.append("")

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

    # SEC Filing Footnotes
    if snap.footnotes_md:
        lines.append("")
        lines.append("## SEC Filing Footnotes (10-K)")
        lines.append(snap.footnotes_md)

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
