---
id: industry_position
name: 行业地位与竞争格局分析
tags: [fundamental, forward_looking]
data_needed: [income, fina_indicator]
outputs:
  - field: market_position
    type: enum [龙头, 第二梯队, 一般, 边缘化]
  - field: competitive_moat
    type: enum [强, 中, 弱, 无]
  - field: moat_type
    type: text
  - field: industry_trend
    type: enum [增长, 成熟, 衰退, 周期性]
  - field: position_reasoning
    type: text
---

## 分析目标

评估公司在行业中的竞争地位、护城河强度和行业发展趋势。

## 分析框架

### 1. 行业定位

基于公司规模（收入/市值）和行业特征判断：
- 龙头：行业前 3，具有定价权
- 第二梯队：行业 4-10 位，有一定竞争力
- 一般：中等规模，无明显优势
- 边缘化：小市值，可能被整合

### 2. 护城河类型

| 护城河 | 判断标准 |
|--------|---------|
| 规模优势 | 营收远超同行，规模效应明显 |
| 品牌壁垒 | 毛利率持续高于行业平均 |
| 网络效应 | 用户/商户越多越有价值 |
| 牌照/特许 | 银行、保险、运营商等 |
| 技术专利 | 研发投入高、专利壁垒 |
| 转换成本 | 客户替换成本高 |
| 资源垄断 | 矿产、土地等自然资源 |

### 3. 行业生命周期

- 增长期：收入增速 > 15%，行业渗透率低
- 成熟期：增速 5-15%，格局稳定
- 衰退期：增速 < 5% 或负增长，被新技术替代
- 周期性：收入随经济周期大幅波动

### 4. 竞争格局变化

- 调用 `query_market_context(info_type="industry_overview")` 了解行业近况
- 调用 `query_market_context(info_type="news")` 看是否有行业变局信号
- 新进入者威胁？替代品威胁？上下游议价能力变化？

## 注意

- 银行、保险等牌照型企业天然有强护城河
- 周期性行业的龙头在周期底部可能被误判为"衰退"
- 护城河强度应该看 3-5 年视角，不是当期财报能完全反映的
