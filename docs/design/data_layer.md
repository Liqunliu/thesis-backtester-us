# 数据层设计

## 设计目标

1. **完整性**：覆盖日线行情、估值指标、复权因子、财报（6类）、分红、十大股东、治理风险数据
2. **增量更新**：所有数据支持增量获取，避免重复拉取
3. **数据源解耦**：通过 Protocol 抽象，支持多种数据源无缝切换
4. **因子预计算**：截面因子 + 时序因子全量预计算，筛选时零计算
5. **时间边界**：快照生成严格按公告日期过滤，杜绝前视偏差
6. **性能优化**：PyArrow predicate pushdown、lru_cache、ThreadPoolExecutor 并行 I/O

## 分层架构

```
┌─────────────────────────────────────────────────────┐
│              Consumer Layer (只读)                    │
│  api.py (查询接口, lru_cache)                        │
│  snapshot.py (时点快照, ThreadPoolExecutor 并行 I/O)  │
├─────────────────────────────────────────────────────┤
│              Computation Layer                       │
│  factor_store.py (因子预计算 + _CachedApi 批量缓存)   │
├─────────────────────────────────────────────────────┤
│              Orchestration Layer                     │
│  updater.py (DataUpdater: 增量编排)                  │
├─────────────────────────────────────────────────────┤
│              Persistence Layer                       │
│  storage.py (Parquet I/O: 月分区/股票分区,            │
│              predicate pushdown via PyArrow filters)  │
├─────────────────────────────────────────────────────┤
│              Abstraction Layer                       │
│  provider.py (DataProvider Protocol + Registry)      │
├─────────────────────────────────────────────────────┤
│              Implementation Layer                    │
│  tushare/provider.py (Tushare Pro API 封装)          │
└─────────────────────────────────────────────────────┘
```

## DataProvider 协议

```python
@runtime_checkable
class DataProvider(Protocol):
    @property
    def name(self) -> str: ...

    # --- 基础数据 ---
    def fetch_stock_list(self) -> pd.DataFrame: ...
    def fetch_trade_calendar(self, start_date, end_date) -> pd.DataFrame: ...

    # --- 日线市场数据 (按日期批量) ---
    def fetch_daily_bulk(self, trade_date) -> pd.DataFrame: ...
    def fetch_adj_factor_bulk(self, trade_date) -> pd.DataFrame: ...
    def fetch_daily_indicator_bulk(self, trade_date) -> pd.DataFrame: ...

    # --- 财报数据 (按股票) ---
    def fetch_balancesheet(self, ts_code) -> pd.DataFrame: ...
    def fetch_income(self, ts_code) -> pd.DataFrame: ...
    def fetch_cashflow(self, ts_code) -> pd.DataFrame: ...
    def fetch_financial_indicator(self, ts_code) -> pd.DataFrame: ...
    def fetch_dividend(self, ts_code) -> pd.DataFrame: ...
    def fetch_top10_holders(self, ts_code) -> pd.DataFrame: ...
    def fetch_disclosure_date(self, end_date) -> pd.DataFrame: ...

    # --- 治理与风险数据 (按股票) ---
    def fetch_fina_audit(self, ts_code) -> pd.DataFrame: ...
    def fetch_fina_mainbz(self, ts_code) -> pd.DataFrame: ...
    def fetch_pledge_stat(self, ts_code) -> pd.DataFrame: ...
    def fetch_stk_holdernumber(self, ts_code) -> pd.DataFrame: ...
    def fetch_stk_holdertrade(self, ts_code) -> pd.DataFrame: ...
    def fetch_share_float(self, ts_code) -> pd.DataFrame: ...
    def fetch_repurchase(self, ts_code) -> pd.DataFrame: ...
```

### Provider 注册与获取

```python
# 注册
register("tushare", TushareProvider())

# 获取（懒加载：首次调用时自动实例化 Tushare）
provider = get_provider()          # 默认 provider
provider = get_provider("tushare") # 指定 provider

# 切换默认
set_default("akshare")
```

### Tushare 实现

Provider 实现位于 `src/data/tushare/provider.py`（子目录，非单文件），包含所有 Tushare Pro API 调用封装。

### 扩展新数据源

实现 `DataProvider` 协议即可：

```python
class AKShareProvider:
    @property
    def name(self) -> str:
        return "akshare"

    def fetch_stock_list(self) -> pd.DataFrame:
        # 返回 ts_code, name, industry, list_status, list_date
        ...
```

## 存储设计

### 目录结构

