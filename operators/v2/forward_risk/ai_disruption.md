---
id: ai_disruption_risk
name: AI/大模型冲击风险评估
tags: [risk, forward_looking]
data_needed: [income, fina_mainbz]
outputs:
  - field: disruption_level
    type: enum [高危, 中等, 低, 受益]
  - field: revenue_at_risk_pct
    type: number
  - field: disruption_timeline
    type: text
  - field: ai_opportunity
    type: text
  - field: disruption_reasoning
    type: text
---

## 分析目标

评估 AI/大模型技术发展对该公司核心业务的替代风险或增益机会。

## 分析框架

### 1. 核心业务拆解

从利润表和主营构成中识别：
- 主要收入来源是什么？各占多少比例？
- 每项业务的本质是什么？（信息处理 / 实体制造 / 人工服务 / 资源垄断）

### 2. 逐项评估 AI 替代可能性

对每项主要业务判断：

| 业务类型 | AI 替代风险 |
|---------|-----------|
| 软件/SaaS | 高 — AI 可能直接生成同类功能 |
| 信息服务/咨询 | 高 — AI 能替代信息整理和基础分析 |
| 中介/平台 | 中高 — AI Agent 可能绕过中介 |
| 金融服务 | 中 — 受监管保护但效率压力大 |
| 制造/实体 | 低 — 短期不受直接冲击 |
| 资源/能源 | 低 — 实体资源不可替代 |
| AI 基础设施 | 受益 — 算力/数据/芯片需求增长 |

### 3. 收入风险比例

估算受 AI 冲击的收入占总收入的百分比（revenue_at_risk_pct）。

### 4. 时间线判断

- 已经在发生（竞争对手已推出 AI 替代方案）
- 1-2 年内（技术成熟但尚未大规模应用）
- 3-5 年内（趋势明确但落地需要时间）
- 暂不明确

### 5. 转型能力

公司是否有主动拥抱 AI 的迹象？
- 有 AI 相关投入/专利/产品 → 可能转危为机
- 无任何 AI 布局 → 被动等待被替代

## 注意

- 实体经济（制造、资源、农业）短期不受 AI 直接冲击，但效率提升压力存在
- 银行等受监管保护的行业，AI 冲击被延缓但不是消除
- 要区分"AI 冲击收入"和"AI 提升效率"——后者可能是利好
