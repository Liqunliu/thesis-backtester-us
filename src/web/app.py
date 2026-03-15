"""
策略调试台 — Streamlit Web App

用 st.data_editor 做表格化配置编辑，3 个主 tab:
  策略配置 | 筛选预览 | 粗略回测

启动:
    streamlit run src/web/app.py
"""
import copy
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
import yaml

from src.engine.config import StrategyConfig
from src.engine.operators import OperatorRegistry, Operator
from src.screener.quick_filter import screen_at_date

# ==================== 常量 ====================

AVAILABLE_FIELDS = [
    "pe", "pe_ttm", "pb", "ps", "ps_ttm",
    "dv_ratio", "dv_ttm",
    "total_mv", "circ_mv",
    "total_share", "float_share", "free_share",
    "turnover_rate", "turnover_rate_f",
    "volume_ratio",
    "close", "change", "pct_chg",
]

CROSS_SECTION_OPTIONS = ["1w", "2w", "1m", "2m", "3m", "6m", "1y"]

# ==================== 页面 ====================

st.set_page_config(page_title="策略调试台", page_icon="📊", layout="wide")


# ==================== 工具函数 ====================

def find_strategies() -> list:
    d = PROJECT_ROOT / "strategies"
    return sorted(str(p.relative_to(PROJECT_ROOT)) for p in d.rglob("strategy.yaml")) if d.exists() else []


def save_yaml(path: Path, data: dict):
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def save_chapters_file(config: StrategyConfig, chapters: list):
    save_yaml(config.get_chapters_path(), {'chapters': chapters})


# ---- data_editor <-> config 转换 ----

def filters_to_df(filters: list) -> pd.DataFrame:
    """过滤条件列表 → DataFrame (供 data_editor)"""
    rows = []
    for f in filters:
        rows.append({
            'field': f.get('field', ''),
            'min': f.get('min', None),
            'max': f.get('max', None),
            'fallback': f.get('fallback', ''),
        })
    if not rows:
        rows = [{'field': '', 'min': None, 'max': None, 'fallback': ''}]
    return pd.DataFrame(rows)


def df_to_filters(df: pd.DataFrame) -> list:
    """DataFrame → 过滤条件列表"""
    result = []
    for _, row in df.iterrows():
        field = str(row.get('field', '')).strip()
        if not field:
            continue
        entry = {'field': field}
        if pd.notna(row.get('min')):
            entry['min'] = float(row['min'])
        if pd.notna(row.get('max')):
            entry['max'] = float(row['max'])
        fb = str(row.get('fallback', '')).strip()
        if fb:
            entry['fallback'] = fb
        result.append(entry)
    return result


def factors_to_df(factors: list) -> pd.DataFrame:
    rows = []
    for f in factors:
        rows.append({
            'field': f.get('field', ''),
            'weight': f.get('weight', 1.0),
            'lower_better': f.get('lower_better', False),
            'full': f.get('full', 0.0),
            'zero': f.get('zero', 0.0),
        })
    if not rows:
        rows = [{'field': '', 'weight': 1.0, 'lower_better': False, 'full': 0.0, 'zero': 0.0}]
    return pd.DataFrame(rows)


def df_to_factors(df: pd.DataFrame) -> list:
    result = []
    for _, row in df.iterrows():
        field = str(row.get('field', '')).strip()
        if not field:
            continue
        result.append({
            'field': field,
            'weight': float(row.get('weight', 1.0)),
            'lower_better': bool(row.get('lower_better', False)),
            'full': float(row.get('full', 0.0)),
            'zero': float(row.get('zero', 0.0)),
        })
    return result


def tiers_to_df(tiers: list) -> pd.DataFrame:
    """分级 → 扁平表: name + 每个条件展开为 field_min / field_max 列
    简化: 用文本列 conditions 表示, 格式 "pe_ttm<=8; dv>=7"
    """
    rows = []
    for t in tiers:
        conds = t.get('conditions', [])
        cond_parts = []
        for c in conds:
            s = c['field']
            if 'min' in c:
                s += f">={c['min']}"
            if 'max' in c:
                s += f"<={c['max']}"
            cond_parts.append(s)
        rows.append({'name': t['name'], 'conditions': '; '.join(cond_parts)})
    if not rows:
        rows = [{'name': '', 'conditions': ''}]
    return pd.DataFrame(rows)


