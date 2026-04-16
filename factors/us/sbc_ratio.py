"""
Stock-Based Compensation Ratio (SBC/Net Income)

US tech companies often have SBC > 20% of net income, making GAAP
earnings overstate real cash earnings. This ratio flags SBC-heavy companies.

Thresholds:
  < 10%: Minimal concern
  10-20%: Moderate — consider SBC-adjusted earnings
  > 20%: Material — must use SBC-adjusted OE in QY analysis
"""
import pandas as pd
import numpy as np

META = {
    "id": "sbc_ratio",
    "name": "SBC/Net Income (%)",
    "description": "Stock-Based Compensation as % of Net Income",
    "data_needed": ["cashflow", "income"],
    "type": "time_series",
}


def compute(df: pd.DataFrame) -> pd.Series:
    sbc = df.get("sbc", pd.Series(dtype="float64"))
    ni = df.get("net_income", pd.Series(dtype="float64"))
    if sbc.empty or ni.empty:
        return pd.Series(pd.NA, index=df.index, dtype="float64")
    ni_safe = ni.replace(0, np.nan)
    return (sbc.abs() / ni_safe.abs() * 100).round(2)
