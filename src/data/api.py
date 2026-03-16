"""
数据查询接口 (只读)

提供行情、财报、预计算因子的统一查询入口。
所有上层模块 (screener, agent, backtest) 通过此模块读取数据。

CLI:
    python -m src.engine.launcher data status    # 查看数据覆盖状态

Python:
    from src.data import api
    api.get_stock_list()                                          # 股票列表
    api.get_daily('2024-01-01', '2024-06-30', ts_code='601288.SH')  # 不复权日线
    api.get_daily_adjusted('2024-01-01', '2024-06-30', adjust='qfq') # 前复权日线
    api.get_daily_adjusted('2024-01-01', '2024-06-30', adjust='hfq') # 后复权日线
    api.get_daily_indicator('2024-01-01', '2024-06-30')           # PE/PB/DV/市值
    api.get_income('601288.SH')                                   # 利润表
    api.get_factors('2024-01-01', '2024-06-30')                   # 截面因子
    api.get_ts_factors()                                          # 时序因子
    api.get_data_status()                                         # 数据状态字典
"""
from typing import List, Optional
import functools
import pandas as pd
from . import storage


# ==================== 缓存层 ====================

@functools.lru_cache(maxsize=2)
def _load_stock_list() -> pd.DataFrame:
    """缓存加载股票列表（会话内复用，避免重复读磁盘）"""
    return storage.load_one('basic', '', 'stock_list')


@functools.lru_cache(maxsize=1)
def _load_trade_calendar() -> pd.DataFrame:
    """缓存加载交易日历"""
    return storage.load_one('basic', '', 'trade_calendar')


# ==================== 股票列表 ====================

def get_stock_list(only_active: bool = True) -> pd.DataFrame:
    """获取股票列表"""
    df = _load_stock_list()
    if df.empty:
        return df
    if only_active:
        df = df[df['list_status'] == 'L']
    return pd.DataFrame(df)


def get_stock_codes(only_active: bool = True) -> List[str]:
    """获取股票代码列表"""
    df = get_stock_list(only_active)
    return df['ts_code'].tolist() if not df.empty else []


def get_stock_name(ts_code: str) -> Optional[str]:
    """获取股票名称"""
    df = get_stock_list(only_active=False)
    if df.empty:
        return None
    match = df[df['ts_code'] == ts_code]
    return match['name'].iloc[0] if not match.empty else None


# ==================== 交易日历 ====================

def get_trade_calendar(
    start_date: str,
    end_date: str,
    only_open: bool = True,
) -> pd.DataFrame:
    """获取交易日历"""
    df = _load_trade_calendar()
    if df.empty:
        return df
    df = df[(df['cal_date'] >= start_date) & (df['cal_date'] <= end_date)]
    if only_open:
        df = df[df['is_open'] == 1]
    return df.sort_values('cal_date').reset_index(drop=True)


def get_trade_dates(start_date: str, end_date: str) -> List[str]:
    """获取交易日列表"""
    df = get_trade_calendar(start_date, end_date, only_open=True)
    return df['cal_date'].tolist() if not df.empty else []


# ==================== 日线行情 ====================

def get_daily(
    start_date: str,
    end_date: str,
    ts_code: Optional[str] = None,
    columns: Optional[List[str]] = None,
) -> pd.DataFrame:
    """获取日线行情"""
    months = storage.get_months_between(start_date, end_date)
    filters = [('ts_code', '==', ts_code)] if ts_code else None
    df = storage.load('daily', 'raw', months, columns, filters=filters)
    if df.empty:
        return df
    df = df[(df['trade_date'] >= start_date) & (df['trade_date'] <= end_date)]
    if ts_code and 'ts_code' in df.columns:
        df = df[df['ts_code'] == ts_code]
    return df.sort_values(['ts_code', 'trade_date']).reset_index(drop=True)


def get_daily_adjusted(
    start_date: str,
    end_date: str,
    ts_code: Optional[str] = None,
    adjust: str = 'qfq',
) -> pd.DataFrame:
    """获取复权日线行情

    自动合并 raw + adj_factor，计算复权价格。

    Args:
        start_date: 开始日期 YYYY-MM-DD
        end_date: 结束日期 YYYY-MM-DD
        ts_code: 股票代码，None 返回全市场
        adjust: 复权方式
            'qfq' - 前复权 (默认，以最新价为基准向前调整)
            'hfq' - 后复权 (以上市首日价为基准向后调整)

    Returns:
        DataFrame 包含: ts_code, trade_date, open, high, low, close, volume, amount
        其中 open/high/low/close 已按复权方式调整
    """
    months = storage.get_months_between(start_date, end_date)
    filters = [('ts_code', '==', ts_code)] if ts_code else None
    raw = storage.load('daily', 'raw', months, filters=filters)
    adj = storage.load('daily', 'adj_factor', months, ['ts_code', 'trade_date', 'adj_factor'], filters=filters)
    if raw.empty or adj.empty:
        return raw

    raw = raw[(raw['trade_date'] >= start_date) & (raw['trade_date'] <= end_date)]
    adj = adj[(adj['trade_date'] >= start_date) & (adj['trade_date'] <= end_date)]
    if ts_code and 'ts_code' in raw.columns:
        raw = raw[raw['ts_code'] == ts_code]
        adj = adj[adj['ts_code'] == ts_code]

    df = raw.merge(adj, on=['ts_code', 'trade_date'], how='left')

    price_cols = ['open', 'high', 'low', 'close']
    if adjust == 'hfq':
        # 后复权: price * adj_factor
        for col in price_cols:
            df[col] = (df[col] * df['adj_factor']).round(4)
    else:
        # 前复权: price * adj_factor / latest_adj_factor_per_stock
        latest_adj = df.groupby('ts_code')['adj_factor'].transform('last')
        for col in price_cols:
            df[col] = (df[col] * df['adj_factor'] / latest_adj).round(4)

    df = df.drop(columns=['adj_factor'])
    return df.sort_values(['ts_code', 'trade_date']).reset_index(drop=True)