def df_to_tiers(df: pd.DataFrame) -> list:
    result = []
    for _, row in df.iterrows():
        name = str(row.get('name', '')).strip()
        if not name:
            continue
        cond_str = str(row.get('conditions', '')).strip()
        conditions = []
        for part in cond_str.split(';'):
            part = part.strip()
            if not part:
                continue
            cond = {}
            if '>=' in part:
                idx = part.index('>=')
                cond['field'] = part[:idx].strip()
                rest = part[idx + 2:].strip()
                if '<=' in rest:
                    idx2 = rest.index('<=')
                    cond['min'] = float(rest[:idx2].strip())
                    cond['max'] = float(rest[idx2 + 2:].strip())
                else:
                    cond['min'] = float(rest)
            elif '<=' in part:
                idx = part.index('<=')
                cond['field'] = part[:idx].strip()
                cond['max'] = float(part[idx + 2:].strip())
            else:
                cond['field'] = part
            if cond.get('field'):
                conditions.append(cond)
        result.append({'name': name, 'conditions': conditions})
    return result


def chapters_to_df(chapters: list) -> pd.DataFrame:
    rows = []
    for ch in chapters:
        rows.append({
            'id': ch.get('id', ''),
            'chapter': ch.get('chapter', 0),
            'title': ch.get('title', ''),
            'dependencies': ', '.join(ch.get('dependencies', [])),
            'operators': ', '.join(ch.get('operators', [])),
            'output_type': ch.get('output_type', ''),
        })
    if not rows:
        rows = [{'id': '', 'chapter': 1, 'title': '', 'dependencies': '',
                 'operators': '', 'output_type': ''}]
    return pd.DataFrame(rows)


def df_to_chapters(df: pd.DataFrame) -> list:
    result = []
    for _, row in df.iterrows():
        ch_id = str(row.get('id', '')).strip()
        if not ch_id:
            continue
        ch_num = int(row.get('chapter', 0))
        result.append({
            'id': ch_id,
            'chapter': ch_num,
            'title': str(row.get('title', '')).strip(),
            'pattern': f"## 第{'一二三四五六七八九十'[min(ch_num - 1, 9)]}章" if 1 <= ch_num <= 10 else f"## Ch{ch_num}",
            'dependencies': [d.strip() for d in str(row.get('dependencies', '')).split(',') if d.strip()],
            'operators': [d.strip() for d in str(row.get('operators', '')).split(',') if d.strip()],
            'output_type': str(row.get('output_type', '')).strip(),
        })
    return result


# ==================== 侧边栏: 策略选择 ====================

st.sidebar.header("策略")
strategies = find_strategies()

if strategies:
    selected_yaml = st.sidebar.selectbox("当前策略", strategies)
    config = StrategyConfig.from_yaml(selected_yaml)
    st.sidebar.caption(f"{config.name}  v{config.version}")
else:
    config = None

st.sidebar.divider()

# 新建策略
with st.sidebar.expander("新建策略"):
    new_id = st.text_input("策略ID", placeholder="my_strategy")
    new_display = st.text_input("名称", placeholder="我的价值投资策略")
    if st.button("创建", type="primary"):
        if new_id and new_display:
            new_dir = PROJECT_ROOT / "strategies" / new_id
            if new_dir.exists():
                st.error("已存在")
            else:
                new_dir.mkdir(parents=True)
                skeleton = {
                    'meta': {'name': new_display, 'version': '1.0.0'},
                    'paths': {'template': 'template.md', 'chapters': 'chapters.yaml'},
                    'screening': {'exclude': [], 'filters': [],
                                  'scoring': {'factors': [], 'tiers': [], 'default_tier': '不达标'}},
                    'backtest': {'cross_section_interval': '6m',
                                 'forward_periods': [
                                     {'months': 1, 'label': '1个月'}, {'months': 3, 'label': '3个月'},
                                     {'months': 6, 'label': '6个月'}, {'months': 12, 'label': '12个月'}]},
                }
                save_yaml(new_dir / "strategy.yaml", skeleton)
                save_yaml(new_dir / "chapters.yaml", {'chapters': []})
                (new_dir / "template.md").write_text("# 投资理念\n\n", encoding='utf-8')
                st.success(f"已创建: strategies/{new_id}")
                st.rerun()

# 删除策略
if config and len(strategies) > 1:
    with st.sidebar.expander("删除策略"):
        st.warning(f"将删除 {config.strategy_dir.name}")
        if st.button("确认删除"):
            shutil.rmtree(config.strategy_dir)
            st.rerun()

