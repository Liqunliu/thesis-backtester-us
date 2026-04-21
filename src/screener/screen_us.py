"""
US Equity Screening Engine

Adapts the declarative quick_filter for US equities, using Bloomberg
or yfinance providers directly (no pre-populated Parquet required).

For backtesting, data is fetched on-demand at each cross-section date
with time-boundary enforcement.

Usage:
    from src.screener.screen_us import screen_us_at_date
    result = screen_us_at_date('2024-06-30', config)
"""
import logging
from typing import List, Optional

import pandas as pd

from src.data.provider import get_provider
from src.engine.config import StrategyConfig
from .quick_filter import (
    ScreenResult,
    _apply_filters,
    _compute_scores,
    _compute_tiers,
    _apply_industry_cap,
)
from .us_universe import get_sp500

logger = logging.getLogger(__name__)


def screen_us_at_date(
    cutoff_date: str,
    config: StrategyConfig,
    top_n: int = 30,
    provider_name: Optional[str] = None,
) -> ScreenResult:
    """Screen US equities at a given date using declarative config.

    Args:
        cutoff_date: Cross-section date (YYYY-MM-DD)
        config: Strategy config (filters, scoring, tiers from YAML)
        top_n: Return top N candidates
        provider_name: 'bloomberg' or 'yfinance' (default from config)
    """
    provider = get_provider(provider_name or config.provider_name)

    filters = config.get_filters()
    factors = config.get_scoring_factors()
    tiers = config.get_tiers()
    default_label = config.get_default_tier_label()
    exclude_rules = config.get_exclude_rules()
    include_industries = config.get_include_rules()
    industry_cap = config.get_industry_cap()

    result = ScreenResult(cutoff_date=cutoff_date)

    # 1. Get universe (S&P 500 + extra tickers from strategy config)
    stock_list = get_sp500()
    tickers = stock_list["ts_code"].tolist()

    extra_tickers = config.raw.get("screening", {}).get("extra_tickers", [])
    if extra_tickers:
        new_tickers = [t for t in extra_tickers if t not in tickers]
        if new_tickers:
            extra_df = pd.DataFrame({
                "ts_code": new_tickers,
                "name": new_tickers,
                "industry": ["Cyclical"] * len(new_tickers),
                "list_status": ["L"] * len(new_tickers),
                "list_date": [""] * len(new_tickers),
            })
            stock_list = pd.concat([stock_list, extra_df], ignore_index=True)
            tickers = stock_list["ts_code"].tolist()

    result.total_stocks = len(tickers)
    print(f"  Universe: {len(tickers)} stocks (S&P 500 + {len(extra_tickers)} extra)")

    # 2. Fetch indicator data for the cutoff date
    #    For each stock, get PE, PB, DY, market cap
    print(f"  Fetching indicators for {cutoff_date}...")
    df = _fetch_us_indicators(provider, tickers, cutoff_date)

    if df.empty:
        print(f"  Warning: no indicator data for {cutoff_date}")
        return result

    print(f"  Got indicators for {len(df)} stocks")

    # 3. Apply exclude rules (industry filtering)
    industry_map = stock_list.set_index("ts_code")["industry"].to_dict()
    df["industry"] = df["ts_code"].map(industry_map).fillna("")
    if exclude_rules:
        for rule in exclude_rules:
            field = rule.get("field", "")
            contains = rule.get("contains", [])
            if field == "industry" and contains:
                pattern = "|".join(contains)
                df = df[~df["industry"].str.contains(pattern, case=False, na=False)]

    # 3b. Apply include rules (filter DOWN to matching industries only)
    if include_industries:
        pattern = "|".join(include_industries)
        before_include = len(df)
        df = df[df["industry"].str.contains(pattern, case=False, na=False)]
        print(f"  Include industries filter: {before_include} -> {len(df)} stocks")

    # 4a. Apply cheap filters first (use bulk data: pe_ttm, pb, market_cap)
    cheap_filters = [f for f in filters if f["field"] in df.columns]
    df_cheap = _apply_filters(df.copy(), cheap_filters)
    print(f"  After cheap filters (PE/PB/mktcap): {len(df_cheap)} stocks")

    # 4b. Fetch financials only for survivors, compute expensive factors
    df_cheap = _compute_us_factors_inline(provider, df_cheap, cutoff_date)

    # 5. Apply all filters (including gross_margin, debt_to_equity, etc.)
    df = _apply_filters(df_cheap.copy(), filters)
    result.after_basic_filter = len(df)
    print(f"  After all filters: {len(df)} stocks")

    if df.empty:
        return result

    # 6. Score
    df = df.copy()
    df["tier_score"] = _compute_scores(df, factors)

    # 7. Tier classification
    df["tier_rating"] = _compute_tiers(df, tiers, default_label)

    # 8. Sort by score
    df = df.sort_values("tier_score", ascending=False)

    # 9. Industry cap
    if industry_cap and industry_cap > 0:
        industry_map = stock_list.set_index("ts_code")["industry"].to_dict()
        before = len(df)
        df = _apply_industry_cap(df, industry_map, industry_cap)
        if len(df) < before:
            print(f"  Industry cap ({industry_cap}/industry): {before} -> {len(df)}")

    # 10. Top N
    candidates = df.head(top_n).copy()

    # 11. Add names
    name_map = stock_list.set_index("ts_code")["name"].to_dict()
    ind_map = stock_list.set_index("ts_code")["industry"].to_dict()
    candidates["stock_name"] = candidates["ts_code"].map(name_map)
    if "industry" not in candidates.columns:
        candidates["industry"] = candidates["ts_code"].map(ind_map)

    # 12. Arrange output columns
    base_cols = ["ts_code", "stock_name", "industry"]
    factor_fields = [f["field"] for f in factors if f["field"] in candidates.columns]
    filter_fields = [
        f["field"] for f in filters
        if f["field"] in candidates.columns and f["field"] not in factor_fields
    ]
    score_cols = ["tier_score", "tier_rating"]
    output_cols = base_cols + filter_fields + factor_fields + ["total_mv"] + score_cols
    seen = set()
    unique_cols = []
    for c in output_cols:
        if c not in seen and c in candidates.columns:
            seen.add(c)
            unique_cols.append(c)
    candidates = candidates[unique_cols].reset_index(drop=True)

    result.candidates = candidates
    print(f"  Candidates: {len(candidates)} stocks")

    return result


