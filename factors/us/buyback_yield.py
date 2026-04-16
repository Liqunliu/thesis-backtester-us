"""
Buyback Yield (Share Repurchases / Market Cap)

Captures capital returned via buybacks — dominant return mechanism
for US large caps (often exceeds dividend yield).
"""
import pandas as pd
import numpy as np

META = {
    "id": "buyback_yield",
    "name": "Buyback Yield (%)",
    "description": "Annual share repurchases / market cap × 100",
    "data_needed": ["cashflow", "daily_indicator"],
    "type": "time_series",
}


def compute(df: pd.DataFrame) -> pd.Series:
    buybacks = df.get("share_repurchases", pd.Series(dtype="float64"))
    mv = df.get("total_mv", pd.Series(dtype="float64"))
    if buybacks.empty or mv.empty:
        return pd.Series(pd.NA, index=df.index, dtype="float64")
    mv_safe = mv.replace(0, np.nan)
    # Buybacks are negative in cashflow (cash outflow), take absolute value
    return (buybacks.abs() / mv_safe * 100).round(2)