if config is None:
    st.info("请先创建一个策略")
    st.stop()

# ==================== 3 个 Tab ====================

tab_config, tab_operators, tab_screen, tab_backtest = st.tabs([
    "⚙️ 策略配置", "🧩 算子库", "🔍 筛选预览", "📈 粗略回测"])


# ==================== Tab 1: 策略配置 ====================

with tab_config:

    # ---- 1.1 基本信息 ----
    st.subheader("基本信息")
    raw = copy.deepcopy(config.raw)
    meta = raw.setdefault('meta', {})
    c1, c2, c3 = st.columns(3)
    meta['name'] = c1.text_input("策略名称", value=meta.get('name', ''))
    meta['version'] = c2.text_input("版本", value=meta.get('version', ''))
    bt_cfg = raw.setdefault('backtest', {})
    cur_interval = bt_cfg.get('cross_section_interval', '6m')
    bt_cfg['cross_section_interval'] = c3.selectbox(
        "截面间隔", CROSS_SECTION_OPTIONS,
        index=CROSS_SECTION_OPTIONS.index(cur_interval) if cur_interval in CROSS_SECTION_OPTIONS else 5)

    st.divider()

    # ---- 1.2 排除规则 ----
    st.subheader("排除规则")
    screening = raw.setdefault('screening', {})
    excludes = screening.get('exclude', [])
    exc_df = pd.DataFrame(excludes if excludes else [{'field': '', 'contains': ''}])
    # contains 是 list, 转成逗号字符串便于编辑
    if not exc_df.empty and 'contains' in exc_df.columns:
        exc_df['contains'] = exc_df['contains'].apply(
            lambda x: ', '.join(x) if isinstance(x, list) else str(x))
    edited_exc = st.data_editor(exc_df, num_rows="dynamic", use_container_width=True, key="exc_editor")

    st.divider()

    # ---- 1.3 过滤条件 ----
    st.subheader("过滤条件")
    st.caption("field: 字段名 | min/max: 范围 | fallback: 主字段为空时的备选(逗号分隔)")
    filters_df = filters_to_df(config.get_filters())
    col_config_filters = {
        'field': st.column_config.SelectboxColumn("field", options=AVAILABLE_FIELDS, required=True),
        'min': st.column_config.NumberColumn("min", format="%.4f"),
        'max': st.column_config.NumberColumn("max", format="%.4f"),
        'fallback': st.column_config.TextColumn("fallback"),
    }
    edited_filters = st.data_editor(
        filters_df, num_rows="dynamic", use_container_width=True,
        column_config=col_config_filters, key="filter_editor")

    st.divider()

    # ---- 1.4 评分因子 ----
    st.subheader("评分因子")
    st.caption("weight: 权重 | lower_better: 值越小越好 | full: 满分值 | zero: 零分值")
    factors_df = factors_to_df(config.get_scoring_factors())
    col_config_factors = {
        'field': st.column_config.SelectboxColumn("field", options=AVAILABLE_FIELDS, required=True),
        'weight': st.column_config.NumberColumn("weight", format="%.2f", min_value=0.0),
        'lower_better': st.column_config.CheckboxColumn("lower_better"),
        'full': st.column_config.NumberColumn("full", format="%.2f"),
        'zero': st.column_config.NumberColumn("zero", format="%.2f"),
    }
    edited_factors = st.data_editor(
        factors_df, num_rows="dynamic", use_container_width=True,
        column_config=col_config_factors, key="factor_editor")

    st.divider()

    # ---- 1.5 分级 ----
    st.subheader("分级条件")
    st.caption("name: 级别名 | conditions: 条件表达式, 用分号分隔. 示例: pe_ttm<=8; pb<=0.8; dv>=7.0")
    tiers_df = tiers_to_df(config.get_tiers())
    col_config_tiers = {
        'name': st.column_config.TextColumn("name", required=True),
        'conditions': st.column_config.TextColumn("conditions", width="large"),
    }
    edited_tiers = st.data_editor(
        tiers_df, num_rows="dynamic", use_container_width=True,
        column_config=col_config_tiers, key="tier_editor")

    default_tier = st.text_input("默认级别", value=config.get_default_tier_label())

    st.divider()

    # ---- 1.6 分析框架(章节) ----
    st.subheader("分析框架")
    st.caption("章节编排: operators 列填写算子ID(逗号分隔), data_needed 从算子自动推导")
    chapters_df = chapters_to_df(config.get_chapter_defs())
    col_config_ch = {
        'id': st.column_config.TextColumn("id", required=True),
        'chapter': st.column_config.NumberColumn("chapter", format="%d", min_value=1),
        'title': st.column_config.TextColumn("title"),
        'dependencies': st.column_config.TextColumn("dependencies"),
        'operators': st.column_config.TextColumn("operators", width="large",
                                                   help="算子ID, 逗号分隔. 见「算子库」tab"),
        'output_type': st.column_config.TextColumn("output_type"),
    }
    edited_chapters = st.data_editor(
        chapters_df, num_rows="dynamic", use_container_width=True,
        column_config=col_config_ch, key="chapter_editor")

    st.divider()

    # ---- 保存所有 ----
    if st.button("💾 保存所有配置", type="primary", use_container_width=True):
        # 基本信息
        raw['meta'] = meta
        raw['backtest'] = bt_cfg

        # 排除规则
        new_excludes = []
        for _, row in edited_exc.iterrows():
            field = str(row.get('field', '')).strip()
            contains_str = str(row.get('contains', '')).strip()
            if field and contains_str:
                new_excludes.append({
                    'field': field,
                    'contains': [x.strip() for x in contains_str.split(',') if x.strip()],
                })
        screening['exclude'] = new_excludes

        # 过滤条件
        screening['filters'] = df_to_filters(edited_filters)

        # 评分
        scoring = screening.setdefault('scoring', {})
        scoring['factors'] = df_to_factors(edited_factors)
        scoring['tiers'] = df_to_tiers(edited_tiers)
        scoring['default_tier'] = default_tier

        raw['screening'] = screening
        save_yaml(config.yaml_path, raw)

        # 章节 → 独立文件
        save_chapters_file(config, df_to_chapters(edited_chapters))

        st.success("所有配置已保存")
        st.rerun()

    # YAML 原文 (折叠)
    with st.expander("查看 YAML 原文"):
        st.code(yaml.dump(config.raw, allow_unicode=True, default_flow_style=False, sort_keys=False),
                language='yaml')