def _fetch_us_indicators(
    provider, tickers: List[str], cutoff_date: str
) -> pd.DataFrame:
    """Fetch PE, PB, DY, market cap for all tickers.

    Uses provider.fetch_daily_indicator_bulk if available,
    falls back to per-stock fetching.
    """
    try:
        df = provider.fetch_daily_indicator_bulk(cutoff_date)
        if not df.empty:
            return df
    except Exception as e:
        logger.debug("Bulk indicator fetch failed: %s, falling back to per-stock", e)

    # Fallback: per-stock (slow but reliable)
    import time
    rows = []
    for t in tickers:
        try:
            fi = provider.fetch_financial_indicator(t)
            if not fi.empty:
                row = fi.iloc[0].to_dict()
                row["ts_code"] = t
                rows.append(row)
        except Exception:
            continue
        time.sleep(0.05)

    return pd.DataFrame(rows) if rows else pd.DataFrame()


def _compute_us_factors_inline(
    provider, df: pd.DataFrame, cutoff_date: str
) -> pd.DataFrame:
    """Compute US-specific screening factors inline.

    For full backtest, these should be pre-computed via factors/us/.
    For interactive screening, compute on-demand from provider data.
    """
    # Shareholder yield, owner earnings yield, and gg_quick
    # require cashflow data — fetch per stock (expensive)
    # Only compute if the scoring config references these fields

    need_fields = set()
    for col in ["shareholder_yield", "owner_earnings_yield", "gg_quick",
                "roe_avg_3y", "gross_margin_avg_3y", "debt_to_equity"]:
        if col not in df.columns:
            need_fields.add(col)

    if not need_fields:
        return df

    import time
    logger.info("Computing inline factors for %d stocks...", len(df))
    print(f"  Fetching financials for {len(df)} stocks (may take several minutes)...")

    for idx, row in df.iterrows():
        ticker = row["ts_code"]
        try:
            cf = provider.fetch_cashflow(ticker)
            inc = provider.fetch_income(ticker)
            bal = provider.fetch_balancesheet(ticker)
        except Exception:
            continue

        if cf.empty or inc.empty:
            continue

        # Sort oldest→newest, use last 3 years where available
        cf = cf.sort_values("end_date") if not cf.empty else cf
        inc = inc.sort_values("end_date") if not inc.empty else inc
        bal = bal.sort_values("end_date") if not bal.empty else bal

        latest_cf = cf.iloc[-1] if not cf.empty else {}
        latest_inc = inc.iloc[-1] if not inc.empty else {}
        latest_bal = bal.iloc[-1] if not bal.empty else {}
        mv = row.get("total_mv", 0)  # already in millions

        # gross_margin_avg_3y
        if "gross_margin_avg_3y" in need_fields and len(inc) >= 1:
            rev_col, gp_col = "revenue", "gross_profit"
            if rev_col in inc.columns and gp_col in inc.columns:
                recent = inc.tail(3)
                rev = pd.to_numeric(recent[rev_col], errors="coerce")
                gp = pd.to_numeric(recent[gp_col], errors="coerce")
                margins = (gp / rev * 100).dropna()
                if len(margins) > 0:
                    df.at[idx, "gross_margin_avg_3y"] = margins.mean()

        # debt_to_equity
        if "debt_to_equity" in need_fields and not bal.empty:
            lt = pd.to_numeric(latest_bal.get("lt_debt", 0) or 0, errors="coerce")
            st = pd.to_numeric(latest_bal.get("st_debt", 0) or 0, errors="coerce")
            eq = pd.to_numeric(latest_bal.get("total_equity", None), errors="coerce")
            if pd.notna(eq) and eq > 0:
                df.at[idx, "debt_to_equity"] = (lt + st) / eq

        # roe_avg_3y (use balance sheet ROE if not in bulk data)
        if "roe_avg_3y" in need_fields and len(inc) >= 1:
            if len(inc) >= 1 and not bal.empty:
                roe_vals = []
                for i in range(min(3, len(inc))):
                    ni = pd.to_numeric(inc.iloc[-(i+1)].get("net_income", None), errors="coerce")
                    eq_i = pd.to_numeric(bal.iloc[-1].get("total_equity", None), errors="coerce") if not bal.empty else None
                    if pd.notna(ni) and pd.notna(eq_i) and eq_i > 0:
                        roe_vals.append(ni / eq_i * 100)
                if roe_vals:
                    df.at[idx, "roe_avg_3y"] = sum(roe_vals) / len(roe_vals)

        # mv in millions (from bulk fetch — already converted)
        if mv and mv > 0:
            ocf = abs(float(latest_cf.get("ocf", 0) or 0))
            capex = abs(float(latest_cf.get("capex", 0) or 0))
            divs = abs(float(latest_cf.get("dividends_paid", 0) or 0))
            buybacks = abs(float(latest_cf.get("share_repurchases", 0) or 0))
            sbc = abs(float(latest_cf.get("sbc", 0) or 0))
            ni = float(latest_inc.get("net_income", 0) or 0)
            da = abs(float(latest_cf.get("dep_amort", 0) or 0))

            if "shareholder_yield" in need_fields:
                df.at[idx, "shareholder_yield"] = (divs + buybacks) / mv * 100

            if "owner_earnings_yield" in need_fields:
                maint = da * 1.0  # conservative default
                oe = ni + da - min(maint, capex)
                df.at[idx, "owner_earnings_yield"] = oe / mv * 100

            if "gg_quick" in need_fields:
                aa = ocf - capex + buybacks - divs - sbc
                df.at[idx, "gg_quick"] = aa / mv * 100

        time.sleep(0.1)  # avoid Bloomberg rate limits

    return df


