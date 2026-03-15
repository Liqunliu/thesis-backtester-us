# Thesis Backtester — 用 AI 回测任何投资思路

> 能否在真金白银下注之前，让 AI 先验证你的投资理念是否有效？

**Thesis Backtester** 是一个开源引擎，用 LLM 驱动的盲测分析来回测*定性*投资思路。传统量化回测只能验证数值化规则（"PE<10 就买入"），而本工具验证的是真实投资者的判断：

- "这个高股息能持续吗，还是在透支未来？"
- "低 PE 是真便宜还是价值陷阱？"
- "管理层是在创造价值还是做资本运作？"
- "这个商业模式能撑过下行周期吗？"

## 核心思路

```
传统回测:     数值规则  →  历史价格  →  损益
思路回测:     投资理念  →  AI盲测分析  →  对比实际结果
```

**工作流程：**

1. **定义**：将投资理念编写为算子组合（`.md` 分析指令 + YAML 配置）
2. **筛选**：在每个历史截面，按声明式量化条件筛出候选池
3. **盲测**：只给 AI 截止日期前可得的财务数据，隐藏公司名称
4. **验证**：将 AI 的买入/回避建议与实际前向收益对比，5 维质量评分

核心洞察：**任何可以用文字描述的投资思路，都可以通过这种方式回测验证。**

## 概念验证：6 年盲测实验

我们用价值投资理念（龟级筛选：低PE + 低PB + 高股息 + FCF质量）在 **2019-2024 年 12 个半年截面、60 只股票**上做了完整验证。

### 核心结果

| 策略 | 样本 | 平均6月收益 | 胜率 |
|------|------|-----------|------|
| 纯量化筛选 | 60 | +7.5% | — |
| 量化 + AI 过滤（仅买入信号） | 9 | **+24.1%** | **67%** |
| **AI 过滤增益** | — | **+16.6 个百分点** | — |

### AI 的强项

| 能力 | 证据 |
|------|------|
| 识别高杠杆价值陷阱 | 18只地产股中16只被标记回避，均收益 -10% |
| 高确信买入信号 | 6只≥70分买入股，均收益 +41.5%，胜率 83% |
| 知道何时不出手 | 2019/2024 无买入信号 = 现金避险 |

### AI 的弱点

| 短板 | 证据 |
|------|------|
| 周期底部反转 | 鲁西化工评25分 → 实际涨73% |
| 牛市中过于保守 | 2020年回避信号平均收益 +30.6% |

### 逐年表现

| 年份 | 纯量化 | AI高确信 | 代表案例 |
|------|--------|---------|---------|
| 2019 | -9.9% | 持现金 | 无信号，规避下跌 |
| 2020 | +28.4% | -13.3% | 唯一失手：交通银行 |
| 2021 | +7.7% | +21.4% | 中国神华 +46% |
| 2022 | +0.9% | +28.7% | 中国石油 +50% |
| 2023 | +9.5% | +48.4% | 平煤/淮北/南京银行，均+48% |
| 2024 | +8.8% | 持现金 | 无信号 |

> 完整明细见 `strategies/v6_value/backtest/` 目录

## 架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Strategy Instance                        │
│  strategy.yaml (筛选 + 章节 + 算子组合 + LLM 配置，一站式定义)    │
└─────────────────────────┬───────────────────────────────────────┘
                          │ 读取配置
┌─────────────────────────▼───────────────────────────────────────┐
│                      Engine Layer (src/engine/)                  │
│  StrategyConfig · Launcher · FactorRegistry · OperatorRegistry  │
│  Tracker (SQLite)                                               │
└──────┬──────────┬──────────┬──────────┬─────────────────────────┘
       │          │          │          │
┌──────▼───┐ ┌───▼────┐ ┌──▼────┐ ┌───▼──────┐
│ Screener │ │ Agent  │ │ Back- │ │   Web    │
│ 量化筛选  │ │ 盲测分析│ │ test  │ │ Dashboard│
│          │ │        │ │ 回测  │ │ 调参界面  │
└──────┬───┘ └───┬────┘ └──┬────┘ └───┬──────┘
       │         │         │          │
┌──────▼─────────▼─────────▼──────────▼───────────────────────────┐
│                      Data Layer (src/data/)                      │
│  Provider(抽象) · Storage(Parquet) · Updater · FactorStore · API │
│  Snapshot(时点快照, 并行I/O)                                      │
└─────────────────────────────────────────────────────────────────┘
```

### 目录结构

```
src/
├── engine/        # 引擎层：StrategyConfig + Launcher + FactorRegistry + OperatorRegistry + Tracker
├── data/          # 数据层：Provider抽象 + Parquet存储 + 时间点快照(并行I/O)
│   └── tushare/   #   Tushare Provider 实现
├── agent/         # Agent层：LLM盲测分析（DAG调度 + tool_use + 16种数据查询）
├── screener/      # 筛选层：声明式量化筛选（读取预计算因子）
├── backtest/      # 回测层：批量回测 + 前瞻收益采集 + 5维质量评分
└── web/           # Web层：Streamlit 策略调参界面

factors/           # 量化因子定义（.py, 截面+时序, 自动发现）
operators/         # 定性分析算子（.md, YAML frontmatter + 分析指令, 21个）
  ├── screening/   #   数据核查、地缘政治、快速筛选、央国企识别
  ├── fundamental/ #   负债、周期、现金流、管理层、流派分类、业绩修复
  ├── valuation/   #   FCF、股息、PE陷阱、安全边际、所有者收益、估值修复
  ├── decision/    #   苹果模型、仓位管理、压力测试
  └── special/     #   烟蒂股、轻资产模式

