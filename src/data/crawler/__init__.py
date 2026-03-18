"""
免费数据提供者 — 基于 AKShare + 公开数据爬取

用于实时单股分析（live-analyze），不依赖 Tushare 付费 API。
实现 DataProvider 协议中按股票获取的方法。
批量方法（按交易日全市场）不实现——回测场景应使用 TushareProvider。

数据来源:
  - AKShare 东方财富接口: 三张财报、日线行情、分红、十大股东、财务指标
  - 数据自动做字段映射，对外暴露与 TushareProvider 一致的列名
"""
from .provider import CrawlerProvider

__all__ = ['CrawlerProvider']
