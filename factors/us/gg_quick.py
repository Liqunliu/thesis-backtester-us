"""
Quick GG (Penetration Return Rate) for Screening

Simplified GG for pre-analysis ranking. The full 13-step refined GG
is computed by the agent during analysis — this is the fast screening proxy.

Formula:
  AA = OCF - CapEx + Buybacks - Debt Change - Dividends - SBC
  GG = AA / Market Cap × 100

Reference: calculate_qy_gg.py in AI_fundamental_investment_framework_us
"""
import pandas as pd
import numpy as np

META = {
    "id": "gg_quick",
    "name": "Quick GG (%)",
    "description": "Screening-grade penetration return rate (OCF-CapEx+Buybacks-Debt-Div-SBC)/MktCap",
    "data_needed": ["cashflow", "daily_indicator"],
    "type": "time_series",
}


def compute(df: pd.DataFrame) -> pd.Series:
    ocf = df.get("ocf", pd.Series(dtype="float64"))
    capex = df.get("capex", pd.Series(dtype="float64"))
    buybacks = df.get("share_repurchases", pd.Series(0, index=df.index))
    divs = df.get("dividends_paid", pd.Series(0, index=df.index))
    sbc = df.get("sbc", pd.Series(0, index=df.index))
    mv = df.get("total_mv", pd.Series(dtype="float64"))

    if ocf.empty or mv.empty:
        return pd.Series(pd.NA, index=df.index, dtype="float64")

    mv_safe = mv.replace(0, np.nan)

    # All cashflow items: outflows are negative, inflows positive
    # OCF is positive, CapEx is negative, Buybacks are negative, Divs are negative, SBC is positive
    aa = (
        ocf.fillna(0)
        + capex.fillna(0)        # CapEx is already negative
        - buybacks.abs().fillna(0)  # Buybacks: add back (returned to shareholders)
        + divs.fillna(0)         # Dividends: already negative
        - sbc.abs().fillna(0)    # SBC: deduct (real cost)
    )

    return (aa / mv_safe * 100).round(2)