```
data/
├── tushare/                     # 市场数据根目录
│   ├── basic/                   # 基础数据（全量覆盖）
│   │   ├── stock_list.parquet
│   │   └── trade_calendar.parquet
│   ├── daily/                   # 日线数据（月分区）
│   │   ├── raw/                 #   OHLCV
│   │   │   ├── 2019-01.parquet
│   │   │   └── ...
│   │   ├── indicator/           #   PE/PB/DV/市值
│   │   ├── adj_factor/          #   复权因子
│   │   ├── factors/             #   预计算截面因子
│   │   └── ts_factors/          #   预计算时序因子
│   │       └── latest.parquet   #     (单文件，每股票一行)
│   └── financial/               # 财报数据（按股票分区）
│       ├── balancesheet/
│       ├── income/
│       ├── cashflow/
│       ├── fina_indicator/
│       ├── dividend/
│       ├── top10_holders/
│       ├── top10_floatholders/
│       ├── disclosure_date/
│       ├── fina_audit/          # 审计意见
│       ├── fina_mainbz/         # 主营业务构成
│       ├── pledge_stat/         # 股权质押
│       ├── stk_holdernumber/    # 股东户数
│       ├── stk_holdertrade/     # 高管增减持
│       ├── share_float/         # 限售解禁
│       └── repurchase/          # 回购
└── snapshots/                   # 生成的时点快照
```

### 分区策略

| 数据类型 | 分区方式 | 分区键 | 写入模式 |
|---------|---------|--------|---------|
| 股票列表 | 单文件 | — | overwrite |
| 交易日历 | 单文件 | — | overwrite |
| 日线行情 | 按月 | `YYYY-MM` | merge (ts_code + trade_date) |
| 日线指标 | 按月 | `YYYY-MM` | merge (ts_code + trade_date) |
| 复权因子 | 按月 | `YYYY-MM` | merge (ts_code + trade_date) |
| 截面因子 | 按月 | `YYYY-MM` | merge (ts_code + trade_date) |
| 时序因子 | 单文件 | `latest` | merge (ts_code) |
| 财报数据 | 按股票 | `ts_code` | merge (ts_code + end_date) |
| 治理风险数据 | 按股票 | `ts_code` | merge (依数据类型) |

### Merge 模式

增量更新的核心：新数据与旧数据合并，按 merge_on 列去重，保留最新。

```python
# storage.save() with mode='merge'
existing = load_one(...)
combined = pd.concat([existing, new_df])
combined = combined.drop_duplicates(subset=merge_on, keep='last')
combined = combined.sort_values(merge_on)
combined.to_parquet(path, compression='zstd')
```

### 性能优化：Predicate Pushdown

`storage.load_range()` 使用 PyArrow filters 实现谓词下推，避免全量加载月分区文件：

```python
# 按 ts_code 过滤时，只读取匹配的行组
filters = [('ts_code', '=', ts_code)] if ts_code else None
table = pq.read_table(path, filters=filters)
```

## 增量更新

### DataUpdater 类

```python
class DataUpdater:
    def __init__(self, provider_name=None):
        self.provider = get_provider(provider_name)

    # 自动检测最新日期，只拉取增量
    def update_daily(self, start_date=None, end_date=None):
        if start_date is None:
            start_date = storage.get_latest_date('daily', 'raw')  # 从断点续传

    def daily_update(self):
        """日常一键更新"""
        self.update_stock_list()
        self.update_daily()
        self.update_daily_indicator()
        self.update_factors()

    def full_update(self, market_start, financial_codes):
        """全量初始化"""
        self.init_basic()
        self.update_daily(market_start)
        self.update_daily_indicator(market_start)
        self.update_financials(financial_codes)
        self.update_factors()
        self.update_ts_factors(financial_codes)
```

### 更新命令

```bash
# 日常增量（行情 + 指标 + 截面因子）
python -m src.engine.launcher data daily-update

# 全量初始化
python -m src.engine.launcher data full-update 2020-01-01 601288.SH 000001.SZ

# 单独更新
python -m src.engine.launcher data update-daily
python -m src.engine.launcher data update-indicator
python -m src.engine.launcher data update-financials 601288.SH 000001.SZ
python -m src.engine.launcher data update-factors
python -m src.engine.launcher data update-ts-factors
python -m src.engine.launcher data recalc-factors
python -m src.engine.launcher data recalc-ts-factors
```

## 因子预计算

### 两类因子

| | 截面因子 (Cross-Section) | 时序因子 (Time-Series) |
|--|------------------------|---------------------|
| **计算粒度** | 每个交易日 × 每只股票 | 每只股票（一次） |
| **输入** | 当日全市场 indicator DataFrame | 单只股票的历史财报 |
| **输出** | `Series`（与输入 index 对齐） | `float` 标量 |
| **存储** | `daily/factors/{YYYY-MM}.parquet` | `daily/ts_factors/latest.parquet` |
| **行数** | 每月 ~5000 × ~22 交易日 = ~110,000 行 | ~5500 行（每股票一行） |
| **更新策略** | 增量：从最新日期续算 | 增量：跳过已有值的股票 |
| **典型因子** | dv, ep, market_cap_yi | profit_growth_5y, roe_avg_3y, dividend_years |

