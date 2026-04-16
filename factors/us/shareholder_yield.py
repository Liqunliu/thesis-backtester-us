"""
Shareholder Yield (Dividends + Buybacks) / Market Cap

Total capital returned to shareholders as % of market cap.
This is the primary screening factor for us-qy (weight 35%).

Net version deducts SBC dilution cost:
  Net Shareholder Yield = (Dividends + Buybacks - SBC) / Market Cap
"""
import pandas as pd
import numpy as np

META = {
    "id": "shareholder_yield",
    "name": "Shareholder Yield (%)",
    "description": "(Dividends Paid + Share Repurchases) / Market Cap × 100",
    "data_needed": ["cashflow", "daily_indicator"],
    "type": "time_series",
}


def compute(df: pd.DataFrame) -> pd.Series:
    divs = df.get("dividends_paid", pd.Series(0, index=df.index))
    buybacks = df.get("share_repurchases", pd.Series(0, index=df.index))
    mv = df.get("total_mv", pd.Series(dtype="float64"))

    if mv.empty:
        return pd.Series(pd.NA, index=df.index, dtype="float64")

    mv_safe = mv.replace(0, np.nan)
    # Both are negative in cashflow (outflows), take absolute values
    total_return = divs.abs().fillna(0) + buybacks.abs().fillna(0)
    return (total_return / mv_safe * 100).round(2)
