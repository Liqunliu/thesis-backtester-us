"""
US Equity Backtest Pipeline

Adapts the three-stage backtest (screen → agent → eval) for US equities.
Uses Bloomberg/yfinance providers, SPY benchmark, and English output.

Usage:
    python -m src.engine.launcher strategies/us_qy/strategy.yaml backtest-screen-us
    python -m src.engine.launcher strategies/us_qy/strategy.yaml backtest-agent-us
    python -m src.engine.launcher strategies/us_qy/strategy.yaml backtest-eval-us
"""
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, TYPE_CHECKING

import pandas as pd

from .pipeline import (
    generate_crosssection_dates,
    save_screen_csv,
    load_screen_csv,
    load_agent_reports,
    AgentProgress,
    _run_agent_concurrent,
    EvalSlice,
    _bt_dirs,
    _outcome_to_dict,
    _dict_to_outcome,
)

if TYPE_CHECKING:
    from src.engine.config import StrategyConfig


# ==================== Step 1: backtest-screen-us ====================

def step_screen_us(config: "StrategyConfig") -> List[str]:
    """Generate cross-section dates + screen US equities at each date."""
    from src.screener.screen_us import screen_us_at_date

    dates = generate_crosssection_dates(
        config.get_backtest_start(),
        config.get_backtest_end(),
        config.get_cross_section_interval(),
    )
    top_n = config.get_backtest_top_n()
    screen_dir, _, _ = _bt_dirs(config)

    print(f"US Backtest Screening: {config.name} v{config.version}")
    print(f"  Cross-sections: {len(dates)} ({dates[0]} ~ {dates[-1]})")
    print(f"  Interval: {config.get_cross_section_interval()}")
    print(f"  Top N: {top_n}")
    print(f"  Output: {screen_dir}")
    print()

    for i, date in enumerate(dates, 1):
        print(f"[{i}/{len(dates)}] {date}")
        result = screen_us_at_date(date, config, top_n=top_n)
        if not result.candidates.empty:
            csv_path = save_screen_csv(result.candidates, date, screen_dir)
            n = len(result.candidates)
            tier_info = ""
            if "tier_rating" in result.candidates.columns:
                dist = result.candidates["tier_rating"].value_counts()
                tier_info = " | " + ", ".join(f"{k}:{v}" for k, v in dist.items())
            print(f"  -> {n} stocks{tier_info} -> {csv_path.name}")
        else:
            print(f"  -> No candidates")

    print(f"\nDone: {len(dates)} cross-sections saved to {screen_dir}")
    return dates


# ==================== Step 2: backtest-agent-us ====================