# ==================== Tab 2: 算子库 ====================

with tab_operators:
    registry = OperatorRegistry(strategy_dir=config.strategy_dir)
    all_ops = registry.list_all()
    all_tags = registry.all_tags()

    st.subheader(f"可用算子 ({len(all_ops)})")

    # 按标签筛选
    selected_tags = st.multiselect("按标签筛选", all_tags, key="op_tag_filter")
    if selected_tags:
        filtered_ops = [op for op in all_ops if any(t in op.tags for t in selected_tags)]
    else:
        filtered_ops = all_ops

    # 算子列表
    op_rows = []
    for op in filtered_ops:
        op_rows.append({
            'id': op.id,
            'name': op.name,
            'tags': ', '.join(op.tags),
            'data_needed': ', '.join(op.data_needed),
            'source': str(op.source_path.parent.name) if op.source_path else '',
            'content_len': len(op.content),
        })
    if op_rows:
        st.dataframe(pd.DataFrame(op_rows), use_container_width=True, hide_index=True)

    # 查看算子详情
    if filtered_ops:
        selected_op_id = st.selectbox("查看算子内容", [op.id for op in filtered_ops])
        selected_op = registry.get(selected_op_id)
        if selected_op:
            st.markdown(f"**{selected_op.name}** — tags: `{', '.join(selected_op.tags)}` | "
                        f"data: `{', '.join(selected_op.data_needed)}`")
            st.markdown(selected_op.content)

    st.divider()

    # 新建算子
    st.subheader("新建算子")
    nc1, nc2 = st.columns(2)
    new_op_id = nc1.text_input("算子ID", placeholder="my_operator", key="new_op_id")
    new_op_name = nc2.text_input("名称", placeholder="我的分析算子", key="new_op_name")
    new_op_tags = st.text_input("标签 (逗号分隔)", placeholder="fundamental, debt", key="new_op_tags")
    new_op_data = st.text_input("所需数据 (逗号分隔)", placeholder="balancesheet, income", key="new_op_data")
    new_op_content = st.text_area("分析指令 (Markdown)", height=200, key="new_op_content",
                                   placeholder="## 分析要点\n\n1. ...\n2. ...")

    op_scope = st.radio("保存位置", ["全局 (operators/)", f"策略私有 (strategies/{config.strategy_dir.name}/operators/)"],
                        key="op_scope")

    if st.button("创建算子", type="primary", key="create_op"):
        if new_op_id and new_op_name and new_op_content:
            tags = [t.strip() for t in new_op_tags.split(',') if t.strip()]
            data = [d.strip() for d in new_op_data.split(',') if d.strip()]
            frontmatter = yaml.dump({
                'id': new_op_id, 'name': new_op_name,
                'tags': tags, 'data_needed': data,
            }, allow_unicode=True, default_flow_style=False).strip()

            md_content = f"---\n{frontmatter}\n---\n\n{new_op_content}\n"

            if "全局" in op_scope:
                target_dir = PROJECT_ROOT / "operators"
            else:
                target_dir = config.strategy_dir / "operators"
            target_dir.mkdir(parents=True, exist_ok=True)

            target_path = target_dir / f"{new_op_id}.md"
            if target_path.exists():
                st.error(f"算子已存在: {target_path}")
            else:
                target_path.write_text(md_content, encoding='utf-8')
                st.success(f"已创建: {target_path}")
                st.rerun()
        else:
            st.warning("请填写算子ID、名称和内容")


