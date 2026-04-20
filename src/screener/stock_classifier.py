"""
Stock Classifier — Auto-route tickers to the best strategy.

Pure Python, no LLM. Uses pre-computed metrics + Bloomberg data
to classify stocks into: quality_yield, cyclical, cigar_butt, turnaround, growth.

Usage:
    from src.screener.stock_classifier import classify_stock, classify_batch

    result = classify_stock("AAPL")
    # → {"ticker": "AAPL", "strategy": "quality_yield", "confidence": "HIGH", ...}

    results = classify_batch(["AAPL", "AFRM", "OXY", "HPQ"])
    # → [{"ticker": ..., "strategy": ..., ...}, ...]

CLI:
    python -m src.screener.stock_classifier AAPL AFRM OXY DAL OPEN
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Cyclical industries (from us_cyclical strategy)
# Includes Bloomberg sector names (Energy, Materials, Industrials)
# and sub-industry keywords
CYCLICAL_INDUSTRIES = {
    # Bloomberg sector-level
    "energy", "materials",
    # Sub-industries
    "oil", "gas", "petroleum", "semiconductor", "steel",
    "aluminum", "mining", "chemicals", "auto", "airlines", "shipping",
    "construction", "paper", "forest", "copper", "metals",
    "industrial", "aerospace", "defense",
}

# Industries excluded from cigar butt NAV analysis
CIGAR_EXCLUDED = {
    "banks", "insurance", "asset management", "capital markets",
    "mortgage", "reit", "financial",
}


@dataclass
class ClassificationResult:
    ticker: str
    strategy: str          # quality_yield, cyclical, cigar_butt, turnaround, growth
    confidence: str        # HIGH, MEDIUM, LOW
    reason: str            # One-line explanation
    secondary: str = ""    # Alternative strategy if confidence is LOW
    metrics: dict = field(default_factory=dict)  # Key metrics used for classification


def classify_stock(
    ticker: str,
    provider=None,
    snapshot=None,
) -> ClassificationResult:
    """Classify a single stock into the best strategy.

    Args:
        ticker: Stock ticker (e.g., 'AAPL')
        provider: BloombergProvider instance (optional, will create if None)
        snapshot: Pre-existing USStockSnapshot (optional, will create if None)

    Returns:
        ClassificationResult with strategy recommendation
    """
    # Get or create snapshot with pre-computed metrics
    if snapshot is None:
        from src.data.snapshot_us import get_or_create_us_snapshot
        import datetime
        cutoff = datetime.date.today().strftime("%Y-%m-%d")
        try:
            snapshot = get_or_create_us_snapshot(ticker, cutoff)
        except Exception as e:
            logger.warning("Failed to create snapshot for %s: %s", ticker, e)
            return ClassificationResult(
                ticker=ticker, strategy="unknown", confidence="LOW",
                reason=f"Data unavailable: {e}"
            )

    m = snapshot.computed_metrics or {}
    industry = (snapshot.industry or "").lower()

    # Extract key classification metrics
    pe = None
    pb = None
    if not snapshot.daily_indicators.empty:
        row = snapshot.daily_indicators.iloc[0]
        pe = float(row.get("pe_ttm")) if pd.notna(row.get("pe_ttm")) else None
        pb = float(row.get("pb")) if pd.notna(row.get("pb")) else None

    z_score = m.get("altman_z_score")
    z_zone = m.get("altman_zone", "unknown")
    ocf_negative = m.get("ocf_negative", False)
    revenue_growth = m.get("revenue_growth_yoy")
    revenue_trajectory = m.get("revenue_trajectory", "unknown")
    gross_margin = m.get("gross_margin_latest")
    gm_direction = m.get("gross_margin_direction", "unknown")
    cash_runway = m.get("cash_runway_months")
    ps = m.get("price_to_sales")
    gg = m.get("gg_primary")
    debt_to_equity = m.get("debt_to_equity")
    market_cap = m.get("market_cap_m")

    metrics = {
        "pe": pe, "pb": pb, "z_score": z_score, "z_zone": z_zone,
        "ocf_negative": ocf_negative, "revenue_growth_yoy": revenue_growth,
        "gross_margin": gross_margin, "gm_direction": gm_direction,
        "ps": ps, "gg": gg, "debt_to_equity": debt_to_equity,
        "cash_runway": cash_runway, "industry": industry,
        "revenue_trajectory": revenue_trajectory,
    }

    # ================================================================
    # Classification rules (ordered by specificity)
    # ================================================================

    # --- Rule 1: Distress / Turnaround ---
    # Negative earnings + high volatility + potential bankruptcy risk
    is_turnaround = False
    turnaround_reasons = []

    if z_zone == "distress":
        is_turnaround = True
        turnaround_reasons.append(f"Z-score distress zone ({z_score:.1f})")

    if ocf_negative and cash_runway and cash_runway < 36:
        is_turnaround = True
        turnaround_reasons.append(f"Burning cash, {cash_runway:.0f}m runway")

    if pe is not None and pe < 0:
        is_turnaround = True
        turnaround_reasons.append("Negative earnings")
    elif pe is None and ocf_negative:
        is_turnaround = True
        turnaround_reasons.append("No PE + negative OCF")

    if revenue_growth and revenue_growth > 20 and ocf_negative:
        is_turnaround = True
        turnaround_reasons.append(f"High growth ({revenue_growth:.0f}%) but burning cash")

    if ps and ps > 5 and (pe is None or pe < 0):
        is_turnaround = True
        turnaround_reasons.append(f"High P/S ({ps:.1f}x) with no earnings")

    # Recently turned profitable — still turnaround if P/S is high
    # and gross margins are volatile (fintech, proptech pattern)
    if pe and pe > 0 and ps and ps > 3 and revenue_growth and revenue_growth > 20:
        if gm_direction in ("compressing", "expanding"):
            is_turnaround = True
            turnaround_reasons.append(
                f"Recently profitable (PE={pe:.0f}) but P/S={ps:.1f}x + volatile margins"
            )

    # No data available — likely speculative/small company
    if pe is None and pb is None and market_cap and market_cap < 10000:
        is_turnaround = True
        turnaround_reasons.append("No PE/PB data + small cap — likely speculative")

    if is_turnaround and len(turnaround_reasons) >= 2:
        return ClassificationResult(
            ticker=ticker, strategy="turnaround", confidence="HIGH",
            reason="; ".join(turnaround_reasons), metrics=metrics,
        )
    elif is_turnaround:
        # Single turnaround signal — might be temporary
        pass  # Fall through to other checks

    # --- Rule 2: Cigar Butt (Deep Value) ---
    if pb is not None and pb < 0.7:
        is_excluded = any(ex in industry for ex in CIGAR_EXCLUDED)
        if not is_excluded:
            confidence = "HIGH" if pb < 0.5 else "MEDIUM"
            return ClassificationResult(
                ticker=ticker, strategy="cigar_butt", confidence=confidence,
                reason=f"P/B={pb:.2f} (deep discount to book value)",
                secondary="quality_yield" if gg and gg > 5 else "",
                metrics=metrics,
            )

    # --- Rule 3: Cyclical ---
    is_cyclical_industry = any(kw in industry for kw in CYCLICAL_INDUSTRIES)

    if is_cyclical_industry:
        confidence = "HIGH"
        reason = f"Cyclical industry: {industry}"

        # Check if also qualifies for QY
        if gg and gg > 7.3 and pe and 0 < pe < 15:
            confidence = "MEDIUM"
            reason += f" (also passes QY: GG={gg:.1f}%, PE={pe:.0f})"
            return ClassificationResult(
                ticker=ticker, strategy="cyclical", confidence=confidence,
                reason=reason, secondary="quality_yield", metrics=metrics,
            )

        return ClassificationResult(
            ticker=ticker, strategy="cyclical", confidence=confidence,
            reason=reason, metrics=metrics,
        )

    # Revenue volatility check (for non-obvious cyclicals)
    if revenue_growth is not None and m.get("revenue_growth_2y_cagr") is not None:
        rev_spread = abs(revenue_growth - m["revenue_growth_2y_cagr"])
        if rev_spread > 20:  # Highly volatile revenue
            return ClassificationResult(
                ticker=ticker, strategy="cyclical", confidence="MEDIUM",
                reason=f"Revenue highly volatile (1Y={revenue_growth:.0f}%, 2Y CAGR={m['revenue_growth_2y_cagr']:.0f}%)",
                secondary="turnaround" if ocf_negative else "quality_yield",
                metrics=metrics,
            )

    # --- Rule 4: High Growth (no dedicated strategy yet) ---
    if revenue_growth and revenue_growth > 30 and gross_margin and gross_margin > 40:
        if pe and pe > 30:
            return ClassificationResult(
                ticker=ticker, strategy="growth", confidence="MEDIUM",
                reason=f"High growth ({revenue_growth:.0f}% rev) + high margin ({gross_margin:.0f}%) + expensive (PE={pe:.0f})",
                secondary="turnaround" if ocf_negative else "quality_yield",
                metrics=metrics,
            )

    # --- Rule 5: Quality Yield (default for profitable companies) ---
    if pe and 0 < pe < 30 and gg is not None:
        if gg > 7.3:
            return ClassificationResult(
                ticker=ticker, strategy="quality_yield", confidence="HIGH",
                reason=f"GG={gg:.1f}% > 7.3% threshold, PE={pe:.0f}",
                metrics=metrics,
            )
        elif gg > 3:
            return ClassificationResult(
                ticker=ticker, strategy="quality_yield", confidence="MEDIUM",
                reason=f"GG={gg:.1f}% (marginal), PE={pe:.0f}",
                secondary="cyclical" if is_cyclical_industry else "",
                metrics=metrics,
            )

    # --- Rule 6: Turnaround fallback ---
    if is_turnaround:
        return ClassificationResult(
            ticker=ticker, strategy="turnaround", confidence="MEDIUM",
            reason="; ".join(turnaround_reasons),
            secondary="quality_yield" if pe and pe > 0 else "",
            metrics=metrics,
        )

    # --- Default: Quality Yield ---
    reason = "Default classification"
    if pe and pe > 0:
        reason = f"Profitable (PE={pe:.0f}), no strong signal for other strategies"
    elif pe is None:
        reason = "PE unavailable, defaulting to quality analysis"

    return ClassificationResult(
        ticker=ticker, strategy="quality_yield", confidence="LOW",
        reason=reason, metrics=metrics,
    )


def classify_batch(
    tickers: List[str],
    provider=None,
) -> List[ClassificationResult]:
    """Classify multiple stocks."""
    results = []
    for ticker in tickers:
        result = classify_stock(ticker, provider=provider)
        results.append(result)
    return results


# Strategy path mapping
STRATEGY_PATHS = {
    "quality_yield": "strategies/us_qy/strategy.yaml",
    "cyclical": "strategies/us_cyclical/strategy.yaml",
    "cigar_butt": "strategies/us_cigar/strategy.yaml",
    "turnaround": "strategies/us_turnaround/strategy.yaml",
    "growth": "strategies/us_qy/strategy.yaml",  # Fallback to QY for now
}


def get_strategy_path(strategy: str) -> str:
    """Get the strategy YAML path for a classification."""
    return STRATEGY_PATHS.get(strategy, STRATEGY_PATHS["quality_yield"])


# ---- CLI ----
def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.screener.stock_classifier AAPL AFRM OXY ...")
        print("\nClassifies stocks into: quality_yield, cyclical, cigar_butt, turnaround, growth")
        sys.exit(1)

    tickers = [t.upper() for t in sys.argv[1:]]

    print(f"Classifying {len(tickers)} stocks...\n")
    print(f"{'Ticker':<8} {'Strategy':<16} {'Conf':<8} {'Reason'}")
    print(f"{'─'*8} {'─'*16} {'─'*8} {'─'*50}")

    results = classify_batch(tickers)
    for r in results:
        secondary = f" (alt: {r.secondary})" if r.secondary else ""
        print(f"{r.ticker:<8} {r.strategy:<16} {r.confidence:<8} {r.reason[:60]}{secondary}")

    # Summary
    from collections import Counter
    counts = Counter(r.strategy for r in results)
    print(f"\nSummary: {dict(counts)}")


if __name__ == "__main__":
    main()
