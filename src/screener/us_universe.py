"""
US stock universe management.

Provides S&P 500 constituent list for screening. Supports both
static CSV and dynamic Wikipedia fetch.
"""
import logging
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

_SP500_CSV = Path(__file__).parent.parent / "data" / "bloomberg" / "sp500_constituents.csv"


def get_sp500(csv_path: Optional[Path] = None) -> pd.DataFrame:
    """Load S&P 500 constituent list.

    Returns DataFrame with: ts_code, name, industry, list_status, list_date
    """
    path = csv_path or _SP500_CSV
    if path.exists():
        return pd.read_csv(path)

    # Fetch from Wikipedia
    try:
        logger.info("Fetching S&P 500 list from Wikipedia...")
        tables = pd.read_html(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        )
        df = tables[0][["Symbol", "Security", "GICS Sector", "Date added"]].copy()
        df.columns = ["ts_code", "name", "industry", "list_date"]
        df["ts_code"] = df["ts_code"].str.replace(".", "-", regex=False)
        df["list_status"] = "L"
        df["list_date"] = df["list_date"].fillna("")

        # Cache for next time
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)
        logger.info("Cached %d S&P 500 constituents to %s", len(df), path)

        return df
    except Exception as e:
        logger.warning("Failed to fetch S&P 500 from Wikipedia: %s", e)
        return pd.DataFrame({
            "ts_code": ["AAPL", "MSFT", "GOOGL", "AMZN", "META",
                         "NVDA", "BRK-B", "UNH", "JNJ", "V"],
            "name": ["Apple", "Microsoft", "Alphabet", "Amazon", "Meta",
                      "NVIDIA", "Berkshire", "UnitedHealth", "J&J", "Visa"],
            "industry": ["Information Technology"] * 6 + ["Financials"] +
                        ["Health Care"] * 2 + ["Financials"],
            "list_status": ["L"] * 10,
            "list_date": [""] * 10,
        })