def step_agent_us(config: "StrategyConfig", max_retry: int = 1, dry_run: bool = False) -> AgentProgress:
    """Read screen CSVs -> concurrent agent analysis -> save reports.

    Same logic as step_agent but with English labels.
    """
    screen_dir, reports_dir, _ = _bt_dirs(config)
    dates = generate_crosssection_dates(
        config.get_backtest_start(),
        config.get_backtest_end(),
        config.get_cross_section_interval(),
    )
    concurrency = config.get_agent_concurrency()

    tasks = []
    per_date_stats = []
    for date in dates:
        df = load_screen_csv(date, screen_dir)
        if df is None:
            print(f"Warning: no screen results for {date}, run backtest-screen-us first")
            continue
        batch_n = config.get_agent_batch_size(len(df))
        codes = df["ts_code"].head(batch_n).tolist()
        existing = load_agent_reports(reports_dir, date)
        new_codes = [c for c in codes if c not in existing]
        per_date_stats.append((date, batch_n, len(existing), len(new_codes)))
        for c in new_codes:
            tasks.append((c, date))

    print(f"US Agent Analysis{'(dry run)' if dry_run else ''}")
    print(f"  Cross-sections: {len(dates)}")
    print(f"  Concurrency: {concurrency}")
    print()
    print(f"  {'Date':<12} {'Selected':>8} {'Done':>6} {'Pending':>8}")
    print(f"  {'-'*12} {'-'*8} {'-'*6} {'-'*8}")
    for date, total, done, pending in per_date_stats:
        print(f"  {date:<12} {total:>8} {done:>6} {pending:>8}")

    total_pending = len(tasks)
    total_selected = sum(t for _, t, _, _ in per_date_stats)
    total_done = sum(d for _, _, d, _ in per_date_stats)
    print(f"  {'-'*12} {'-'*8} {'-'*6} {'-'*8}")
    print(f"  {'Total':<12} {total_selected:>8} {total_done:>6} {total_pending:>8}")

    if total_pending == 0:
        print("\nAll agent analyses complete.")
        return AgentProgress()

    est_minutes = total_pending * 5 / concurrency
    est_cost = total_pending * 0.50
    print(f"\n  Est. time: {est_minutes:.0f} min ({est_minutes/60:.1f} hours)")
    print(f"  Est. cost: ${est_cost:.1f} ({total_pending} stocks x $0.50)")
    print(f"  Reports: {reports_dir}")

    if dry_run:
        return AgentProgress(total=total_pending)

    print()
    progress = AgentProgress(total=len(tasks), start_time=time.time())

    for attempt in range(1 + max_retry):
        if attempt > 0:
            retry_tasks = [(f["ts_code"], f["cutoff_date"]) for f in progress.failed_list]
            progress.failed = 0
            progress.failed_list = []
            tasks = retry_tasks
            print(f"\n--- Retry round {attempt}: {len(tasks)} stocks ---\n")
        _run_agent_concurrent(tasks, config, reports_dir, concurrency, progress)
        if not progress.failed_list:
            break

    elapsed = time.time() - progress.start_time
    print(f"\n{'='*60}")
    print(f"Agent analysis complete")
    print(f"  Success: {progress.completed}/{progress.total}")
    print(f"  Failed: {progress.failed}")
    print(f"  Time: {elapsed/60:.1f} min")
    if progress.failed_list:
        print(f"\nFailed (re-run to retry):")
        for f in progress.failed_list:
            print(f"  {f['ts_code']} @ {f['cutoff_date']}: {f['error'][:80]}")
    print(f"{'='*60}")
    return progress


# ==================== Step 3: backtest-eval-us ====================

def step_eval_us(config: "StrategyConfig") -> Path:
    """Evaluate US backtest: 5 benchmarks + VETO avoidance + quintile analysis."""
    screen_dir, reports_dir, bt_dir = _bt_dirs(config)
    dates = generate_crosssection_dates(
        config.get_backtest_start(),
        config.get_backtest_end(),
        config.get_cross_section_interval(),
    )

    print(f"US Backtest Evaluation: {config.name} v{config.version}")
    print(f"  Cross-sections: {len(dates)}")
    print()

    # 1. Load data
    slices = []
    for date in dates:
        df = load_screen_csv(date, screen_dir)
        if df is None:
            continue
        reports = load_agent_reports(reports_dir, date)
        slices.append(EvalSlice(
            cutoff_date=date,
            candidates=df,
            agent_reports=reports,
        ))
        print(f"  {date}: {len(df)} candidates, {len(reports)} agent reports")

    if not slices:
        print("No data to evaluate. Run backtest-screen-us first.")
        return bt_dir

    # 2. Collect forward returns
    _collect_us_forward_returns(slices, bt_dir)

    # 3. Evaluate
    performance = _evaluate_us_baselines(slices, config)

    # 4. VETO avoidance analysis
    veto_analysis = _analyze_veto_avoidance(slices)

    # 5. Score quintile analysis
    quintile_analysis = _analyze_score_quintiles(slices)

    # 6. Generate report
    report = _format_us_eval_report(slices, performance, veto_analysis, quintile_analysis, config)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    report_path = bt_dir / f"backtest_report_us_{ts}.md"
    report_path.write_text(report, encoding="utf-8")

    # 7. Print summary
    print(f"\n{'='*60}")
    print(f"US Backtest Results (6-month forward)")
    print(f"{'='*60}")
    for key, bl in performance.items():
        stats = bl.get("stats_6m", {})
        if stats.get("count", 0) > 0:
            print(f"  {bl['label']}: "
                  f"mean={stats['mean']*100:+.1f}% "
                  f"win={stats['win_rate']*100:.0f}% "
                  f"n={stats['count']}")

    # Alpha
    mkt = performance.get("spy", {}).get("stats_6m", {}).get("mean")
    buy = performance.get("buy_signal", {}).get("stats_6m", {}).get("mean")
    if mkt is not None and buy is not None:
        print(f"\n  Alpha (6m): BUY signal vs SPY = {(buy-mkt)*100:+.1f}pp")

    if veto_analysis:
        print(f"\n  VETO avoidance: {veto_analysis.get('summary', 'N/A')}")

    print(f"\nReport: {report_path}")
    return report_path