strategies/        # 策略实例（每种投资哲学一个目录）
└── v6_value/      #   V6 价值投资（算子驱动，6章节21算子）
    └── strategy.yaml  # 一站式配置：筛选 + 章节 + 算子 + LLM
```

### 关键设计

- **算子驱动**：分析逻辑以算子（`.md` 文件）为最小单元，策略通过 YAML 组合算子，输出 Schema 从算子 frontmatter 自动生成
- **盲测**：隐藏公司名称，消除 AI 品牌偏见和记忆污染
- **三层时间边界**：数据层硬过滤（按公告日）+ Prompt 显式注入 + Agent 工具沙盒
- **策略即配置**：引擎与投资理念解耦，`strategy.yaml` 一站式定义筛选 + 分析框架 + LLM 参数
- **行业门控**：算子级前置排除，防止 FCF 估值用于银行、烟蒂股分类用于盈利企业等误用
- **Provider 抽象**：数据源通过 Protocol 解耦，更换 Tushare 只需实现接口

## 快速开始

### 环境

```bash
pip install -e .
export TUSHARE_TOKEN="your_token_here"  # 需要 Tushare Pro 账号
```

### 数据初始化

```bash
# 初始化基础数据（股票列表 + 交易日历）
python -m src.engine.launcher data init-basic

# 初始化市场数据（日线行情 + 指标 + 因子）
python -m src.engine.launcher data init-market 2020-01-01

# 日常增量更新
python -m src.engine.launcher data daily-update
```

### 使用

```bash
# 量化筛选
python -m src.engine.launcher strategies/v6_value/strategy.yaml screen 2024-06-30

# 单股 Agent 盲测分析（需要 LLM_API_KEY + LLM_BASE_URL）
python -m src.engine.launcher strategies/v6_value/strategy.yaml agent-analyze 601288.SH 2024-06-30

# 批量截面回测
python -m src.backtest.batch_backtest --strategy strategies/v6_value/strategy.yaml --top 50

# 前瞻收益采集
python -m src.backtest.outcome_collector 601288.SH 2024-06-30

# Web 调参界面
streamlit run src/web/app.py
```

### 创建自己的策略

1. 创建 `strategies/<name>/strategy.yaml`（参考 [v6_value](strategies/v6_value/strategy.yaml)）
2. 在 `screening` 部分定义量化筛选条件
3. 在 `framework.chapters` 部分组合已有算子（或在 `operators/` 创建新算子）
4. 运行筛选 → Agent 分析 → 回测验证

无需编写代码，输出 Schema 从算子 `outputs` 字段自动生成。

## 可回测的投资思路

| 思路 | 核心问题 | 状态 |
|------|---------|------|
| 龟级价值投资 | "低估值是真便宜吗？" | **已验证：+16.6pp** |
| 高股息陷阱识别 | "高息能持续吗？" | 规划中 |
| 困境反转 | "暴雷后能恢复吗？" | 规划中 |
| 周期择时 | "处于周期什么位置？" | 规划中 |
| 成长合理估值 | "高增长撑得起高PE吗？" | 规划中 |
| 央国企价值重估 | "中特估有基本面支撑吗？" | 规划中 |

新策略只需创建 `strategy.yaml` 组合算子，无需修改引擎代码。

## 与现有产品的差异

| 品类 | 代表 | 验证对象 | 本工具 |
|------|------|---------|--------|
| 量化回测 | 聚宽/米筐 | 数值化交易规则 | **定性投资判断** |
| AI选股 | 同花顺iFinD | 因子打分 | **结构化框架验证** |
| 智能投研 | 萝卜投研 | 信息检索 | **决策验证** |
| 投顾服务 | 券商投顾 | 个股推荐 | **方法论验证** |

## 文档

### 设计文档

- [整体架构](docs/design/architecture.md) — 系统分层与模块职责
- [Agent 运行时](docs/design/agent.md) — DAG 调度、Prompt 组装、工具沙盒
- [数据层](docs/design/data_layer.md) — Provider 抽象、Parquet 存储、时点快照
- [算子与因子](docs/design/operators.md) — 21 个算子清单、自动 Schema、行业门控
- [筛选层](docs/design/screener.md) — 声明式量化筛选引擎
- [回测层](docs/design/backtest.md) — 批量回测、5 维质量评分

### 规划文档

- [产品设计](docs/investment_thesis_backtester.md) — 完整产品愿景
- [数据维度路线图](docs/data_dimensions_roadmap.md) — 已实现与待扩展的数据维度
- [框架自动进化](docs/framework_evolution.md) — 错误模式分析与改进方向
- [规模扩展计划](docs/scaling_plan.md) — 从 60 样本到 600+ 的扩展路径

## 技术栈

| 组件 | 技术选型 |
|------|---------|
| 语言 | Python 3.9+ |
| 数据存储 | Parquet (zstd 压缩, 月/股票分区) |
| 数据库 | SQLite (分析追踪) |
| LLM 接口 | OpenAI 兼容 API (async, tool_use) |
| 数据源 | Tushare Pro API (Provider 抽象) |
| Web | Streamlit |

## 贡献

项目早期阶段，欢迎参与：

- **新策略实例** — 带上你自己的投资理念，创建 `strategy.yaml` 组合算子
- **新分析算子** — 在 `operators/` 添加 `.md` 文件即可
- **数据源适配** — 实现 `DataProvider` Protocol 接入港股/美股
- **多模型对比** — GPT/Gemini/DeepSeek 横评

## 许可证

Apache License 2.0

## 免责声明

本工具仅用于**投资方法论研究与验证**，不构成投资建议。历史回测结果不代表未来表现。投资有风险，决策需谨慎。

---

[English](README_en.md)