# ==================== Tab 3: 筛选预览 ====================

with tab_screen:
    c1, c2, c3 = st.columns([2, 1, 1])
    cutoff_date = c1.date_input("截面日期", value=pd.to_datetime("2024-06-30"))
    top_n = c2.number_input("候选数", value=50, min_value=10, max_value=500, step=10)
    run = c3.button("运行筛选", type="primary", use_container_width=True)

    if run:
        cutoff_str = cutoff_date.strftime('%Y-%m-%d')
        with st.spinner(f"筛选中 {cutoff_str} ..."):
            result = screen_at_date(cutoff_str, config=config, top_n=top_n)

        m1, m2, m3 = st.columns(3)
        m1.metric("全市场", f"{result.total_stocks}")
        m2.metric("过滤后", f"{result.after_basic_filter}")
        m3.metric("候选", f"{len(result.candidates)}")

        if not result.candidates.empty:
            # 评级分布
            if 'tier_rating' in result.candidates.columns:
                dist = result.candidates['tier_rating'].value_counts()
                cols = st.columns(max(len(dist), 1))
                for i, (rating, count) in enumerate(dist.items()):
                    cols[i].metric(rating, count)

            # 候选表
            display = [c for c in result.candidates.columns if c not in ('trade_date', 'total_mv')]
            st.dataframe(result.candidates[display], use_container_width=True, hide_index=True)

            # 分布图
            factors = config.get_scoring_factors()
            chart_fields = [f['field'] for f in factors[:2] if f['field'] in result.candidates.columns]
            if chart_fields:
                chart_cols = st.columns(len(chart_fields))
                for i, fld in enumerate(chart_fields):
                    with chart_cols[i]:
                        st.caption(fld)
                        st.bar_chart(result.candidates[fld].dropna())
        else:
            st.warning("无候选，请调整过滤条件")


# ==================== Tab 3: 粗略回测 ====================

with tab_backtest:
    st.caption("在多个历史截面运行筛选，观察候选池稳定性")

    default_dates = "2022-06-30, 2022-12-31, 2023-06-30, 2023-12-31, 2024-06-30"
    dates_input = st.text_input("截面日期 (逗号分隔)", value=default_dates)
    bt_top = st.number_input("每截面候选数", value=50, min_value=10, max_value=200, step=10, key="bt_top")

    if st.button("运行回测", type="primary"):
        dates = [d.strip() for d in dates_input.split(',') if d.strip()]
        bar = st.progress(0)
        results = []

        for i, date in enumerate(dates):
            bar.progress(i / len(dates), text=date)
            try:
                r = screen_at_date(date, config=config, top_n=bt_top)
                results.append({'截面': date, '全市场': r.total_stocks,
                                '过滤后': r.after_basic_filter, '候选': len(r.candidates),
                                **(r.candidates['tier_rating'].value_counts().to_dict()
                                   if not r.candidates.empty and 'tier_rating' in r.candidates.columns
                                   else {})})
            except Exception as e:
                st.warning(f"{date}: {e}")
        bar.progress(1.0, text="完成")

        if results:
            st.dataframe(pd.DataFrame(results).fillna(0), use_container_width=True, hide_index=True)
            trend = pd.DataFrame(results)[['截面', '候选']].set_index('截面')
            st.line_chart(trend)