def _collect_us_forward_returns(slices: List[EvalSlice], bt_dir: Path):
    """Collect forward returns using yfinance (works without Bloomberg)."""
    import yfinance as yf

    outcomes_dir = bt_dir / "outcomes_cache"
    outcomes_dir.mkdir(parents=True, exist_ok=True)

    total = sum(len(sl.candidates) for sl in slices)
    done = 0
    t0 = time.time()
    print(f"\nCollecting forward returns ({total} stocks)...")

    for sl in slices:
        codes = sl.candidates["ts_code"].tolist()
        cache_path = outcomes_dir / f"outcomes_{sl.cutoff_date}.json"
        cache = {}
        if cache_path.exists():
            try:
                cache = json.loads(cache_path.read_text())
            except Exception:
                pass

        for ticker in codes:
            done += 1
            if ticker in cache:
                sl.outcomes[ticker] = cache[ticker]
                continue

            try:
                # Fetch 13 months of price data after cutoff
                start = sl.cutoff_date
                end_dt = pd.to_datetime(start) + pd.Timedelta(days=400)
                hist = yf.download(ticker, start=start, end=end_dt.strftime("%Y-%m-%d"),
                                   progress=False)
                if hist.empty or len(hist) < 2:
                    continue

                p0 = float(hist["Close"].iloc[0])
                outcome = {"cutoff_price": p0}

                for months, key in [(1, "return_1m"), (3, "return_3m"),
                                     (6, "return_6m"), (12, "return_12m")]:
                    target_days = months * 21  # trading days
                    if len(hist) > target_days:
                        p1 = float(hist["Close"].iloc[target_days])
                        outcome[key] = (p1 - p0) / p0
                    else:
                        outcome[key] = None

                # Max drawdown (6m)
                if len(hist) > 126:
                    window = hist["Close"].iloc[:126]
                    peak = window.expanding().max()
                    dd = ((window - peak) / peak).min()
                    outcome["max_drawdown_6m"] = float(dd)

                sl.outcomes[ticker] = outcome
                cache[ticker] = outcome

            except Exception:
                pass

            if done % 50 == 0 or done == total:
                elapsed = time.time() - t0
                print(f"  [{done}/{total}] {elapsed:.0f}s")

        cache_path.write_text(json.dumps(cache, default=str))

    print(f"  Done: {done} stocks, {time.time()-t0:.0f}s")


