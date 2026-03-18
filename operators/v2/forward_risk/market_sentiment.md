---
id: market_sentiment
name: 市场情绪与资金面分析
tags: [risk, market]
data_needed: []
outputs:
  - field: sentiment_level
    type: enum [极度乐观, 偏乐观, 中性, 偏悲观, 极度悲观]
  - field: fund_flow_trend
    type: enum [持续流入, 流入转流出, 中性, 流出转流入, 持续流出]
  - field: market_position
    type: text
  - field: sentiment_reasoning
    type: text
---

## 分析目标

评估该股票当前的市场情绪和资金面状况，判断价格是否受到情绪过度影响。

## 分析框架

### 1. 获取市场数据

调用以下工具获取实时数据：
- `query_market_context(info_type="fund_flow")` — 近期主力资金流向
- `query_market_context(info_type="market_index")` — 大盘走势
- `query_market_context(info_type="industry_overview")` — 行业板块表现

### 2. 资金面分析

从主力资金流数据判断：
- 近 5 日主力净流入趋势（持续流入/流出/转折）
- 近 20 日累计主力净流入（正=资金看好，负=资金撤离）
- 超大单 vs 大单 vs 中小单的方向是否一致

### 3. 大盘环境

从沪深300走势判断：
- 近 5 日/20 日大盘涨跌
- 大盘处于什么位置（上升趋势/震荡/下跌趋势）
- 个股走势和大盘是否同步（beta 高低）

### 4. 行业热度

- 所属行业今日涨跌幅在全市场排名
- 行业资金净流入/流出
- 行业内上涨 vs 下跌家数

### 5. 综合判断

市场情绪对投资决策的影响：
- 极度悲观 + 基本面好 → 可能是买入机会
- 极度乐观 + 估值偏高 → 谨慎，可能透支了未来
- 中性 → 回归基本面分析

## 注意

- 本算子依赖实时增强数据，回测模式下工具返回空数据，自动降级
- 情绪分析是辅助维度，不应改变基本面判断的核心结论
- 资金面是短期信号，和长期价值投资逻辑可能矛盾——需明确标注时间维度
