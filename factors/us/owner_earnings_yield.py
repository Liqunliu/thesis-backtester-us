"""
Owner Earnings Yield (OE / Market Cap)

Buffett's owner earnings as a yield metric:
  OE = Net Income + D&A - Maintenance CapEx
  OE Yield = OE / Market Cap × 100

Maintenance CapEx estimated as D&A × coefficient (1.0 default for screening).
SBC-adjusted variant: OE_adj = OE - SBC
"""
import pandas as pd
import numpy as np

META = {
    "id": "owner_earnings_yield",
    "name": "Owner Earnings Yield (%)",
    "description": "(Net Income + D&A - Maint CapEx) / Market Cap × 100",
    "data_needed": ["income", "cashflow", "daily_indicator"],
    "type": "time_series",
}


def compute(df: pd.DataFrame) -> pd.Series:
    ni = df.get("net_income", pd.Series(dtype="float64"))
    da = df.get("dep_amort", pd.Series(dtype="float64"))
    capex = df.get("capex", pd.Series(dtype="float64"))
    mv = df.get("total_mv", pd.Series(dtype="float64"))

    if ni.empty or mv.empty:
        return pd.Series(pd.NA, index=df.index, dtype="float64")

    mv_safe = mv.replace(0, np.nan)
    da_val = da.abs().fillna(0)
    capex_val = capex.abs().fillna(0)

    # Maintenance CapEx ≈ D&A × 1.0 (conservative screening default)
    maint_capex = da_val * 1.0
    # Cap maintenance at actual CapEx (can't exceed total)
    maint_capex = maint_capex.clip(upper=capex_val)

    oe = ni.fillna(0) + da_val - maint_capex
    return (oe / mv_safe * 100).round(2)
