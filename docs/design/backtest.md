# 回测层设计

## 定位

验证 Agent 分析质量的闭环系统。通过批量截面回测 → 前瞻收益采集 → 多维质量评分，量化评估投资框架和 Agent 的分析能力。

核心问题：**Agent 的分析结论在事后看来有多准确？**

## 回测体系全景

```
┌─────────────────────────────────────────────────────┐
│                 Backtest Pipeline                     │
│                                                      │
│  ┌──────────┐    ┌──────────┐    ┌────────────────┐ │
│  │  Batch   │───→│ Outcome  │───→│   Quality      │ │
│  │ Backtest │    │Collector │    │   Scorer       │ │
│  │ 截面回测  │    │ 收益采集  │    │  5维质量评分    │ │
│  └──────────┘    └──────────┘    └────────────────┘ │
│       │                               │              │
│       │                               ▼              │
│       │                        ┌──────────────┐      │
│       │                        │ Cross-Section│      │
│       │                        │  Comparison  │      │
│       │                        │  跨截面对比    │      │
│       └────────────────────────┴──────────────┘      │
└─────────────────────────────────────────────────────┘
```

## 模块详解

### 1. 批量截面回测 (batch_backtest.py)

#### 职责

在多个历史截面日期运行量化筛选，采集前瞻收益，评估筛选策略的历史表现。支持通过 StrategyConfig 配置筛选条件。

#### 工作流

```
生成截面日期序列（默认半年一次，可配置）
    │
    ▼ 对每个日期
    │   1. screen_at_date(cutoff_date, config) → 候选列表
    │   2. collect_forward_outcome(ts_code, cutoff_date) → 每只候选的收益
    │   3. 合并为 CrossSectionResult
    │
    ▼ 汇总统计
    │
    ▼ 输出报告
```

#### 调用方式

```bash
python -m src.backtest.batch_backtest --top 50
python -m src.backtest.batch_backtest --dates 2023-06-30,2023-12-31,2024-06-30
python -m src.backtest.batch_backtest --strategy strategies/v6_value/strategy.yaml
```

### 2. 前瞻收益采集 (outcome_collector.py)

#### 职责

采集分析截止日期之后的实际市场表现，作为质量评估的 ground truth。

#### ForwardOutcome 数据结构

```python
@dataclass
class ForwardOutcome:
    cutoff_price: float          # 基准价格
    return_1m: float             # 1个月收益
    return_3m: float             # 3个月收益
    return_6m: float             # 6个月收益
    return_12m: float            # 12个月收益
    max_drawdown_6m: float       # 最大回撤
    max_gain_6m: float           # 最大涨幅
    volatility_6m: float         # 波动率
    actual_dividends: float      # 12个月内每股分红
    data_available_months: int   # 可用数据月数
    collection_date: str
```

前瞻周期从 `strategy.yaml` 的 `backtest.forward_periods` 读取。

### 3. 质量评分 (quality_scorer.py)

#### 5 维评分体系

| 维度 | 权重 | 评估内容 |
|------|------|---------|
| 方向判断 | 40% | AI 看多/空 vs 实际涨跌 |
| 推荐质量 | 25% | 买入→赚钱? 回避→跌了? |
| 风险识别 | 15% | 有回撤时是否提前预警? |
| 安全边际 | 10% | 声称的安全边际是否兜住? |
| 分红准确度 | 10% | 分红预测 vs 实际分红 |

可评分条件：`data_available_months >= 3`

### 4. 跨截面对比 (crosssection.py)

三种操作模式：plan（规划截面日期）、prepare（数据准备）、compare（纵向对比分析结论变化）。

## 数据存储

### SQLite (tracker.py)

表：`analysis_runs`、`chapter_outputs`、`synthesis`、`backtest_outcomes`。

### 文件

```
{strategy_dir}/backtest/
├── agent_reports/{ts_code}_{cutoff_date}_report.md
├── agent_reports/{ts_code}_{cutoff_date}_structured.json
├── outcomes/
├── cross_section/
└── batch/
```

## 待实现

- **blind_batch.py**：批量盲测协调器，连通 Agent 分析和回测评分
- **Tracker 集成**：runtime.py 完成分析后写入 SQLite

## 设计约束

1. **无前视偏差**：分析基于 cutoff_date 之前的数据，收益采集基于之后的数据
2. **可复现**：相同样本 + 策略 + LLM → 可重现（temperature=0.1）
3. **渐进式**：可先跑少量样本，再扩展到全量
4. **配置驱动**：forward_periods 等参数从 strategy.yaml 读取