def get_daily_indicator(
    start_date: str,
    end_date: str,
    ts_code: Optional[str] = None,
    columns: Optional[List[str]] = None,
) -> pd.DataFrame:
    """获取每日指标（PE/PB/换手率/市值等）"""
    months = storage.get_months_between(start_date, end_date)
    filters = [('ts_code', '==', ts_code)] if ts_code else None
    df = storage.load('daily', 'indicator', months, columns, filters=filters)
    if df.empty:
        return df
    df = df[(df['trade_date'] >= start_date) & (df['trade_date'] <= end_date)]
    if ts_code and 'ts_code' in df.columns:
        df = df[df['ts_code'] == ts_code]
    return df.sort_values(['ts_code', 'trade_date']).reset_index(drop=True)


# ==================== 基本面数据 ====================

def get_balancesheet(
    ts_code: str,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    获取资产负债表

    Args:
        ts_code: 股票代码
        end_date: 截止报告期，如 '2024-06-30'，None 则返回所有
    """
    df = storage.load_financial('balancesheet', partitions=[ts_code])
    if df.empty:
        return df
    if end_date:
        df = df[df['end_date'] <= end_date]
    return df.sort_values('end_date').reset_index(drop=True)


def get_income(
    ts_code: str,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """获取利润表"""
    df = storage.load_financial('income', partitions=[ts_code])
    if df.empty:
        return df
    if end_date:
        df = df[df['end_date'] <= end_date]
    return df.sort_values('end_date').reset_index(drop=True)


def get_cashflow(
    ts_code: str,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """获取现金流量表"""
    df = storage.load_financial('cashflow', partitions=[ts_code])
    if df.empty:
        return df
    if end_date:
        df = df[df['end_date'] <= end_date]
    return df.sort_values('end_date').reset_index(drop=True)


def get_dividend(ts_code: str) -> pd.DataFrame:
    """获取分红数据"""
    df = storage.load_financial('dividend', partitions=[ts_code])
    if df.empty:
        return df
    return df.sort_values('end_date').reset_index(drop=True)


def get_financial_indicator(
    ts_code: str,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """获取财务指标（ROE、毛利率等）"""
    df = storage.load_financial('fina_indicator', partitions=[ts_code])
    if df.empty:
        return df
    if end_date:
        df = df[df['end_date'] <= end_date]
    return df.sort_values('end_date').reset_index(drop=True)


def get_disclosure_dates(ts_code: str) -> pd.DataFrame:
    """获取财报披露日期（disclosure_date 按报告期分区，需加载全部后按股票过滤）"""
    df = storage.load_financial('disclosure_date')
    if df.empty:
        return df
    if 'ts_code' in df.columns:
        df = df[df['ts_code'] == ts_code]
    return df.sort_values('end_date').reset_index(drop=True)


def get_top10_holders(
    ts_code: str,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """获取前十大股东"""
    df = storage.load_financial('top10_holders', partitions=[ts_code])
    if df.empty:
        return df
    if end_date:
        df = df[df['end_date'] <= end_date]
    return df.sort_values(['end_date', 'hold_ratio'], ascending=[True, False]).reset_index(drop=True)


def get_top10_floatholders(
    ts_code: str,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """获取前十大流通股东"""
    df = storage.load_financial('top10_floatholders', partitions=[ts_code])
    if df.empty:
        return df
    if end_date and 'end_date' in df.columns:
        df = df[df['end_date'] <= end_date]
    return df.reset_index(drop=True)


def get_pledge_stat(
    ts_code: str,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """获取股权质押统计"""
    df = storage.load_financial('pledge_stat', partitions=[ts_code])
    if df.empty:
        return df
    if end_date:
        df = df[df['end_date'] <= end_date]
    return df.sort_values('end_date').reset_index(drop=True)


def get_pledge_detail(ts_code: str) -> pd.DataFrame:
    """获取股权质押明细"""
    df = storage.load_financial('pledge_detail', partitions=[ts_code])
    if df.empty:
        return df
    return df.reset_index(drop=True)


def get_fina_audit(
    ts_code: str,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """获取审计意见"""
    df = storage.load_financial('fina_audit', partitions=[ts_code])
    if df.empty:
        return df
    if end_date:
        df = df[df['end_date'] <= end_date]
    return df.sort_values('end_date').reset_index(drop=True)


def get_fina_mainbz(
    ts_code: str,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """获取主营业务构成"""
    df = storage.load_financial('fina_mainbz', partitions=[ts_code])
    if df.empty:
        return df
    if end_date:
        df = df[df['end_date'] <= end_date]
    return df.sort_values('end_date').reset_index(drop=True)


def get_stk_holdernumber(
    ts_code: str,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """获取股东人数"""
    df = storage.load_financial('stk_holdernumber', partitions=[ts_code])
    if df.empty:
        return df
    if end_date:
        df = df[df['end_date'] <= end_date]
    return df.sort_values('end_date').reset_index(drop=True)


def get_stk_holdertrade(ts_code: str) -> pd.DataFrame:
    """获取股东增减持"""
    df = storage.load_financial('stk_holdertrade', partitions=[ts_code])
    if df.empty:
        return df
    return df.reset_index(drop=True)


def get_share_float(ts_code: str) -> pd.DataFrame:
    """获取限售解禁"""
    df = storage.load_financial('share_float', partitions=[ts_code])
    if df.empty:
        return df
    return df.reset_index(drop=True)


def get_repurchase(ts_code: str) -> pd.DataFrame:
    """获取股票回购"""
    df = storage.load_financial('repurchase', partitions=[ts_code])
    if df.empty:
        return df
    return df.reset_index(drop=True)


# ==================== 预计算因子 ====================

def get_factors(
    start_date: str,
    end_date: str,
    ts_code: Optional[str] = None,
    columns: Optional[List[str]] = None,
) -> pd.DataFrame:
    """获取预计算的因子数据"""
    from .factor_store import get_factor_data
    return get_factor_data(start_date, end_date, ts_code, columns)


def get_daily_indicator_with_factors(
    start_date: str,
    end_date: str,
    ts_code: Optional[str] = None,
) -> pd.DataFrame:
    """获取每日指标 + 预计算因子 (合并)"""
    from .factor_store import get_indicator_with_factors
    return get_indicator_with_factors(start_date, end_date, ts_code)


def get_ts_factors(
    ts_code=None,
    columns: Optional[List[str]] = None,
) -> pd.DataFrame:
    """获取预计算的时序因子 (每股票一行静态属性)"""
    from .factor_store import get_ts_factor_data
    return get_ts_factor_data(ts_code, columns)


# ==================== 元信息 ====================

def get_latest_date(category: str = 'daily', sub: str = 'raw') -> Optional[str]:
    """获取本地数据最新日期"""
    return storage.get_latest_date(category, sub)


def get_index_daily(
    ts_code: str,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """
    获取指数日线行情 (直接调用 tushare API，不走本地存储)

    Args:
        ts_code: 指数代码，如 '000300.SH' (沪深300), '000905.SH' (中证500)
        start_date: 起始日期 YYYY-MM-DD
        end_date: 结束日期 YYYY-MM-DD

    Returns:
        DataFrame [ts_code, trade_date, close, open, high, low, pct_chg]
    """
    from .tushare.provider import TushareProvider
    provider = TushareProvider()
    return provider.fetch_index_daily(ts_code, start_date, end_date)


def get_data_status() -> dict:
    """获取本地数据状态摘要"""
    status = {}

    # 日线数据
    for sub in ['raw', 'indicator', 'adj_factor', 'factors']:
        partitions = storage.list_partitions('daily', sub)
        latest = storage.get_latest_date('daily', sub) if partitions else None
        status[f'daily_{sub}'] = {
            'partitions': len(partitions),
            'latest_date': latest,
            'months': f"{partitions[0]}~{partitions[-1]}" if partitions else None,
        }

    # 时序因子
    ts_df = get_ts_factors()
    ts_factor_cols = [c for c in ts_df.columns if c != 'ts_code'] if not ts_df.empty else []
    status['ts_factors'] = {
        'stocks': len(ts_df),
        'factors': len(ts_factor_cols),
        'factor_ids': ts_factor_cols,
    }

    # 财报数据
    for sub in ['balancesheet', 'income', 'cashflow', 'fina_indicator',
                'dividend', 'top10_holders', 'top10_floatholders',
                'pledge_stat', 'pledge_detail', 'fina_audit', 'fina_mainbz',
                'stk_holdernumber', 'stk_holdertrade', 'share_float', 'repurchase',
                'disclosure_date']:
        partitions = storage.list_financial_partitions(sub)
        status[f'financial_{sub}'] = {
            'count': len(partitions),
        }

    # 基础数据
    stock_list = get_stock_list(only_active=True)
    status['stock_list'] = {'active_count': len(stock_list)}

    return status
