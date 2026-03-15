# 盲测规模扩展与框架优化计划

## 一、当前状态（v6）

| 维度 | 当前 | 目标 |
|------|------|------|
| 样本量 | 60（每截面5只） | 300-600（每截面25-50只） |
| 截面频率 | 半年（12个截面） | 季度（24个截面），未来可月度 |
| 验证指标 | 仅6个月前向收益 | 1m/3m/6m/12m + 最大回撤（已支持） |
| 框架 | V6（21算子，6章节） | 支持多框架对比 |
| 数据维度 | 15+ 类（含治理风险） | +宏观环境数据 |
| Agent 工具 | 16种数据查询 | 已实现 |

## 二、扩展方案

### Phase 1：全量600样本

已有12个半年截面 × 每截面50只 = 600样本的筛选和前向收益数据。

**工作量**：
1. 补齐财务数据：约86只新股票需要下载（~30分钟）
2. 运行 Agent 分析：`batch_backtest.py` 协调（并行运行）
3. 前瞻收益采集：`outcome_collector.py`（已支持 1m/3m/6m/12m + 回撤）
4. 质量评分：`quality_scorer.py` 5维评分
5. 重新生成验证报告

**价值**：
- 样本从60→600，统计显著性大幅提升
- 可以做更细粒度的归因分析（按行业/市值/龟级分组）

### Phase 2：季度截面

在半年截面之间插入季度截面（3月31日、9月30日）。

**需要做的**：
1. 对每个季度末运行量化筛选（`quick_filter`，通过 Launcher）
2. 计算前向收益（`outcome_collector`）
3. 运行 Agent 盲测分析
4. 质量评分 + 跨截面对比

**新增截面**：12个 → 累计约1200样本

### Phase 3：灵活截面频率

支持任意截面频率：
- 月度：每月末跑一次（72个截面 × 50 = 3600样本）
- 事件驱动：在重大事件节点增加截面

`crosssection.py` 的 `plan` 模式已支持自定义日期列表。

## 三、框架灵活化

### 3.1 v6 已实现的配置化

v6 通过 `strategy.yaml` 一站式配置已解决大部分硬编码问题：

```yaml
# strategy.yaml 完整结构
meta:
  name: V6 价值投资分析
  version: "6.0"

screening:           # 量化筛选（声明式）
  exclude: [...]
  filters: [...]
  scoring: {factors: [...], tiers: [...]}

framework:           # 分析框架（算子驱动）
  analyst_role: ...
  chapters: [...]    # 章节 + 算子组合 + 依赖关系
  synthesis_fields: [...]

backtest:            # 回测参数
  cross_section_interval: 6m
  forward_periods: [{months: 1}, {months: 3}, {months: 6}, {months: 12}]

llm:                 # LLM 配置
  model: gpt-4o
  temperature: 0.1
  max_tokens: 8192
```

### 3.2 创建新策略

创建新的投资策略只需：
1. 创建 `strategies/<name>/strategy.yaml`
2. 选择和组合已有算子（或创建新算子）
3. 运行筛选和分析

无需修改任何引擎代码。

### 3.3 多验证指标

`outcome_collector.py` 已支持多周期收益：

| 指标 | 用途 |
|------|------|
| fwd_1m | 短期信号有效性 |
| fwd_3m | 中短期 |
| fwd_6m | 核心指标 |
| fwd_12m | 长期价值验证 |
| max_drawdown_6m | 风险控制能力 |
| max_gain_6m | 最大涨幅 |
| volatility_6m | 波动率 |
| actual_dividends | 分红准确度验证 |

`quality_scorer.py` 提供 5 维质量评分（方向40% + 推荐25% + 风险15% + 安全边际10% + 分红10%），可评分条件为 `data_available_months >= 3`。

## 四、优先级排序

| 任务 | 优先级 | 依赖 | 预期效果 |
|------|--------|------|---------|
| blind_batch.py 协调器 | P0 | Agent + Backtest | 打通端到端自动化 |
| Phase 1: 全量600样本 | P0 | blind_batch.py | 统计说服力×10 |
| Tracker 集成 | P1 | runtime.py | 分析运行可追溯 |
| Phase 2: 季度截面 | P1 | Phase 1 完成 | 样本量→1200 |
| 宏观环境算子 | P1 | 新算子 | 解决周期反转盲区 |
| 多策略对比 | P2 | 新策略 yaml | 验证引擎通用性 |
| Phase 3: 灵活截面 | P2 | Phase 2 完成 | 完整产品能力 |

## 五、待实现模块

### blind_batch.py（P0）

批量盲测协调器，连通 Agent 分析和回测评分：

```
输入: strategy.yaml + 截面日期列表
  │
  ▼ 对每个截面日期
  │   1. quick_filter 筛选 → 候选列表
  │   2. runtime.py 对每个候选运行 Agent 盲测分析
  │   3. outcome_collector 采集前瞻收益
  │   4. quality_scorer 5维评分
  │
  ▼ 汇总
  │   crosssection 跨截面对比
  │
  ▼ 输出验证报告
```

### Tracker 集成（P1）

`src/engine/tracker.py`（SQLite，已实现 235 行）需要与 `runtime.py` 集成：
- `runtime.py` 完成分析后调用 `tracker.record_analysis()`
- 保存 run_id, ts_code, cutoff_date, 各章节输出, 综合评分
- 支持查询历史分析结果

---

*文档版本: v2.0 (v6 架构)*
*更新日期: 2026-03-16*
