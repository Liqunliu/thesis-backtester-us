"""
数据提供者抽象层

定义 DataProvider 协议，解耦数据获取与具体数据源。
不同数据源 (Tushare, AKShare, Wind, CSV) 只需实现此协议即可接入。

用法:
    from src.data.provider import get_provider
    provider = get_provider()           # 默认 tushare
    provider = get_provider("tushare")  # 指定

环境变量:
    DATA_PROVIDER   默认数据源名称 (默认 "tushare")
    TUSHARE_TOKEN   Tushare Pro API token
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Protocol, runtime_checkable

import pandas as pd

logger = logging.getLogger(__name__)


# ==================== 协议定义 ====================

@runtime_checkable
class DataProvider(Protocol):
    """数据提供者协议

    所有方法返回标准化 DataFrame，列名使用统一约定:
    - 日期列: trade_date, ann_date, end_date (格式 YYYY-MM-DD)
    - 代码列: ts_code (格式 600000.SH / 000001.SZ)
    """

    @property
    def name(self) -> str:
        """提供者名称"""
        ...

    # ---------- 基础数据 ----------

    def fetch_stock_list(self) -> pd.DataFrame:
        """股票列表

        必须包含: ts_code, name, industry, list_status, list_date
        """
        ...

    def fetch_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        """交易日历

        必须包含: cal_date, is_open
        """
        ...

    # ---------- 日线数据 (批量) ----------

    def fetch_daily_bulk(self, trade_date: str) -> pd.DataFrame:
        """批量获取某一交易日全市场日线行情

        Args:
            trade_date: 交易日 YYYY-MM-DD

        Returns:
            必须包含: ts_code, trade_date, open, high, low, close, volume, amount
        """
        ...

    def fetch_adj_factor_bulk(self, trade_date: str) -> pd.DataFrame:
        """批量获取某一交易日全市场复权因子

        Args:
            trade_date: 交易日 YYYY-MM-DD

        Returns:
            必须包含: ts_code, trade_date, adj_factor
        """
        ...

    def fetch_daily_indicator_bulk(self, trade_date: str) -> pd.DataFrame:
        """批量获取某一交易日全市场估值指标

        Args:
            trade_date: 交易日 YYYY-MM-DD

        Returns:
            必须包含: ts_code, trade_date, pe_ttm, pb, dv_ttm, total_mv
        """
        ...

    # ---------- 财报数据 (按股票) ----------

    def fetch_balancesheet(self, ts_code: str) -> pd.DataFrame:
        """资产负债表 (全历史)

        必须包含: ts_code, ann_date, end_date, report_type
        """
        ...

    def fetch_income(self, ts_code: str) -> pd.DataFrame:
        """利润表 (全历史)"""
        ...

    def fetch_cashflow(self, ts_code: str) -> pd.DataFrame:
        """现金流量表 (全历史)"""
        ...

    def fetch_financial_indicator(self, ts_code: str) -> pd.DataFrame:
        """财务指标 (ROE/毛利率等)"""
        ...

    def fetch_dividend(self, ts_code: str) -> pd.DataFrame:
        """分红数据"""
        ...

    def fetch_top10_holders(self, ts_code: str) -> pd.DataFrame:
        """前十大股东"""
        ...

    def fetch_top10_floatholders(self, ts_code: str) -> pd.DataFrame:
        """前十大流通股东"""
        ...

    def fetch_pledge_stat(self, ts_code: str) -> pd.DataFrame:
        """股权质押统计"""
        ...

    def fetch_pledge_detail(self, ts_code: str) -> pd.DataFrame:
        """股权质押明细"""
        ...

    def fetch_fina_audit(self, ts_code: str) -> pd.DataFrame:
        """审计意见"""
        ...

    def fetch_fina_mainbz(self, ts_code: str) -> pd.DataFrame:
        """主营业务构成"""
        ...

    def fetch_stk_holdernumber(self, ts_code: str) -> pd.DataFrame:
        """股东人数"""
        ...

    def fetch_stk_holdertrade(self, ts_code: str) -> pd.DataFrame:
        """股东增减持"""
        ...

    def fetch_share_float(self, ts_code: str) -> pd.DataFrame:
        """限售解禁"""
        ...

    def fetch_repurchase(self, ts_code: str) -> pd.DataFrame:
        """股票回购"""
        ...

    def fetch_disclosure_date(self, end_date: Optional[str] = None) -> pd.DataFrame:
        """财报披露日期 (全市场)"""
        ...

    # ---------- 财报数据 (按报告期截面, 全市场) ----------

    def fetch_income_by_period(self, period: str) -> pd.DataFrame:
        """利润表 — 按报告期截面获取全市场

        Args:
            period: 报告期 YYYY-MM-DD (如 2024-12-31)
        """
        ...

    def fetch_balancesheet_by_period(self, period: str) -> pd.DataFrame:
        """资产负债表 — 按报告期截面获取全市场"""
        ...

    def fetch_cashflow_by_period(self, period: str) -> pd.DataFrame:
        """现金流量表 — 按报告期截面获取全市场"""
        ...

    def fetch_fina_indicator_by_period(self, period: str) -> pd.DataFrame:
        """财务指标 — 按报告期截面获取全市场"""
        ...


# ==================== 提供者注册表 ====================

_registry: Dict[str, DataProvider] = {}
_default_name: str = "tushare"


def register(name: str, provider: DataProvider) -> None:
    """注册数据提供者"""
    _registry[name] = provider
    logger.info(f"数据提供者已注册: {name}")


def get_provider(name: str = None) -> DataProvider:
    """获取数据提供者

    Args:
        name: 提供者名称，None 使用默认

    Returns:
        DataProvider 实例
    """
    target = name or _default_name

    if target not in _registry:
        # 延迟加载: 首次访问时自动注册
        if target == "tushare":
            from .tushare import TushareProvider
            register("tushare", TushareProvider())
        else:
            raise ValueError(f"未知数据提供者: {target}，已注册: {list(_registry.keys())}")

    return _registry[target]


def set_default(name: str) -> None:
    """设置默认数据提供者"""
    global _default_name
    _default_name = name


def list_providers() -> List[str]:
    """列出所有已注册的提供者"""
    return list(_registry.keys())
