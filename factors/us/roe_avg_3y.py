"""
3-Year Average ROE

Smooths cyclical noise. Used in us-qy screening (weight 25%)
and moat quantitative gate (D2-2: 5yr avg ROE > 15% = strong moat evidence).
"""
import pandas as pd
import numpy as np

META = {
    "id": "roe_avg_3y",
    "name": "ROE 3Y Avg (%)",
    "description": "3-year average return on equity",
    "data_needed": ["fina_indicator"],
    "type": "time_series",
}


def compute(df: pd.DataFrame) -> pd.Series:
    roe = df.get("roe", pd.Series(dtype="float64"))
    if roe.empty:
        return pd.Series(pd.NA, index=df.index, dtype="float64")
    return roe.rolling(window=3, min_periods=2).mean().round(2)
