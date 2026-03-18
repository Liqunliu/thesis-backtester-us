# 个股实时分析模块设计

## 定位

在现有回测框架基础上新增单股实时分析能力。用户输入股票代码，系统自动获取最新公开数据，通过算子 DAG 逐步分析，输出结构化报告。

与回测模块完全隔离，不修改任何已有代码的接口和行为。

## 与回测模块的关系

| | 回测 (backtest) | 实时分析 (live) |
|--|----------------|----------------|
| 数据源 | Tushare（付费，历史完整） | 免费爬虫（AKShare + 公开数据） |
| 时间 | 历史截面 | 当前最新 |
| 批量/单股 | 批量（多截面 × 多股票） | 单股 |
| 输出位置 | `strategies/xxx/backtest/` | `strategies/xxx/live/` |
| 算子库 | 版本锁定（如 v1） | 可用任意版本 |

两者共享引擎层（OperatorRegistry、DAG 调度、Agent Runtime、Synthesis），但数据获取和结果存储完全独立。

## 命令

```bash
# 已有命令（不变）
agent-analyze 601288.SH 2024-06-30      # Tushare 数据，指定历史截面

# 新增命令
live-analyze 601288.SH                   # 免费数据，自动获取最新
```

## 数据层：CrawlerProvider

基于 AKShare 实现，遵循已有的 DataProvider 协议。

### 数据覆盖情况

| 数据类型 | AKShare 接口 | 覆盖状态 |
|---------|-------------|---------|
| 日线行情 | stock_zh_a_hist() | ✅ 完整 |
| 资产负债表 | stock_balance_sheet_by_report_em() | ✅ 221 列，含公告日期 |
| 利润表 | stock_profit_sheet_by_report_em() | ✅ 170 列，含公告日期 |
| 现金流量表 | stock_cash_flow_sheet_by_report_em() | ✅ 316 列，含公告日期 |
| 财务指标 | stock_financial_analysis_indicator() | ✅ 86 列 |
| 分红历史 | stock_history_dividend_detail() | ✅ |
| 十大股东 | stock_main_stock_holder() | ✅ 含公告日期 |
| 每日 PE/PB/DV | 无直接接口 | ⚠️ 需从行情+财报自行计算 |
| 审计意见 | 无 | ❌ 降级处理 |
| 主营构成 | 无 | ❌ 降级处理 |
| 回购 | 无 | ❌ 降级处理 |

核心财务数据（三张表 + 指标 + 行情 + 分红 + 股东）覆盖完整。缺失的三项为补充数据，算子降级处理（标记为"数据不可用"），不影响核心分析。

### 字段映射

AKShare 东方财富接口使用英文大写字段名（如 TOTAL_ASSETS），与 Tushare 的字段名不同。CrawlerProvider 内部完成映射，对外暴露与 TushareProvider 一致的 Snapshot 结构。

## 输出结构

每次分析在策略实例目录下生成独立文件夹：

```
strategies/v6_value/live/
└── 601288.SH_2026-03-18/
    ├── raw_data/           # 爬取的原始数据
    │   ├── balance_sheet.csv
    │   ├── income.csv
    │   ├── cashflow.csv
    │   ├── daily_quotes.csv
    │   └── dividend.csv
    ├── snapshot.json        # 构建的 Snapshot
    ├── report.md            # 完整分析报告
    ├── structured.json      # 结构化结论（评分、建议、各章输出）
    └── run.log              # 运行日志（章节耗时、LLM 调用、错误）
```

每次分析自包含：原始数据 + 分析结果 + 运行日志。事后可完整复查。

## Web 分析工作台

替换现有的策略配置编辑界面（`src/web/app.py`），提供可视化的单股分析交互。

### 界面布局

```
左侧面板:
  - 策略选择（预设策略下拉 / 自定义模式）
  - 自定义模式：算子勾选列表，按依赖自动排序
  - 股票代码输入
  - 开始分析按钮

右侧面板:
  - 各章节执行状态（等待 / 运行中 / 完成）
  - 运行中章节实时显示分析进展
  - 每步完成后展示关键结论摘要

底部:
  - 最终报告（评分 + 建议 + 关键风险 + 展开全文）
```

### 实时进度展示

在 `run_blind_analysis()` 中新增可选的 `on_progress` 回调参数。CLI 不传回调，行为不变；Web 界面传回调，实时更新。

```python
async def run_blind_analysis(
    ts_code, cutoff_date, config, blind_mode, output_dir,
    on_progress=None,    # 新增，可选
):
    ...
    for ch_id, ch_def in chapters:
        if on_progress:
            on_progress("chapter_start", ch_id, ch_def["title"])

        result = await run_agent_loop(...)

        if on_progress:
            on_progress("chapter_done", ch_id, structured_output)

    if on_progress:
        on_progress("synthesis_start", None, None)
    synthesis = await run_agent_loop(...)
    if on_progress:
        on_progress("synthesis_done", None, synthesis)
```

进度事件类型：

| 事件 | 含义 |
|------|------|
| chapter_start | 开始执行某章 |
| chapter_done | 某章完成，附带结构化输出 |
| synthesis_start | 开始综合研判 |
| synthesis_done | 综合研判完成，附带最终结论 |

Web 界面通过 Streamlit 的 `st.status` 组件消费这些事件，实时更新各章节状态。

### 自定义编排

用户可在界面中勾选算子组合，系统自动根据算子的 `gate.require_prior` 声明排序为 DAG。自定义编排保存到 `workspace/` 目录，不影响正式策略。

```
workspace/                  # 临时编排
├── test_bank.yaml          # 用户自定义的银行分析框架
└── test_growth.yaml        # 用户自定义的成长股框架
```

用户满意后可手动保存为正式策略。

## 算子版本管理

```
operators/
├── v1/        # 冻结，与回测结果（+7.1pp alpha）绑定
└── v2/        # 迭代中，新增前瞻性风险算子等
```

策略通过 `operators_dir` 指定使用的版本：

```yaml
framework:
  operators_dir: operators/v1    # 或 operators/v2
```

v1 冻结后不再修改，确保回测结果始终可复现。v2 自由迭代，积累足够数据后可独立回测生成新的验证报告。

## 新增文件清单

| 文件 | 职责 |
|------|------|
| `src/data/crawler/provider.py` | CrawlerProvider：AKShare 数据获取 + 字段映射 |
| `src/data/crawler/__init__.py` | 模块初始化 |
| `src/web/app.py` | 重写为分析工作台 |
| `src/engine/launcher.py` | 新增 `live-analyze` 命令 |
| `src/agent/runtime.py` | `run_blind_analysis` 新增 `on_progress` 回调（非侵入） |

### 对已有代码的修改

| 文件 | 修改内容 | 侵入程度 |
|------|---------|---------|
| `src/agent/runtime.py` | 新增可选 `on_progress` 参数 + 约 10 处 `if on_progress` | 低（不传回调时行为不变） |
| `src/engine/launcher.py` | 新增 `live-analyze` 命令分发 | 低（新增，不改已有） |
| `src/web/app.py` | 替换为分析工作台 | 中（完全重写，但原界面无人使用） |

回测 pipeline、数据层、算子注册表、Agent 运行时的核心逻辑均不受影响。

---

*文档版本: v1.0*
*创建日期: 2026-03-18*
