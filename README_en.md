# Thesis Backtester — Backtest Any Investment Thesis with AI

> Can AI validate whether an investment philosophy actually works — before you risk real money?

**Thesis Backtester** is an open-source engine that backtests *qualitative* investment ideas using LLM-powered blind analysis. Unlike traditional quant backtesting (which only works with numeric rules like "buy when PE < 10"), this tool validates the kind of judgment calls real investors make:

- "Is this high dividend sustainable or a trap?"
- "Is this low PE genuinely cheap or a value trap?"
- "Does management have integrity?"
- "Can this business model survive a downturn?"

## The Core Idea

```
Traditional backtest:  numeric rule  →  historical prices  →  P&L
Thesis backtest:       investment philosophy  →  AI blind analysis  →  compare with actual outcomes
```

**How it works:**

1. **Define** your investment thesis as operator compositions (`.md` analysis instructions + YAML config)
2. **Screen** historical cross-sections with declarative quantitative filters
3. **Blind-test**: feed the AI only financial data available *up to that date*, with company names hidden
4. **Validate**: compare AI's buy/avoid recommendations against actual forward returns with 5-dimensional quality scoring

The key insight: **any investment idea that can be described in words can be backtested this way.**

## Proof of Concept: 6-Year Blind Test

We validated a value investing thesis (turtle-grade screening: low PE + low PB + high dividend yield + FCF quality) across **60 stocks over 12 half-year cross-sections from 2019 to 2024**.

### Results

| Strategy | Samples | Avg 6-Month Return | Win Rate |
|----------|---------|-------------------|----------|
| Quantitative screening only | 60 | +7.5% | — |
| Quant + AI filtering (buy signals only) | 9 | **+24.1%** | **67%** |
| **AI filtering alpha** | — | **+16.6 pp** | — |

### What AI Does Well

| Strength | Evidence |
|----------|----------|
| Identifying leveraged value traps | 16 of 18 real estate stocks flagged as "avoid", avg return -10% |
| High-conviction buy signals | 6 stocks scored ≥70 with "buy": avg +41.5%, 83% win rate |
| Knowing when NOT to invest | No buy signals in 2019 & 2024 = cash preservation during downturns |

### Where AI Struggles

| Weakness | Evidence |
|----------|----------|
| Cyclical bottom reversals | Scored 25 on a stock that returned +73% |
| Too conservative in bull markets | "Avoid" signals averaged +30.6% return in 2020 |

### Year-by-Year Performance

| Year | Quant Only | AI High-Conviction | Notable Picks |
|------|-----------|-------------------|---------------|
| 2019 | -9.9% | Cash (no signal) | — |
| 2020 | +28.4% | -13.3% | 1 miss (bank stock) |
| 2021 | +7.7% | +21.4% | China Shenhua +46% |
| 2022 | +0.9% | +28.7% | PetroChina +50% |
| 2023 | +9.5% | +48.4% | 3 coal/bank picks, avg +48% |
| 2024 | +8.8% | Cash (no signal) | — |

> Full details in `strategies/v6_value/backtest/` directory

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Strategy Instance                        │
│  strategy.yaml (screening + chapters + operators + LLM config)  │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                      Engine Layer (src/engine/)                  │
│  StrategyConfig · Launcher · FactorRegistry · OperatorRegistry  │
│  Tracker (SQLite)                                               │
└──────┬──────────┬──────────┬──────────┬─────────────────────────┘
       │          │          │          │
┌──────▼───┐ ┌───▼────┐ ┌──▼────┐ ┌───▼──────┐
│ Screener │ │ Agent  │ │ Back- │ │   Web    │
│          │ │ (Blind)│ │ test  │ │ Dashboard│
└──────┬───┘ └───┬────┘ └──┬────┘ └───┬──────┘
       │         │         │          │
┌──────▼─────────▼─────────▼──────────▼───────────────────────────┐
│                      Data Layer (src/data/)                      │
│  Provider (abstract) · Parquet Storage · Snapshot (parallel I/O)│
└─────────────────────────────────────────────────────────────────┘
```

### Project Structure

```
src/
├── engine/        # Engine: StrategyConfig + Launcher + FactorRegistry + OperatorRegistry + Tracker
├── data/          # Data: Provider abstraction + Parquet storage + time-point snapshots
│   └── tushare/   #   Tushare Provider implementation
├── agent/         # Agent: LLM blind analysis (DAG scheduling + tool_use + 16 data query tools)
├── screener/      # Screener: declarative quantitative filtering (reads pre-computed factors)
├── backtest/      # Backtest: batch backtest + forward return collection + 5-dim quality scoring
└── web/           # Web: Streamlit strategy tuning dashboard

factors/           # Quantitative factor definitions (.py, cross-section + time-series)
operators/         # Qualitative analysis operators (.md, YAML frontmatter + instructions, 21 total)
  ├── screening/   #   Data quality, geopolitical, quick screen, SOE identification
  ├── fundamental/ #   Debt, cycle, cash flow, management, stream classification, recovery
  ├── valuation/   #   FCF, dividend, PE trap, safety margin, owner earnings, valuation repair
  ├── decision/    #   Apple model, position management, stress test
  └── special/     #   Cigar butt, light asset model

strategies/        # Strategy instances (one directory per investment thesis)
└── v6_value/      #   V6 Value Investing (operator-driven, 6 chapters, 21 operators)
    └── strategy.yaml  # All-in-one config: screening + chapters + operators + LLM
