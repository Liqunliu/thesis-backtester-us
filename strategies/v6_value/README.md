# V6 价值投资分析

基于 [investTemplate](https://github.com/sunheyi6/investTemplate) 框架演进的策略实例。

## 投资模版

本策略的分析框架源自 **个股分析标准模版**，一套面向 A 股/港股的深度价值分析体系。

- 原始仓库：https://github.com/sunheyi6/investTemplate
- 许可证：Apache 2.0

V6 架构采用算子驱动（operators/），由 `strategy.yaml` 单文件定义完整策略。

## 框架概要

**四流派投资体系**：纯硬收息 / 价值发现 / 烟蒂股 / 关联方资源

**6 章分析流程**：

| 章节 | 内容 | 核心算子 |
|------|------|---------|
| 1 | 数据核查与快速筛选 | data_source_grading, geopolitical_exclusion, quick_screen_5min |
| 2 | 基本面分析 | soe_identification, stream_classification, debt_structure, cycle_analysis, management_integrity |
| 3 | 现金流与盈利质量 | cash_trend_5y, performance_restoration, owner_earnings |
| 4 | 估值与安全边际 | pe_trap_detection, valuation_fcf, valuation_dividend, safety_margin |
| 5 | 压力测试与特殊分析 | stress_test, cigar_butt, light_asset_model |
| 6 | 投资决策与持仓管理 | apple_trading_model, valuation_repair, position_management |

## 龟级筛选

| 级别 | PE | PB | 股息率 |
|------|-----|------|--------|
| 金龟 | ≤ 8 | ≤ 0.8 | ≥ 7% |
| 银龟 | ≤ 10 | ≤ 1.0 | ≥ 5% |
| 铜龟 | ≤ 12 | ≤ 1.2 | ≥ 4% |

## 用法

```bash
# 筛选
python -m src.engine.launcher strategies/v6_value/strategy.yaml screen 2024-06-30

# Agent 分析（需要 LLM_API_KEY + LLM_BASE_URL）
python -m src.engine.launcher strategies/v6_value/strategy.yaml agent-analyze 601288.SH 2024-06-30
```
