"""
Tushare 数据提供者

将 tushare API 包装为 DataProvider 协议实现。
"""
from .provider import TushareProvider

__all__ = ['TushareProvider']