```

### Key Design Decisions

- **Operator-driven**: Analysis logic lives in operators (`.md` files). Strategies compose operators via YAML. Output schema auto-generated from operator frontmatter `outputs` fields
- **Blind testing**: Company names hidden to eliminate AI brand bias and memory contamination
- **Time-boundary enforcement**: 3-layer protection — data layer hard filtering (by announcement date), prompt injection, agent tool sandbox
- **Strategy-as-config**: Engine is thesis-agnostic; `strategy.yaml` defines screening + analysis framework + LLM parameters in one file
- **Industry gates**: Operator-level exclusion guards prevent misapplication (e.g., FCF valuation on banks, cigar butt classification on profitable companies)
- **Provider abstraction**: Data sources decoupled via Protocol; swap Tushare by implementing the interface

## Quick Start

### Prerequisites

- Python 3.9+
- [Tushare Pro](https://tushare.pro/) API token (for A-share market data)
- An OpenAI-compatible LLM API (the analysis prompts are in Chinese)

### Installation

```bash
pip install -e .
export TUSHARE_TOKEN="your_token_here"
```

### Data Initialization

```bash
# Initialize basic data (stock list + trade calendar)
python -m src.engine.launcher data init-basic

# Initialize market data (daily quotes + indicators + factors)
python -m src.engine.launcher data init-market 2020-01-01

# Daily incremental update
python -m src.engine.launcher data daily-update
```

### Usage

```bash
# Quantitative screening
python -m src.engine.launcher strategies/v6_value/strategy.yaml screen 2024-06-30

# Single stock agent analysis (requires LLM_API_KEY + LLM_BASE_URL)
python -m src.engine.launcher strategies/v6_value/strategy.yaml agent-analyze 601288.SH 2024-06-30

# Batch cross-section backtest
python -m src.backtest.batch_backtest --strategy strategies/v6_value/strategy.yaml --top 50

# Forward return collection
python -m src.backtest.outcome_collector 601288.SH 2024-06-30

# Web tuning dashboard
streamlit run src/web/app.py
```

### Creating Your Own Strategy

1. Create `strategies/<name>/strategy.yaml` (reference [v6_value](strategies/v6_value/strategy.yaml))
2. Define quantitative screening conditions in `screening` section
3. Compose operators in `framework.chapters` (or create new operators in `operators/`)
4. Run screening → agent analysis → backtest validation

No code required. Output schema is auto-generated from operator `outputs` definitions.

## What Can Be Backtested?

Any investment philosophy that can be described in words:

| Thesis | Core Question | Status |
|--------|--------------|--------|
| Turtle-grade value investing | "Is this cheap stock genuinely undervalued?" | **Validated: +16.6pp alpha** |
| Dividend trap identification | "Is this high yield sustainable?" | Planned |
| Distressed turnaround | "Will this fallen angel recover?" | Planned |
| Cyclical timing | "Where are we in the cycle?" | Planned |
| Growth at reasonable price | "Can high growth justify high PE?" | Planned |
| SOE value rerating | "Does state reform translate to returns?" | Planned |

New strategies only require a `strategy.yaml` composing operators — no engine code changes needed.

## How It Differs from Existing Tools

| Category | Examples | What They Test | What We Test |
|----------|---------|---------------|-------------|
| Quant backtesting | Zipline, Backtrader | Numeric trading rules | **Qualitative judgment** |
| AI stock screeners | Various | Factor scoring | **Structured thesis validation** |
| Research platforms | Wind, Bloomberg | Information retrieval | **Decision verification** |
| Robo-advisors | Wealthfront | Portfolio allocation | **Investment methodology** |

## Documentation

### Design Docs

- [Architecture](docs/design/architecture.md) — System layers and module responsibilities
- [Agent Runtime](docs/design/agent.md) — DAG scheduling, prompt assembly, tool sandbox
- [Data Layer](docs/design/data_layer.md) — Provider abstraction, Parquet storage, snapshots
- [Operators & Factors](docs/design/operators.md) — 21 operator catalog, auto-schema, industry gates
- [Screener](docs/design/screener.md) — Declarative quantitative screening engine
- [Backtest](docs/design/backtest.md) — Batch backtest, 5-dimensional quality scoring

### Planning Docs

- [Product Design](docs/investment_thesis_backtester.md) — Full product vision
- [Data Roadmap](docs/data_dimensions_roadmap.md) — Implemented and planned data dimensions
- [Framework Evolution](docs/framework_evolution.md) — Error pattern analysis and improvement directions
- [Scaling Plan](docs/scaling_plan.md) — Scaling from 60 to 600+ samples

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.9+ |
| Storage | Parquet (zstd compression, monthly/stock partitions) |
| Database | SQLite (analysis tracking) |
| LLM Interface | OpenAI-compatible API (async, tool_use) |
| Data Source | Tushare Pro API (Provider abstraction) |
| Web | Streamlit |

## Contributing

This project is in early stage. Contributions welcome in:

- **New strategy instances** — bring your own investment thesis, create a `strategy.yaml` composing operators
- **New analysis operators** — add `.md` files to `operators/`
- **Data source adapters** — implement `DataProvider` Protocol for US/HK market data
- **Multi-model comparison** — GPT, Gemini, DeepSeek benchmarks

## License

Apache License 2.0

## Disclaimer

This tool is for **investment methodology research and validation only**. It does not constitute investment advice. Past backtest results do not guarantee future performance. Always do your own due diligence.

---

[中文文档](README.md)