def _evaluate_us_baselines(
    slices: List[EvalSlice],
    config: "StrategyConfig",
) -> Dict[str, dict]:
    """Five US benchmarks evaluation."""
    buy_threshold = 70

    # Collect returns by baseline
    baselines = {
        "spy": {"label": "SPY (S&P 500)", "returns_6m": []},
        "screen_all": {"label": "Screen Pool (equal-weight)", "returns_6m": []},
        "pass_pool": {"label": "PASS Pool (all veto gates clear)", "returns_6m": []},
        "buy_signal": {"label": f"BUY Signal (score >= {buy_threshold})", "returns_6m": []},
        "top5": {"label": "Top 5 by Score", "returns_6m": []},
    }

    # SPY benchmark
    try:
        import yfinance as yf
        spy_dates = [sl.cutoff_date for sl in slices]
        for date in spy_dates:
            end_dt = pd.to_datetime(date) + pd.Timedelta(days=200)
            hist = yf.download("SPY", start=date, end=end_dt.strftime("%Y-%m-%d"),
                               progress=False)
            if len(hist) > 126:
                p0 = float(hist["Close"].iloc[0])
                p1 = float(hist["Close"].iloc[126])
                baselines["spy"]["returns_6m"].append((p1 - p0) / p0)
    except Exception:
        pass

    for sl in slices:
        # Screen pool: all candidates with outcomes
        screen_returns = [
            sl.outcomes[t]["return_6m"]
            for t in sl.candidates["ts_code"]
            if t in sl.outcomes and sl.outcomes[t].get("return_6m") is not None
        ]
        baselines["screen_all"]["returns_6m"].extend(screen_returns)

        # PASS pool & BUY signal & Top 5
        for t, report in sl.agent_reports.items():
            if t not in sl.outcomes or sl.outcomes[t].get("return_6m") is None:
                continue
            ret = sl.outcomes[t]["return_6m"]
            syn = report.get("synthesis", {})
            score = syn.get("total_score", syn.get("综合评分", 0))
            try:
                score = float(score)
            except (ValueError, TypeError):
                score = 0

            # Check for veto
            veto = False
            for ch_out in report.get("chapter_outputs", {}).values():
                if isinstance(ch_out, dict):
                    for k, v in ch_out.items():
                        if k.endswith("_pass") and v is False:
                            veto = True
                        if k.endswith("_conclusion") and str(v).upper() == "VETO":
                            veto = True

            if not veto:
                baselines["pass_pool"]["returns_6m"].append(ret)
            if score >= buy_threshold:
                baselines["buy_signal"]["returns_6m"].append(ret)

        # Top 5 by score
        scored = []
        for t, report in sl.agent_reports.items():
            if t not in sl.outcomes or sl.outcomes[t].get("return_6m") is None:
                continue
            syn = report.get("synthesis", {})
            score = syn.get("total_score", syn.get("综合评分", 0))
            try:
                score = float(score)
            except (ValueError, TypeError):
                score = 0
            scored.append((score, sl.outcomes[t]["return_6m"]))
        scored.sort(reverse=True)
        for _, ret in scored[:5]:
            baselines["top5"]["returns_6m"].append(ret)

    # Compute stats
    for key, bl in baselines.items():
        returns = bl["returns_6m"]
        if returns:
            bl["stats_6m"] = {
                "count": len(returns),
                "mean": sum(returns) / len(returns),
                "median": sorted(returns)[len(returns) // 2],
                "win_rate": sum(1 for r in returns if r > 0) / len(returns),
                "best": max(returns),
                "worst": min(returns),
            }
        else:
            bl["stats_6m"] = {"count": 0}

    return baselines


def _analyze_veto_avoidance(slices: List[EvalSlice]) -> dict:
    """VETO avoidance alpha: compare forward returns of VETO'd vs PASS stocks."""
    veto_returns = []
    pass_returns = []

    for sl in slices:
        for t, report in sl.agent_reports.items():
            if t not in sl.outcomes or sl.outcomes[t].get("return_6m") is None:
                continue
            ret = sl.outcomes[t]["return_6m"]

            veto = False
            for ch_out in report.get("chapter_outputs", {}).values():
                if isinstance(ch_out, dict):
                    for k, v in ch_out.items():
                        if k.endswith("_pass") and v is False:
                            veto = True
                        if k.endswith("_conclusion") and str(v).upper() == "VETO":
                            veto = True

            if veto:
                veto_returns.append(ret)
            else:
                pass_returns.append(ret)

    result = {
        "veto_count": len(veto_returns),
        "pass_count": len(pass_returns),
    }

    if veto_returns and pass_returns:
        veto_mean = sum(veto_returns) / len(veto_returns)
        pass_mean = sum(pass_returns) / len(pass_returns)
        avoidance_alpha = pass_mean - veto_mean
        result["veto_mean_return"] = veto_mean
        result["pass_mean_return"] = pass_mean
        result["avoidance_alpha"] = avoidance_alpha
        result["summary"] = (
            f"PASS stocks: {pass_mean*100:+.1f}% vs VETO stocks: {veto_mean*100:+.1f}% "
            f"= {avoidance_alpha*100:+.1f}pp avoidance alpha"
        )
    else:
        result["summary"] = "Insufficient data for VETO avoidance analysis"

    return result


def _analyze_score_quintiles(slices: List[EvalSlice]) -> dict:
    """Score quintile analysis: test monotonicity of score → return relationship."""
    scored_returns = []

    for sl in slices:
        for t, report in sl.agent_reports.items():
            if t not in sl.outcomes or sl.outcomes[t].get("return_6m") is None:
                continue
            syn = report.get("synthesis", {})
            score = syn.get("total_score", syn.get("综合评分", 0))
            try:
                score = float(score)
            except (ValueError, TypeError):
                continue
            scored_returns.append((score, sl.outcomes[t]["return_6m"]))

    if len(scored_returns) < 10:
        return {"summary": "Insufficient data for quintile analysis"}

    scored_returns.sort(key=lambda x: x[0])
    n = len(scored_returns)
    q_size = n // 5

    quintiles = {}
    for qi in range(5):
        start = qi * q_size
        end = start + q_size if qi < 4 else n
        q_data = scored_returns[start:end]
        returns = [r for _, r in q_data]
        scores = [s for s, _ in q_data]
        quintiles[f"Q{qi+1}"] = {
            "score_range": f"{min(scores):.0f}-{max(scores):.0f}",
            "count": len(returns),
            "mean_return": sum(returns) / len(returns) if returns else 0,
            "win_rate": sum(1 for r in returns if r > 0) / len(returns) if returns else 0,
        }

    # Monotonicity check: Q5 should outperform Q1
    q1_mean = quintiles["Q1"]["mean_return"]
    q5_mean = quintiles["Q5"]["mean_return"]
    monotonic = q5_mean > q1_mean

    return {
        "quintiles": quintiles,
        "monotonic": monotonic,
        "q5_minus_q1": q5_mean - q1_mean,
        "summary": (
            f"Q5 ({quintiles['Q5']['score_range']}): {q5_mean*100:+.1f}% vs "
            f"Q1 ({quintiles['Q1']['score_range']}): {q1_mean*100:+.1f}% "
            f"= {(q5_mean-q1_mean)*100:+.1f}pp spread "
            f"({'monotonic' if monotonic else 'NOT monotonic'})"
        ),
    }


def _format_us_eval_report(
    slices: List[EvalSlice],
    performance: Dict,
    veto_analysis: dict,
    quintile_analysis: dict,
    config: "StrategyConfig",
) -> str:
    """Generate markdown evaluation report."""
    lines = [
        f"# US Backtest Report: {config.name} v{config.version}",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Configuration",
        f"- Period: {config.get_backtest_start()} to {config.get_backtest_end()}",
        f"- Interval: {config.get_cross_section_interval()}",
        f"- Cross-sections: {len(slices)}",
        f"- Benchmark: {config.get_benchmark()}",
        f"- Market parameters: Rf={config.get_market_parameters().get('risk_free_rate', 'N/A')}, "
        f"Threshold II={config.get_market_parameters().get('threshold_ii', 'N/A')}",
        "",
        "## 6-Month Forward Returns by Baseline",
        "",
        "| Baseline | Mean | Median | Win Rate | Best | Worst | N |",
        "|----------|------|--------|----------|------|-------|---|",
    ]

    for key, bl in performance.items():
        s = bl.get("stats_6m", {})
        if s.get("count", 0) > 0:
            lines.append(
                f"| {bl['label']} "
                f"| {s['mean']*100:+.1f}% "
                f"| {s['median']*100:+.1f}% "
                f"| {s['win_rate']*100:.0f}% "
                f"| {s['best']*100:+.1f}% "
                f"| {s['worst']*100:+.1f}% "
                f"| {s['count']} |"
            )
        else:
            lines.append(f"| {bl['label']} | N/A | N/A | N/A | N/A | N/A | 0 |")

    # Alpha
    lines.extend(["", "## Alpha Analysis", ""])
    mkt = performance.get("spy", {}).get("stats_6m", {}).get("mean")
    for key in ["screen_all", "pass_pool", "buy_signal", "top5"]:
        bl = performance.get(key, {})
        mean = bl.get("stats_6m", {}).get("mean")
        if mkt is not None and mean is not None:
            lines.append(f"- {bl['label']} vs SPY: **{(mean-mkt)*100:+.1f}pp** alpha")

    # VETO avoidance
    lines.extend(["", "## VETO Avoidance Analysis", ""])
    lines.append(f"- VETO'd stocks: {veto_analysis.get('veto_count', 0)}")
    lines.append(f"- PASS stocks: {veto_analysis.get('pass_count', 0)}")
    lines.append(f"- {veto_analysis.get('summary', 'N/A')}")

    # Quintile analysis
    lines.extend(["", "## Score Quintile Analysis", ""])
    lines.append(f"- {quintile_analysis.get('summary', 'N/A')}")
    if "quintiles" in quintile_analysis:
        lines.extend(["", "| Quintile | Score Range | Mean Return | Win Rate | N |",
                       "|----------|-----------|-------------|----------|---|"])
        for qname, qdata in quintile_analysis["quintiles"].items():
            lines.append(
                f"| {qname} "
                f"| {qdata['score_range']} "
                f"| {qdata['mean_return']*100:+.1f}% "
                f"| {qdata['win_rate']*100:.0f}% "
                f"| {qdata['count']} |"
            )

    return "\n".join(lines)