### _CachedApi 优化

时序因子计算需要读取每只股票的财报。直接调用 `api.get_income(ts_code)` 会逐股票加载 Parquet 文件，5000+ 股票耗时过长。

`_CachedApi` 解决方案：一次性将所有财报文件加载到内存，按 `{data_type: {ts_code: DataFrame}}` 组织，后续查询直接命中内存缓存。

## 公共查询接口 (api.py)

所有上层模块通过 `api.py` 读取数据，不直接操作 storage。

### 缓存策略

`api.py` 使用 `functools.lru_cache` 缓存高频读取的元数据：

```python
@functools.lru_cache(maxsize=2)
def _load_stock_list() -> pd.DataFrame: ...

@functools.lru_cache(maxsize=1)
def _load_trade_calendar() -> pd.DataFrame: ...
```

### 查询接口

```python
# 市场数据
api.get_daily(start_date, end_date, ts_code=None)
api.get_daily_adjusted(start_date, end_date, adjust='qfq')  # 前/后复权
api.get_daily_indicator(start_date, end_date, ts_code=None)

# 财报
api.get_income(ts_code, end_date=None)
api.get_balancesheet(ts_code, end_date=None)
api.get_cashflow(ts_code, end_date=None)
api.get_financial_indicator(ts_code, end_date=None)
api.get_dividend(ts_code)
api.get_top10_holders(ts_code, end_date=None)

# 治理风险
api.get_fina_audit(ts_code, end_date=None)
api.get_fina_mainbz(ts_code, end_date=None)
api.get_pledge_stat(ts_code, end_date=None)
api.get_stk_holdernumber(ts_code, end_date=None)

# 预计算因子
api.get_factors(start_date, end_date, ts_code=None)      # 截面因子
api.get_ts_factors(ts_code=None)                          # 时序因子
api.get_daily_indicator_with_factors(...)                  # 指标 + 因子合并

# 元信息
api.get_stock_list()
api.get_stock_name(ts_code)
api.get_trade_dates(start_date, end_date)
api.get_data_status()
```

## 时点快照 (Snapshot)

### 设计目标

为 Agent 分析提供严格符合时间边界的数据上下文。快照包含截止日期之前已公开的所有信息，不包含任何未来信息。

### StockSnapshot 数据结构

```python
@dataclass
class StockSnapshot:
    ts_code: str
    stock_name: str
    cutoff_date: str
    generated_at: str
    industry: str = ''          # 行业分类
    area: str = ''              # 地区
    list_date: str = ''         # 上市日期

    # 行情数据 (trade_date <= cutoff_date)
    price_history: pd.DataFrame     # ~3年日线
    daily_indicators: pd.DataFrame  # PE/PB/DV/市值

    # 基本面数据 (ann_date <= cutoff_date)
    balancesheet: pd.DataFrame
    income: pd.DataFrame
    cashflow: pd.DataFrame
    fina_indicator: pd.DataFrame
    dividend: pd.DataFrame
    top10_holders: pd.DataFrame
    top10_floatholders: pd.DataFrame

    # 治理与风险数据
    fina_audit: pd.DataFrame        # 审计意见
    fina_mainbz: pd.DataFrame       # 主营业务构成
    pledge_stat: pd.DataFrame       # 股权质押统计
    stk_holdernumber: pd.DataFrame  # 股东户数变化
    stk_holdertrade: pd.DataFrame   # 高管增减持
    share_float: pd.DataFrame       # 限售解禁
    repurchase: pd.DataFrame        # 回购

    # 元数据
    latest_report_period: str
    data_sources: List[str]
    warnings: List[str]
```

### 并行 I/O

`create_snapshot()` 使用 `ThreadPoolExecutor` 并行加载各类数据，显著减少快照生成时间：

```python
with ThreadPoolExecutor() as executor:
    futures = {
        'price': executor.submit(api.get_daily, start, cutoff, ts_code=ts_code),
        'indicator': executor.submit(api.get_daily_indicator, start, cutoff, ts_code=ts_code),
        'income': executor.submit(api.get_income, ts_code),
        'balancesheet': executor.submit(api.get_balancesheet, ts_code),
        # ... 其他数据类型并行加载
    }
```

### 公告日期过滤逻辑

财报数据的过滤不是按报告期（end_date），而是按实际公告日期：

```
优先级：
1. f_ann_date（首次公告日）  ← 最准确
2. ann_date（公告日）        ← 次选
3. disclosure_date 表关联    ← 第三选
4. end_date + 6个月保守估计  ← 最后兜底
```

### 盲测模式

`snapshot_to_markdown(snapshot, blind_mode=True)` 输出中：
- 隐藏公司名称和代码
- 十大股东按属性分类（国有/机构/自然人/其他法人），不显示名称
- 标注"盲测模式：请仅基于数据做出判断"
- 保留行业分类（从财务数据可推断，不构成信息泄露）