def format_us_screen_result(result: ScreenResult) -> str:
    """Format US screening results as markdown."""
    lines = [
        f"# US Equity Screening: {result.cutoff_date}",
        "",
        f"- Universe: {result.total_stocks} stocks",
        f"- After filters: {result.after_basic_filter}",
        f"- Candidates: {len(result.candidates)}",
        "",
    ]

    if result.candidates.empty:
        lines.append("(No candidates)")
        return "\n".join(lines)

    if "tier_rating" in result.candidates.columns:
        tier_counts = result.candidates["tier_rating"].value_counts()
        lines.append("## Tier Distribution")
        for rating in tier_counts.index:
            count = tier_counts.get(rating, 0)
            if count > 0:
                lines.append(f"- {rating}: {count}")
        lines.append("")

    df = result.candidates
    lines.append("## Candidates")

    display_cols = [c for c in df.columns if c not in ("trade_date",)]
    header = "| Rank | " + " | ".join(display_cols) + " |"
    sep = "|------" + "|------" * len(display_cols) + "|"
    lines.append(header)
    lines.append(sep)

    for i, (_, row) in enumerate(df.iterrows(), 1):
        vals = []
        for c in display_cols:
            v = row.get(c, "")
            if isinstance(v, float):
                vals.append(f"{v:.2f}")
            else:
                vals.append(str(v))
        lines.append(f"| {i} | " + " | ".join(vals) + " |")

    return "\n".join(lines)
