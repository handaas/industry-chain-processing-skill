#!/usr/bin/env python3
"""Render an industry-chain analysis result as standalone HTML or Markdown."""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import pathlib
import sys
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from common import json_dumps


def load_payload(input_path: str | None) -> Dict[str, Any]:
    if input_path:
        path = pathlib.Path(input_path).expanduser()
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        raw = sys.stdin.read().strip()
        if not raw:
            raise SystemExit("请提供 --input <result.json> 或通过 stdin 传入 JSON")
        data = json.loads(raw)
    if not isinstance(data, dict):
        raise SystemExit("报告输入必须是 JSON object")
    return data


def as_list(value: Any) -> List[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    return [value]


def first_present(data: Mapping[str, Any], keys: Sequence[str], default: Any = None) -> Any:
    for key in keys:
        if key in data and data[key] not in (None, "", []):
            return data[key]
    return default


def infer_title(data: Mapping[str, Any], explicit: str | None = None) -> str:
    if explicit:
        return explicit
    title = first_present(data, ["title", "report_title"])
    if title:
        return str(title)
    chain = first_present(data, ["chain", "industry", "industry_chain"])
    node = first_present(data, ["node", "segment", "matched_segment"])
    if chain and node:
        return f"{chain} - {node} 企业分析报告"
    if chain:
        return f"{chain} 企业分析报告"
    return "旷湖产业链分析报告"


def normalize_decisions(data: Mapping[str, Any]) -> List[Dict[str, Any]]:
    decisions = first_present(data, ["decisions", "decision_results", "links"], [])
    out: List[Dict[str, Any]] = []
    for item in as_list(decisions):
        if isinstance(item, dict):
            out.append(item)
        else:
            out.append({"decision": str(item)})
    return out


def normalize_candidates(data: Mapping[str, Any]) -> List[Dict[str, Any]]:
    candidates = first_present(data, ["candidates", "companies", "samples"], [])
    if not candidates and isinstance(data.get("preview"), dict):
        candidates = data["preview"].get("samples", [])
    out: List[Dict[str, Any]] = []
    for item in as_list(candidates):
        if isinstance(item, dict):
            out.append(item)
        else:
            out.append({"name": str(item)})
    return out


def decision_counts(decisions: Sequence[Mapping[str, Any]]) -> Dict[str, int]:
    counts = {"confirmed": 0, "uncertain": 0, "rejected": 0}
    for item in decisions:
        label = str(item.get("decision") or "uncertain")
        counts[label] = counts.get(label, 0) + 1
    return counts


def decision_label(value: Any) -> str:
    return {
        "confirmed": "确认挂链",
        "uncertain": "待复核",
        "rejected": "不建议挂链",
    }.get(str(value or ""), str(value or "待复核"))


def strength_label(value: Any) -> str:
    return {
        "strong": "强",
        "medium": "中",
        "weak": "弱",
    }.get(str(value or ""), str(value or "-"))


def route_label(value: Any) -> str:
    return {
        "operator_confirmed": "已确认条件",
        "industry_business_consensus": "行业与业务共识",
        "industry_registration_scope": "行业与经营范围",
        "industry_business_keyword": "行业与业务关键词",
        "business_consensus_precision": "业务双字段共识",
        "registration_scope_precision": "经营范围精确召回",
        "business_keyword_precision": "业务关键词精确召回",
        "web_presence_recall": "官网信息补充召回",
        "project_seed": "项目代表企业校准",
        "external_condition": "外部确认条件",
    }.get(str(value or ""), str(value or "-"))


def text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json_dumps(value, pretty=True)
    return str(value)


def esc(value: Any) -> str:
    return html.escape(text(value), quote=True)


def render_html_list(items: Iterable[Any]) -> str:
    rows = []
    for item in items:
        if isinstance(item, dict):
            label = item.get("name") or item.get("title") or item.get("segment") or item.get("matched_segment") or item
            rows.append(f"<li><pre>{esc(label)}</pre></li>" if isinstance(label, dict) else f"<li>{esc(label)}</li>")
        else:
            rows.append(f"<li>{esc(item)}</li>")
    return "<ul>" + "".join(rows) + "</ul>" if rows else "<p class=\"muted\">暂无</p>"


def render_table(rows: Sequence[Mapping[str, Any]], columns: Sequence[tuple[str, str]]) -> str:
    if not rows:
        return "<p class=\"muted\">暂无</p>"
    head = "".join(f"<th>{html.escape(label)}</th>" for _, label in columns)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{render_table_cell(key, row.get(key, ''))}</td>" for key, _ in columns)
        body_rows.append(f"<tr>{cells}</tr>")
    return f"<div class=\"table-wrap\"><table><thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table></div>"


def render_table_cell(key: str, value: Any) -> str:
    if key == "url":
        url = text(value).strip()
        if not url:
            return "-"
        if url.startswith(("https://", "http://")):
            return f'<a class="source-link" href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">查看原文</a>'
    return esc(value)


LABELS = {
    "segment": "环节",
    "role": "角色/能力",
    "analysis": "分析",
    "priority": "优先级",
    "reason": "原因",
    "step": "步骤",
    "detail": "说明",
    "enterprise": "企业",
    "available": "可用证据",
    "empty": "空数据",
    "warning": "上游警告",
    "error": "错误",
    "products": "证据产品",
    "product": "证据产品",
    "status": "状态",
    "signal_strength": "信号强度",
    "matched_keywords": "命中关键词",
    "key_findings": "关键发现",
    "data_points": "数据点",
    "recall_total": "召回总量",
    "sample_size": "抽样数量",
    "confirmed": "确认挂链",
    "uncertain": "待复核",
    "rejected": "建议剔除",
    "evidence_company_count": "证据企业数",
    "data_mode": "数据模式",
    "canonical_chain_name": "项目产业链",
    "chain_id": "产业链ID",
    "source": "来源",
    "source_type": "来源类型",
    "node_count": "节点数",
    "enterprise_count_cache": "候选企业缓存",
    "updated_at": "更新时间",
    "l2_count": "L2数量",
    "l3_count": "L3数量",
    "l5_count": "L5数量",
    "composite_sources": "组合复用图谱",
    "input_chain": "输入产业链",
    "canonical_chain": "项目产业链",
    "input_node": "输入节点",
    "mapped_project_nodes": "映射项目节点",
    "primary_project_path": "主映射路径",
    "mapping_note": "映射说明",
    "l2_segment": "L2价值环节",
    "l3_segments": "L3产业环节",
    "l5_samples": "L5节点样例",
    "node_name": "节点名称",
    "path": "节点路径",
    "condition_source": "条件组来源",
    "condition_keywords": "条件关键词",
    "link_count": "候选挂链数",
    "node_id": "节点ID",
    "evidence_level": "证据级别",
    "target_node": "目标节点",
    "recommended_link": "挂链建议",
    "decision": "判断",
    "evidence_strength": "证据强度",
    "fit_score": "匹配分",
    "next_action": "下一步",
    "name": "企业名称",
    "id_or_keyword": "ID/关键词",
    "oper_status": "经营状态",
    "address": "地址",
    "business_scope": "经营范围",
    "profile": "企业简介",
    "industry_boundary": "产业边界",
    "commercial_focus": "商业重点",
    "evidence_logic": "证据逻辑",
    "hierarchy_logic": "层级逻辑",
    "analysis_focus": "分析重点",
    "enterprise_boundary": "企业边界",
    "dimension": "分析维度",
    "level": "层级",
    "definition": "定义口径",
    "granularity": "颗粒度",
    "this_report": "本报告口径",
    "usage": "使用说明",
    "bad_markers": "异常标记",
    "warnings": "警告",
    "note": "说明",
    "topic": "主题",
    "finding": "产业背景要点",
    "url": "链接",
    "date": "日期",
}


def label(key: str) -> str:
    return LABELS.get(str(key), str(key).replace("_", " "))


def render_kv_grid(data: Mapping[str, Any]) -> str:
    if not data:
        return "<p class=\"muted\">暂无</p>"
    rows = []
    for key, value in data.items():
        rows.append(f"<div class=\"kv\"><div class=\"kv-label\">{html.escape(label(str(key)))}</div><div class=\"kv-value\">{esc(value)}</div></div>")
    return "<div class=\"kv-grid\">" + "".join(rows) + "</div>"


def table_columns_from_rows(rows: Sequence[Mapping[str, Any]]) -> List[tuple[str, str]]:
    keys: List[str] = []
    for row in rows:
        for key in row.keys():
            if key not in keys:
                keys.append(str(key))
    return [(key, label(key)) for key in keys]


def render_generic_table(rows: Sequence[Any]) -> str:
    normalized: List[Dict[str, Any]] = []
    for item in rows:
        if isinstance(item, dict):
            normalized.append(item)
        else:
            normalized.append({"value": item})
    return render_table(normalized, table_columns_from_rows(normalized)) if normalized else "<p class=\"muted\">暂无</p>"


def normalize_graph_tree(data: Mapping[str, Any]) -> Dict[str, Any]:
    tree = data.get("project_graph_tree")
    if isinstance(tree, dict) and tree.get("children"):
        return tree
    chain = str(data.get("chain") or data.get("industry") or "产业链")
    sections: List[Dict[str, Any]] = []
    for item in as_list(data.get("project_value_chain") or data.get("value_chain")):
        if not isinstance(item, dict):
            continue
        l2 = str(item.get("l2_segment") or item.get("segment") or "").strip()
        if not l2:
            continue
        l3_names = [part.strip() for part in str(item.get("l3_segments") or item.get("role") or "").split("、") if part.strip()]
        l5_names = [part.strip() for part in str(item.get("l5_samples") or "").split("、") if part.strip()]
        children: List[Dict[str, Any]] = []
        if l3_names:
            for index, l3 in enumerate(l3_names):
                children.append({"name": l3, "children": [{"name": name} for name in l5_names[index:index + 4]]})
        elif l5_names:
            children.append({"name": "核心节点", "children": [{"name": name} for name in l5_names]})
        sections.append({"name": l2, "children": children})
    return {"name": chain, "children": sections} if sections else {}


def graph_stats(tree: Mapping[str, Any]) -> Dict[str, int]:
    l2 = len(as_list(tree.get("children")))
    l3 = 0
    l5 = 0
    for section in as_list(tree.get("children")):
        if not isinstance(section, dict):
            continue
        subsections = as_list(section.get("children"))
        l3 += len(subsections)
        for sub in subsections:
            if isinstance(sub, dict):
                l5 += len(as_list(sub.get("children")))
    return {"l2": l2, "l3": l3, "l5": l5}


def render_project_graph_html(data: Mapping[str, Any]) -> str:
    tree = normalize_graph_tree(data)
    sections = [item for item in as_list(tree.get("children")) if isinstance(item, dict)]
    if not sections:
        return ""
    stats = graph_stats(tree)
    chain = str(tree.get("name") or data.get("chain") or "产业链")
    column_count = 2 if len(sections) > 1 else 1
    themes = ["blue", "emerald", "violet", "amber", "rose"]
    hierarchy = [
        ("L1", "产业链"),
        ("L2", "价值环节"),
        ("L3", "产业模块"),
        ("L4", "可选细分方向"),
        ("L5", "产品技术 / 服务能力"),
    ]
    hierarchy_html = "".join(
        f'<span class="graph-badge"><span>{esc(level)}</span> · {esc(label_text)}</span>'
        for level, label_text in hierarchy
    )
    cards: List[str] = []
    for index, section in enumerate(sections):
        theme = themes[index % len(themes)]
        subsections = [item for item in as_list(section.get("children")) if isinstance(item, dict)]
        l5_count = sum(len(as_list(sub.get("children"))) for sub in subsections)
        l3_html: List[str] = []
        for sub in subsections:
            leaves = [leaf for leaf in as_list(sub.get("children")) if isinstance(leaf, dict)]
            leaf_html = "".join(
                f'<div class="graph-l5" title="{esc(leaf.get("name"))}"><span>{esc(leaf.get("name"))}</span></div>'
                for leaf in leaves
            ) or '<p class="graph-empty">暂无 L5 节点</p>'
            l3_html.append(f"""
                <article class="graph-l3 graph-l3-{theme}">
                  <div class="graph-l3-head">
                    <span class="graph-dot graph-dot-{theme}"></span>
                    <h4 title="{esc(sub.get('name'))}">{esc(sub.get('name'))}</h4>
                    <span class="graph-count">{len(leaves)} L5</span>
                  </div>
                  <div class="graph-l5-grid">{leaf_html}</div>
                </article>
            """)
        cards.append(f"""
            <section class="graph-l2 graph-l2-{theme}">
              <div class="graph-l2-head graph-l2-head-{theme}">
                <h3 title="{esc(section.get('name'))}">{esc(section.get('name'))}</h3>
                <span>{len(subsections)} L3 · {l5_count} L5</span>
              </div>
              <div class="graph-l3-stack">{''.join(l3_html)}</div>
            </section>
        """)
    return f"""
    <section class="graph-showcase">
      <div class="graph-topbar">
        <div>
          <p class="graph-kicker">Construction result</p>
          <h2>{esc(chain)}产业链图谱</h2>
          <p class="graph-desc">按 L2/L3/L5 展开产业链标准节点，呈现价值环节、产业模块与产品技术节点之间的层级关系。</p>
        </div>
        <div class="graph-stats">
          <div class="graph-stat"><strong>{stats['l2']}</strong><span>价值环节</span></div>
          <div class="graph-stat"><strong>{stats['l3']}</strong><span>产业模块</span></div>
          <div class="graph-stat"><strong>{stats['l5']}</strong><span>产品技术节点</span></div>
        </div>
      </div>
      <div class="graph-hierarchy">{hierarchy_html}</div>
      <div class="graph-scroll">
        <div class="graph-grid" style="grid-template-columns: repeat({column_count}, minmax(0, 1fr));">
          {''.join(cards)}
        </div>
      </div>
    </section>
    """


def render_professional_sections_html(data: Mapping[str, Any]) -> str:
    sections: List[str] = []

    def card(title: str, body: str, tag: str | None = None) -> None:
        tag_html = f"<span class=\"tag\">{html.escape(tag)}</span>" if tag else ""
        sections.append(f"<section class=\"card\"><div class=\"section-title\"><h2>{html.escape(title)}</h2>{tag_html}</div>{body}</section>")

    if data.get("executive_summary"):
        card("执行摘要", render_html_list(as_list(data.get("executive_summary"))), "Executive")
    if data.get("professional_opinion"):
        card("专业判断", render_html_list(as_list(data.get("professional_opinion"))), "Opinion")
    if isinstance(data.get("industry_overview"), dict):
        card("产业边界与分析逻辑", render_kv_grid(data["industry_overview"]), "Industry")
    if data.get("level_definitions"):
        card("L1-L5 层级口径说明", render_generic_table(as_list(data.get("level_definitions"))), "Level Rules")
    if isinstance(data.get("project_graph_summary"), dict) and data.get("project_graph_summary"):
        card("项目图谱口径", render_kv_grid(data["project_graph_summary"]), "Project Graph")
    if isinstance(data.get("node_mapping"), dict) and data.get("node_mapping"):
        card("项目节点映射", render_kv_grid(data["node_mapping"]), "Node Mapping")
    graph_html = render_project_graph_html(data)
    if graph_html:
        sections.append(graph_html)
    if data.get("value_chain"):
        card("产业链结构", render_generic_table(as_list(data.get("value_chain"))), "Value Chain")
    if data.get("project_node_records"):
        card("项目节点数据记录", render_generic_table(as_list(data.get("project_node_records"))), "Node Records")
    if data.get("hierarchy_analysis"):
        card("层级结构分析", render_generic_table(as_list(data.get("hierarchy_analysis"))), "Hierarchy")
    if data.get("analysis_framework"):
        card("分析框架", render_generic_table(as_list(data.get("analysis_framework"))), "Framework")
    if data.get("key_observations"):
        card("关键观察", render_html_list(as_list(data.get("key_observations"))), "Observations")
    if data.get("project_seed_links"):
        card("项目已有候选挂链/锚点", render_generic_table(as_list(data.get("project_seed_links"))), "Existing Links")
    if isinstance(data.get("link_summary"), dict) and data.get("link_summary"):
        card("挂链总览", render_kv_grid(data["link_summary"]), "Linking")
    if isinstance(data.get("fit_assessment"), dict):
        card("企业-节点匹配评估", render_kv_grid(data["fit_assessment"]), "Fit")
    if isinstance(data.get("enterprise_profile"), dict):
        card("指定企业画像", render_kv_grid(data["enterprise_profile"]), "Enterprise")
    if data.get("evidence_summary"):
        card("证据摘要", render_generic_table(as_list(data.get("evidence_summary"))), "Evidence")
    if isinstance(data.get("data_quality"), dict):
        card("数据质量与接口状态", render_kv_grid(data["data_quality"]), "Data Quality")
    if data.get("risk_flags"):
        card("风险与复核点", render_html_list(as_list(data.get("risk_flags"))), "Risk")
    if data.get("recommendations"):
        card("专业建议", render_html_list(as_list(data.get("recommendations"))), "Recommendations")
    return "\n".join(sections)



def render_commercial_cards(rows: Sequence[Any], title_key: str = "segment", body_key: str = "reason") -> str:
    cards: List[str] = []
    for item in rows:
        if isinstance(item, dict):
            title = item.get(title_key) or item.get("level") or item.get("name") or item.get("dimension") or "要点"
            body = item.get(body_key) or item.get("analysis") or item.get("definition") or item.get("detail") or item
            meta = item.get("priority") or item.get("granularity") or item.get("this_report") or ""
            cards.append(f"""
            <article class="biz-mini-card">
              <div class="biz-mini-meta">{esc(meta)}</div>
              <h3>{esc(title)}</h3>
              <p>{esc(body)}</p>
            </article>
            """)
        else:
            cards.append(f"<article class=\"biz-mini-card\"><h3>要点</h3><p>{esc(item)}</p></article>")
    return "<div class=\"biz-card-grid\">" + "".join(cards) + "</div>" if cards else "<p class=\"muted\">暂无</p>"


def render_segment_analysis_html(rows: Sequence[Any]) -> str:
    cards: List[str] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        cards.append(f"""
        <article class="segment-analysis-card">
          <div class="segment-analysis-head">
            <span class="segment-stage">{esc(item.get('stage') or '产业环节')}</span>
            <h3>{esc(item.get('segment') or '价值环节')}</h3>
            <span class="segment-scale">{esc(item.get('scale') or '')}</span>
          </div>
          <p class="segment-positioning">{esc(item.get('functional_positioning') or '')}</p>
          <dl class="segment-detail-list">
            <div><dt>产业模块</dt><dd>{esc(item.get('composition') or '-')}</dd></div>
            <div><dt>代表性节点</dt><dd>{esc(item.get('representative_nodes') or '-')}</dd></div>
            <div><dt>上下游关系</dt><dd>{esc(item.get('linkage') or '-')}</dd></div>
          </dl>
        </article>
        """)
    return '<div class="segment-analysis-grid">' + "".join(cards) + "</div>" if cards else '<p class="muted">暂无</p>'


def render_value_flow_html(rows: Sequence[Any]) -> str:
    items: List[str] = []
    for index, item in enumerate(rows):
        if not isinstance(item, dict):
            continue
        items.append(f"""
        <article class="value-flow-item">
          <div class="value-flow-index">{index + 1:02d}</div>
          <div class="value-flow-route">
            <strong>{esc(item.get('from_segment') or '-')}</strong>
            <span class="value-flow-relation">{esc(item.get('relationship') or '价值承接')}</span>
            <strong>{esc(item.get('to_segment') or '-')}</strong>
          </div>
          <div class="value-flow-content"><span>传导内容</span><p>{esc(item.get('transmission_content') or '-')}</p></div>
          <div class="value-flow-logic"><span>传导机制</span><p>{esc(item.get('transmission_logic') or '-')}</p></div>
        </article>
        """)
    return '<div class="value-flow-list">' + "".join(items) + "</div>" if items else '<p class="muted">暂无</p>'


def render_structural_features_html(rows: Sequence[Any]) -> str:
    cards: List[str] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        cards.append(f"""
        <article class="structural-feature-card">
          <h3>{esc(item.get('feature') or '结构特征')}</h3>
          <p class="structural-evidence">{esc(item.get('evidence') or '')}</p>
          <p>{esc(item.get('interpretation') or '')}</p>
        </article>
        """)
    return '<div class="structural-feature-grid">' + "".join(cards) + "</div>" if cards else '<p class="muted">暂无</p>'


def render_chain_analysis_html(data: Dict[str, Any], title: str) -> str:
    generated_at = dt.datetime.now().strftime("%Y-%m-%d")
    summary = first_present(data, ["abstract", "summary", "overview"], "")
    chain = str(data.get("chain") or data.get("industry") or "产业链")
    node = str(data.get("node") or "全产业链")
    graph_summary = data.get("project_graph_summary") if isinstance(data.get("project_graph_summary"), dict) else {}
    industry_definition = [item for item in as_list(data.get("industry_definition")) if isinstance(item, dict)]
    level_definitions = as_list(data.get("level_definitions"))
    segment_rows = [item for item in as_list(data.get("segment_analysis")) if isinstance(item, dict)]
    key_node_rows = [item for item in as_list(data.get("key_node_system")) if isinstance(item, dict)]
    value_flow_rows = [item for item in as_list(data.get("value_flow")) if isinstance(item, dict)]
    structural_rows = [item for item in as_list(data.get("structural_characteristics")) if isinstance(item, dict)]
    market_context = [item for item in as_list(data.get("market_context")) if isinstance(item, dict)]
    graph_html = render_project_graph_html(data)
    definition_columns = [("dimension", "定义维度"), ("content", "本报告界定")]
    level_columns = [("level", "层级"), ("name", "层级名称"), ("definition", "定义口径"), ("granularity", "颗粒度"), ("this_report", "本报告口径"), ("usage", "使用说明")]
    market_columns = [("topic", "主题"), ("finding", "产业背景要点"), ("source", "来源"), ("date", "日期"), ("url", "链接")]
    key_node_columns = [("l2_segment", "L2 价值环节"), ("l3_module", "L3 产业模块"), ("node_count", "L5 数量"), ("capability_boundary", "能力边界"), ("representative_nodes", "代表性 L5 节点")]
    cn_nums = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
    section_index = 0
    def next_heading(title_text: str) -> str:
        nonlocal section_index
        label_text = cn_nums[section_index] if section_index < len(cn_nums) else str(section_index + 1)
        section_index += 1
        return f"{label_text}、{title_text}"
    heading_summary = next_heading("报告摘要")
    heading_definition = next_heading("产业定义与层级口径")
    market_section = ""
    if market_context:
        heading_market = next_heading("产业发展环境")
        market_section = f'''<section class="report-page biz-section"><div class="report-topbar"><div class="report-stripe"></div><div class="report-banner">产业链分析报告</div></div><div class="biz-section-head"><div><h2>{heading_market}</h2><p class="biz-section-note">梳理政策导向、市场演进与技术路线，说明产业发展的外部环境和关键影响因素。</p></div><span class="biz-tag">Industry Context</span></div>{render_table(market_context, market_columns)}</section>'''
    heading_graph = next_heading("产业链全景图谱")
    heading_segments = next_heading("价值环节深度解析")
    heading_nodes = next_heading("关键节点与产品技术体系")
    heading_flow = next_heading("价值传导与协同关系")
    heading_structure = next_heading("产业结构特征")
    report_scope = [
        {"name": "分析对象", "value": chain},
        {"name": "关注节点", "value": node},
        {"name": "图谱规模", "value": f"L2 {graph_summary.get('l2_count', '-')} / L3 {graph_summary.get('l3_count', '-')} / L5 {graph_summary.get('l5_count', '-')}"},
        {"name": "层级体系", "value": "L1 产业主题 / L2 价值环节 / L3 产业模块 / L4 细分方向 / L5 标准节点"},
    ]
    scope_html = "".join(f"<div class=\"biz-scope-item\"><span>{esc(item['name'])}</span><strong>{esc(item['value'])}</strong></div>" for item in report_scope)
    toc_items = [heading_summary, heading_definition]
    if market_context:
        toc_items.append(heading_market)
    toc_items.extend([heading_graph, heading_segments, heading_nodes, heading_flow, heading_structure])
    toc_html = "".join(f"<li><span>{esc(item)}</span></li>" for item in toc_items)
    source_note = "产业图谱 + 政策及行业资料" if market_context else "产业图谱"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="icon" href="data:," />
  <title>{esc(title)}</title>
  <style>
    :root {{ --bg:#eef1f5; --card:#ffffff; --text:#1f2937; --muted:#64748b; --line:#d8dee8; --blue:#003b71; --deep:#003b71; --red:#7f1d1d; --gold:#d97706; --stripe:#666; }}
    * {{ box-sizing:border-box; letter-spacing:0 !important; }}
    body {{ margin:0; background:var(--bg); color:var(--text); font-family:"Songti SC","STSong","Noto Serif CJK SC","Source Han Serif SC","SimSun",serif; line-height:1.78; }}
    .research-doc {{ width:min(1120px,100%); margin:0 auto 42px; padding:0 22px; }}
    .report-page {{ position:relative; width:min(1080px,calc(100vw - 32px)); margin:28px auto; background:#fff; border:1px solid #a8adb5; box-shadow:0 18px 44px rgba(15,23,42,.13); }}
    .report-topbar {{ display:flex; align-items:stretch; height:54px; border-bottom:1px solid #333; }}
    .report-stripe {{ flex:1; background:repeating-linear-gradient(0deg,#575757 0,#575757 2px,#747474 2px,#747474 4px); }}
    .report-banner {{ width:420px; display:flex; align-items:center; justify-content:flex-end; padding:0 24px; color:#fff; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; font-weight:800; letter-spacing:.08em; background:linear-gradient(135deg,#0b4c84,#0284c7 48%,#0b2f55); }}
    .cover-grid {{ display:grid; grid-template-columns:330px minmax(0,1fr); min-height:860px; }}
    .cover-side {{ padding:86px 34px 42px; border-right:0; }}
    .cover-side-title {{ color:var(--red); font-size:32px; font-weight:800; letter-spacing:.08em; margin:0 0 12px; }}
    .cover-date {{ margin:0 0 60px; color:#111827; font-size:17px; font-weight:700; }}
    .toc-title,.scope-title {{ margin:0 0 12px; color:#111827; font-size:19px; font-weight:800; border-bottom:2px solid var(--red); padding-bottom:8px; }}
    .toc-list {{ list-style:none; padding:0; margin:0 0 56px; }}
    .toc-list li {{ border-bottom:1px solid #e5e7eb; padding:9px 0; color:#475569; font-size:14px; }}
    .toc-list span {{ display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
    .cover-brand {{ position:absolute; left:38px; bottom:38px; color:#7a7a7a; font-size:28px; font-weight:900; letter-spacing:.02em; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }}
    .cover-main {{ padding:72px 54px 54px 34px; }}
    .report-kicker {{ margin:0 0 16px; color:var(--deep); font-size:16px; font-weight:800; letter-spacing:.16em; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }}
    h1 {{ margin:0 0 20px; color:#0b3768; font-size:36px; line-height:1.25; letter-spacing:-.03em; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }}
    .report-lead {{ margin:0 0 22px; color:#0b3768; font-size:19px; line-height:1.85; font-weight:800; }}
    .abstract-box {{ border-left:5px solid var(--gold); background:#fff8eb; padding:16px 18px; color:#9a4b00; font-size:17px; line-height:1.8; font-style:italic; margin:22px 0 24px; }}
    .biz-subtitle {{ margin:18px 0 0; max-width:880px; color:#dbeafe; font-size:15px; }}
    .biz-metrics {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; margin:22px 0; }}
    .biz-metric {{ border:1px solid #cbd5e1; border-radius:0; background:#f8fbff; padding:14px; }}
    .biz-metric strong {{ display:block; color:#0b3768; font-size:25px; line-height:1; letter-spacing:-.03em; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }}
    .biz-metric span {{ display:block; margin-top:7px; color:#475569; font-size:12px; font-weight:800; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }}
    .biz-section {{ border:0; border-radius:0; background:white; padding:30px; margin-bottom:24px; box-shadow:none; }}
    .report-page.biz-section {{ padding:0 30px 34px; }}
    .report-page.biz-section > .report-topbar {{ margin:0 -30px 30px; }}
    .biz-section-head {{ display:flex; justify-content:space-between; gap:16px; align-items:flex-start; margin-bottom:18px; }}
    .biz-section h2 {{ margin:0; color:#0b3768; font-size:26px; letter-spacing:.03em; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }}
    .biz-section-note {{ margin:6px 0 0; color:var(--muted); font-size:13px; }}
    .biz-tag {{ border-radius:0; background:#eaf4ff; color:#0b3768; padding:5px 10px; font-size:12px; font-weight:800; white-space:nowrap; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }}
    .biz-summary {{ font-size:16px; color:#243041; text-align:justify; }}
    .biz-scope {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; margin-top:18px; }}
    .cover-side .biz-scope {{ grid-template-columns:1fr; }}
    .biz-scope-item {{ border:1px solid #d6dee9; border-radius:0; background:#f8fbff; padding:12px; }}
    .biz-scope-item span {{ display:block; color:#64748b; font-size:12px; font-weight:700; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }}
    .biz-scope-item strong {{ display:block; margin-top:4px; color:#0b3768; font-size:13px; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }}
    .biz-card-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:14px; }}
    .biz-mini-card {{ border:1px solid #d6dee9; border-radius:0; background:#fbfdff; padding:16px; }}
    .biz-mini-meta {{ min-height:18px; color:#2563eb; font-size:11px; font-weight:800; letter-spacing:.04em; }}
    .biz-mini-card h3 {{ margin:6px 0 8px; font-size:16px; letter-spacing:-.02em; }}
    .biz-mini-card p {{ margin:0; color:#475569; font-size:13px; }}
    .biz-subsection-title {{ margin:26px 0 12px; padding-left:12px; border-left:4px solid #0b5ca8; color:#0b3768; font-size:18px; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }}
    .segment-analysis-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }}
    .segment-analysis-card {{ border:1px solid #cbd5e1; border-top:4px solid #0b5ca8; background:#fff; padding:16px; }}
    .segment-analysis-head {{ display:grid; grid-template-columns:auto minmax(0,1fr) auto; gap:10px; align-items:center; }}
    .segment-analysis-head h3 {{ margin:0; color:#0b3768; font-size:17px; line-height:1.35; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }}
    .segment-stage {{ display:inline-flex; align-items:center; justify-content:center; min-width:42px; height:26px; background:#0b3768; color:#fff; font-size:11px; font-weight:800; }}
    .segment-scale {{ color:#64748b; font-size:11px; font-weight:800; white-space:nowrap; }}
    .segment-positioning {{ margin:14px 0; color:#334155; font-size:13px; line-height:1.75; }}
    .segment-detail-list {{ display:grid; gap:9px; margin:0; }}
    .segment-detail-list div {{ display:grid; grid-template-columns:76px minmax(0,1fr); gap:10px; border-top:1px solid #e2e8f0; padding-top:9px; }}
    .segment-detail-list dt {{ color:#0b5ca8; font-size:11px; font-weight:800; }}
    .segment-detail-list dd {{ margin:0; color:#475569; font-size:12px; line-height:1.65; }}
    .value-flow-list {{ display:grid; gap:12px; }}
    .value-flow-item {{ display:grid; grid-template-columns:48px minmax(220px,.8fr) minmax(180px,.7fr) minmax(260px,1fr); gap:14px; align-items:stretch; border:1px solid #cbd5e1; background:#fff; padding:14px; }}
    .value-flow-index {{ display:flex; align-items:center; justify-content:center; background:#0b3768; color:#fff; font-size:16px; font-weight:900; }}
    .value-flow-route {{ display:flex; flex-direction:column; justify-content:center; gap:6px; }}
    .value-flow-route strong {{ color:#0b3768; font-size:13px; line-height:1.45; }}
    .value-flow-relation {{ align-self:flex-start; border-left:3px solid #d97706; padding-left:8px; color:#9a4b00; font-size:11px; font-weight:800; }}
    .value-flow-content,.value-flow-logic {{ border-left:1px solid #e2e8f0; padding-left:14px; }}
    .value-flow-content span,.value-flow-logic span {{ color:#64748b; font-size:10px; font-weight:800; }}
    .value-flow-content p,.value-flow-logic p {{ margin:5px 0 0; color:#334155; font-size:12px; line-height:1.65; }}
    .structural-feature-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }}
    .structural-feature-card {{ border:1px solid #cbd5e1; background:#fff; padding:16px; }}
    .structural-feature-card h3 {{ margin:0 0 10px; color:#0b3768; font-size:17px; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }}
    .structural-feature-card p {{ margin:8px 0 0; color:#475569; font-size:13px; line-height:1.7; }}
    .structural-feature-card .structural-evidence {{ border-left:4px solid #d97706; background:#fff8eb; padding:9px 11px; color:#92400e; font-weight:700; }}
    .table-wrap {{ overflow:auto; border:1px solid #0b3768; border-radius:0; }}
    table {{ width:100%; border-collapse:collapse; background:white; }}
    th,td {{ padding:12px 13px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; font-size:13px; overflow-wrap:anywhere; }}
    th {{ background:#0b3768; color:white; font-weight:800; white-space:nowrap; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }}
    tbody tr:nth-child(even) td {{ background:#dff1fb; }}
    tr:last-child td {{ border-bottom:0; }}
    .source-link {{ color:#0b5ca8; font-weight:800; text-decoration:none; white-space:nowrap; }}
    ul {{ margin:0 0 0 20px; padding:0; }} li {{ margin:7px 0; }}
    .muted {{ color:var(--muted); }}
    .graph-showcase {{ overflow:hidden; border:1px solid #e2e8f0; border-radius:24px; background:#fff; box-shadow:0 12px 32px rgba(15,23,42,.08); margin:0; }}
    .graph-topbar {{ display:flex; justify-content:space-between; gap:24px; align-items:flex-end; padding:24px; border-bottom:1px solid #e2e8f0; background:#fff; }}
    .graph-kicker {{ margin:0; color:#2563eb; font-size:11px; font-weight:800; letter-spacing:.22em; text-transform:uppercase; }}
    .graph-topbar h2 {{ margin:8px 0 0; color:#020617; font-size:28px; letter-spacing:-.04em; }}
    .graph-desc {{ margin:8px 0 0; max-width:760px; color:#64748b; font-size:13px; line-height:1.7; }}
    .graph-stats {{ display:grid; grid-template-columns:repeat(3,minmax(92px,1fr)); gap:8px; min-width:310px; }}
    .graph-stat {{ border:1px solid #e2e8f0; border-radius:16px; background:#f8fafc; padding:12px 14px; text-align:center; }}
    .graph-stat strong {{ display:block; color:#020617; font-size:22px; line-height:1; letter-spacing:-.04em; }}
    .graph-stat span {{ display:block; margin-top:5px; color:#64748b; font-size:11px; font-weight:700; }}
    .graph-hierarchy {{ display:flex; flex-wrap:wrap; gap:8px; padding:14px 24px 0; background:#f8fafc; }}
    .graph-badge {{ display:inline-flex; align-items:center; border:1px solid #e2e8f0; border-radius:999px; background:#fff; padding:5px 12px; color:#64748b; font-size:12px; font-weight:700; }}
    .graph-badge span {{ color:#2563eb; }}
    .graph-scroll {{ overflow:visible; padding:20px; background:#f8fafc; }}
    .graph-grid {{ display:grid; gap:16px; }}
    .graph-l2 {{ display:flex; min-width:0; flex-direction:column; overflow:hidden; border-radius:18px; border:1px solid; box-shadow:0 1px 2px rgba(15,23,42,.04), inset 0 0 0 1px rgba(255,255,255,.7); }}
    .graph-l2-blue {{ border-color:#bfdbfe; background:rgba(239,246,255,.75); }} .graph-l2-emerald {{ border-color:#a7f3d0; background:rgba(236,253,245,.75); }} .graph-l2-violet {{ border-color:#ddd6fe; background:rgba(245,243,255,.75); }} .graph-l2-amber {{ border-color:#fde68a; background:rgba(255,251,235,.75); }} .graph-l2-rose {{ border-color:#fecdd3; background:rgba(255,241,242,.75); }}
    .graph-l2-head {{ display:flex; align-items:center; justify-content:space-between; gap:12px; padding:13px 15px; border-bottom:1px solid; }}
    .graph-l2-head h3 {{ min-width:0; margin:0; font-size:17px; line-height:1.35; font-weight:800; }}
    .graph-l2-head span {{ flex-shrink:0; border-radius:999px; background:rgba(255,255,255,.82); padding:5px 9px; color:#475569; font-size:11px; font-weight:800; }}
    .graph-l2-head-blue {{ border-color:#bfdbfe; background:rgba(219,234,254,.72); color:#172554; }} .graph-l2-head-emerald {{ border-color:#a7f3d0; background:rgba(209,250,229,.72); color:#064e3b; }} .graph-l2-head-violet {{ border-color:#ddd6fe; background:rgba(237,233,254,.72); color:#2e1065; }} .graph-l2-head-amber {{ border-color:#fde68a; background:rgba(254,243,199,.72); color:#78350f; }} .graph-l2-head-rose {{ border-color:#fecdd3; background:rgba(255,228,230,.72); color:#881337; }}
    .graph-l3-stack {{ display:grid; align-content:start; gap:12px; padding:12px; }}
    .graph-l3 {{ min-width:0; border:1px solid; border-radius:14px; background:rgba(255,255,255,.9); }}
    .graph-l3-blue {{ border-color:#dbeafe; }} .graph-l3-emerald {{ border-color:#d1fae5; }} .graph-l3-violet {{ border-color:#ede9fe; }} .graph-l3-amber {{ border-color:#fef3c7; }} .graph-l3-rose {{ border-color:#ffe4e6; }}
    .graph-l3-head {{ display:flex; align-items:center; gap:8px; border-bottom:1px solid #f1f5f9; padding:10px 11px; }}
    .graph-dot {{ width:8px; height:8px; flex-shrink:0; border-radius:999px; }} .graph-dot-blue {{ background:#3b82f6; }} .graph-dot-emerald {{ background:#10b981; }} .graph-dot-violet {{ background:#8b5cf6; }} .graph-dot-amber {{ background:#f59e0b; }} .graph-dot-rose {{ background:#f43f5e; }}
    .graph-l3-head h4 {{ min-width:0; margin:0; color:#0f172a; font-size:13px; line-height:1.35; font-weight:800; }}
    .graph-count {{ margin-left:auto; flex-shrink:0; border-radius:999px; background:#f1f5f9; padding:3px 7px; color:#64748b; font-size:10px; font-weight:800; }}
    .graph-l5-grid {{ display:grid; grid-template-columns:1fr; gap:8px; padding:9px; }}
    .graph-l5 {{ min-width:0; border:1px solid rgba(203,213,225,.82); border-radius:10px; background:rgba(248,250,252,.78); padding:9px 10px; color:#334155; font-size:12px; font-weight:750; line-height:1.35; }}
    .graph-l5 span {{ display:block; overflow-wrap:anywhere; }}
    footer {{ width:min(1080px,100%); margin:0 auto; padding:0 24px 36px; color:#64748b; font-size:12px; }}
    @media (max-width: 860px) {{ .cover-grid {{ grid-template-columns:1fr; }} .cover-side {{ padding:34px; }} .cover-brand {{ position:static; margin-top:32px; }} .biz-metrics,.biz-scope {{ grid-template-columns:1fr 1fr; }} .table-wrap table {{ min-width:720px; }} .segment-analysis-grid,.structural-feature-grid {{ grid-template-columns:1fr; }} .value-flow-item {{ grid-template-columns:40px minmax(0,1fr); }} .value-flow-content,.value-flow-logic {{ grid-column:2; border-left:0; border-top:1px solid #e2e8f0; padding:9px 0 0; }} .graph-topbar {{ flex-direction:column; align-items:stretch; }} .graph-stats {{ min-width:0; }} .graph-grid {{ grid-template-columns:1fr !important; }} h1 {{ font-size:30px; }} .report-banner {{ width:55%; }} }}
    @page {{ size:A4; margin:12mm; }}
    @media print {{
      body {{ background:#fff; line-height:1.55; }}
      .report-page {{ width:100%; margin:0; box-shadow:none; break-after:page; }}
      .research-doc {{ width:100%; padding:0; margin:0; }}
      .cover-grid {{ grid-template-columns:190px minmax(0,1fr); min-height:690px; }}
      .cover-side {{ padding:34px 18px 24px; }}
      .cover-side-title {{ font-size:24px; }}
      .cover-date {{ margin-bottom:28px; font-size:13px; }}
      .toc-title,.scope-title {{ font-size:14px; padding-bottom:5px; }}
      .toc-list {{ margin-bottom:24px; }}
      .toc-list li {{ padding:5px 0; font-size:10px; }}
      .cover-side .biz-scope {{ gap:5px; }}
      .biz-scope-item {{ padding:7px; }}
      .biz-scope-item span {{ font-size:8px; }}
      .biz-scope-item strong {{ font-size:9px; }}
      .cover-brand {{ left:20px; bottom:20px; font-size:18px; }}
      .cover-main {{ padding:38px 28px 28px 22px; }}
      .report-kicker {{ margin-bottom:10px; font-size:11px; }}
      h1 {{ margin-bottom:12px; font-size:27px; }}
      .report-lead {{ margin-bottom:12px; font-size:12px; line-height:1.65; }}
      .abstract-box {{ margin:12px 0 14px; padding:10px 12px; font-size:10px; line-height:1.55; }}
      .biz-metrics {{ gap:6px; margin:12px 0; }}
      .biz-metric {{ padding:8px; }}
      .biz-metric strong {{ font-size:16px; }}
      .biz-metric span {{ margin-top:4px; font-size:8px; }}
      .report-page.biz-section {{ padding:0 18px 22px; }}
      .report-page.biz-section > .report-topbar {{ margin:0 -18px 18px; }}
      .biz-section-head {{ margin-bottom:12px; }}
      .biz-section h2 {{ font-size:20px; }}
      .biz-section-note,.biz-tag {{ font-size:9px; }}
      .table-wrap {{ overflow:visible; }}
      .table-wrap table {{ min-width:0 !important; }}
      th,td {{ padding:6px 7px; font-size:8.5px; line-height:1.45; }}
      .graph-showcase {{ overflow:visible; border-radius:6px; box-shadow:none; }}
      .graph-topbar {{ flex-direction:row; align-items:flex-end; gap:12px; padding:14px; }}
      .graph-topbar h2 {{ font-size:20px; }}
      .graph-desc {{ font-size:9px; }}
      .graph-stats {{ min-width:220px; }}
      .graph-stat {{ border-radius:6px; padding:7px; }}
      .graph-stat strong {{ font-size:15px; }}
      .graph-stat span {{ font-size:8px; }}
      .graph-hierarchy {{ gap:4px; padding:8px 14px 0; }}
      .graph-badge {{ border-radius:6px; padding:3px 6px; font-size:8px; }}
      .graph-scroll {{ padding:10px; }}
      .graph-grid {{ display:block; }}
      .graph-l2 {{ break-inside:avoid; border-radius:6px; margin-bottom:10px; }}
      .graph-l2-head {{ padding:7px 9px; }}
      .graph-l2-head h3 {{ font-size:12px; }}
      .graph-l2-head span {{ border-radius:5px; padding:3px 5px; font-size:8px; }}
      .graph-l3-stack {{ gap:6px; padding:6px; }}
      .graph-l3 {{ border-radius:5px; }}
      .graph-l3-head {{ padding:5px 6px; }}
      .graph-l3-head h4 {{ font-size:9px; }}
      .graph-count {{ border-radius:4px; padding:2px 4px; font-size:7px; }}
      .graph-l5-grid {{ gap:3px; padding:4px; }}
      .graph-l5 {{ border-radius:4px; padding:3px 5px; font-size:7.5px; line-height:1.25; }}
      .segment-analysis-card,.value-flow-item,.structural-feature-card {{ break-inside:avoid; }}
      .segment-analysis-grid,.structural-feature-grid {{ gap:8px; }}
      .segment-analysis-card,.structural-feature-card {{ padding:10px; }}
      .segment-positioning,.structural-feature-card p {{ font-size:9px; line-height:1.45; }}
      .segment-detail-list dd,.value-flow-content p,.value-flow-logic p {{ font-size:8px; line-height:1.4; }}
      .value-flow-item {{ grid-template-columns:32px minmax(150px,.8fr) minmax(120px,.7fr) minmax(180px,1fr); gap:8px; padding:8px; }}
      footer {{ display:none; }}
    }}
  </style>
</head>
<body>
  <article class="report-page">
    <div class="report-topbar"><div class="report-stripe"></div><div class="report-banner">旷湖产业链分析</div></div>
    <div class="cover-grid">
      <aside class="cover-side">
        <h2 class="cover-side-title">行业展望</h2>
        <p class="cover-date">{esc(generated_at)}</p>
        <h3 class="toc-title">目录</h3>
        <ol class="toc-list">{toc_html}</ol>
        <h3 class="scope-title">报告口径</h3>
        <div class="biz-scope">{scope_html}</div>
        <div class="cover-brand">KUANGHU</div>
      </aside>
      <section class="cover-main">
        <p class="report-kicker">INDUSTRY CHAIN RESEARCH</p>
        <h1>{esc(title)}</h1>
        <p class="report-lead">{esc(summary)}</p>
        <div class="abstract-box">报告以产业层级为主线，系统呈现节点边界、价值传导关系与关键结构特征。</div>
        <section class="biz-metrics">
          <div class="biz-metric"><strong>{esc(graph_summary.get('l2_count','-'))}</strong><span>L2 价值环节</span></div>
          <div class="biz-metric"><strong>{esc(graph_summary.get('l3_count','-'))}</strong><span>L3 产业模块</span></div>
          <div class="biz-metric"><strong>{esc(graph_summary.get('l5_count','-'))}</strong><span>L5 标准节点</span></div>
          <div class="biz-metric"><strong>{esc(source_note)}</strong><span>分析依据</span></div>
        </section>
      </section>
    </div>
  </article>
  <main class="research-doc">
    <section class="report-page biz-section"><div class="report-topbar"><div class="report-stripe"></div><div class="report-banner">产业链分析报告</div></div><div class="biz-section-head"><div><h2>{heading_definition}</h2><p class="biz-section-note">明确产业对象、价值边界和层级体系，为后续环节与节点分析建立统一定义。</p></div><span class="biz-tag">Industry Definition</span></div>{render_table(industry_definition, definition_columns)}<h3 class="biz-subsection-title">L1-L5 层级定义</h3>{render_table([row for row in level_definitions if isinstance(row, dict)], level_columns)}</section>
    {market_section}
    <section class="report-page biz-section"><div class="report-topbar"><div class="report-stripe"></div><div class="report-banner">产业链分析报告</div></div><div class="biz-section-head"><div><h2>{heading_graph}</h2><p class="biz-section-note">按照 L2 价值环节、L3 产业模块和 L5 标准节点呈现产业链总体结构。</p></div><span class="biz-tag">Industry Map</span></div>{graph_html}</section>
    <section class="report-page biz-section"><div class="report-topbar"><div class="report-stripe"></div><div class="report-banner">产业链分析报告</div></div><div class="biz-section-head"><div><h2>{heading_segments}</h2><p class="biz-section-note">分析各价值环节的功能定位、模块构成、代表性节点和上下游承接关系。</p></div><span class="biz-tag">Segment Analysis</span></div>{render_segment_analysis_html(segment_rows)}</section>
    <section class="report-page biz-section"><div class="report-topbar"><div class="report-stripe"></div><div class="report-banner">产业链分析报告</div></div><div class="biz-section-head"><div><h2>{heading_nodes}</h2><p class="biz-section-note">以 L3 产业模块为单位，界定能力边界并展示代表性 L5 产品技术节点。</p></div><span class="biz-tag">Node System</span></div>{render_table(key_node_rows, key_node_columns)}</section>
    <section class="report-page biz-section"><div class="report-topbar"><div class="report-stripe"></div><div class="report-banner">产业链分析报告</div></div><div class="biz-section-head"><div><h2>{heading_flow}</h2><p class="biz-section-note">说明基础供给、系统协同与场景转化之间的价值传递机制。</p></div><span class="biz-tag">Value Flow</span></div>{render_value_flow_html(value_flow_rows)}</section>
    <section class="report-page biz-section"><div class="report-topbar"><div class="report-stripe"></div><div class="report-banner">产业链分析报告</div></div><div class="biz-section-head"><div><h2>{heading_structure}</h2><p class="biz-section-note">基于图谱规模、节点分布和环节关系归纳产业体系的结构性特征。</p></div><span class="biz-tag">Structure</span></div>{render_structural_features_html(structural_rows)}</section>
  </main>
  <footer>产业链层级分析报告 · {esc(generated_at)}</footer>
</body>
</html>
"""


def render_policy_analysis_html(data: Dict[str, Any], title: str) -> str:
    generated_at = dt.datetime.now().strftime("%Y-%m-%d")
    summary = first_present(data, ["summary", "overview"], "")
    query = data.get("policy_query") if isinstance(data.get("policy_query"), dict) else {}
    regions = "、".join(str(item) for item in as_list(data.get("regions"))) or "-"
    region_rows = [row for row in as_list(data.get("regional_policy_analysis")) if isinstance(row, dict)]
    dimension_rows = [row for row in as_list(data.get("policy_dimensions")) if isinstance(row, dict)]
    policy_items = [row for row in as_list(data.get("policy_items")) if isinstance(row, dict)]
    region_columns = [
        ("region", "地区"),
        ("policy_count", "线索数"),
        ("handaas_policy_count", "旷湖政策库"),
        ("web_policy_count", "联网补充"),
        ("policy_focus", "政策重点"),
        ("key_agencies", "主要机构/来源"),
        ("analysis", "区域政策解读"),
    ]
    dimension_columns = [("dimension", "政策维度"), ("count", "线索数")]
    policy_columns = [
        ("region", "地区"),
        ("title", "政策/信息标题"),
        ("agency", "机构/来源"),
        ("policy_type", "类型"),
        ("publish_date", "日期"),
        ("summary", "摘要"),
        ("url", "链接"),
    ]
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{esc(title)}</title>
  <style>
    :root {{ --bg:#eef1f5; --page:#fff; --blue:#0b3768; --line:#d8dee8; --red:#7f1d1d; --gold:#d97706; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--bg); color:#1f2937; font-family:"Songti SC","STSong","Noto Serif CJK SC","SimSun",serif; line-height:1.78; }}
    .page {{ width:min(1080px,calc(100vw - 32px)); margin:28px auto; background:var(--page); border:1px solid #a8adb5; box-shadow:0 18px 44px rgba(15,23,42,.13); padding:0 34px 34px; }}
    .topbar {{ display:flex; height:54px; margin:0 -34px 30px; border-bottom:1px solid #333; }}
    .stripe {{ flex:1; background:repeating-linear-gradient(0deg,#575757 0,#575757 2px,#747474 2px,#747474 4px); }}
    .banner {{ width:420px; display:flex; align-items:center; justify-content:flex-end; padding:0 24px; color:#fff; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; font-weight:800; letter-spacing:.08em; background:linear-gradient(135deg,#0b4c84,#0284c7 48%,#0b2f55); }}
    h1 {{ margin:0 0 14px; color:var(--blue); font-size:36px; line-height:1.25; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }}
    h2 {{ margin:0 0 16px; color:var(--blue); font-size:25px; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }}
    .kicker {{ margin:0 0 14px; color:var(--blue); font-size:13px; font-weight:800; letter-spacing:.16em; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }}
    .summary {{ color:var(--blue); font-size:18px; line-height:1.9; font-weight:800; }}
    .note {{ border-left:5px solid var(--gold); background:#fff8eb; padding:14px 16px; color:#92400e; margin:18px 0; }}
    .scope {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; margin:22px 0; }}
    .scope div {{ border:1px solid #d6dee9; background:#f8fbff; padding:12px; }}
    .scope span {{ display:block; color:#64748b; font-size:12px; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }}
    .scope strong {{ color:var(--blue); font-size:13px; }}
    .table-wrap {{ overflow:auto; border:1px solid var(--blue); }}
    table {{ width:100%; border-collapse:collapse; background:white; }}
    th,td {{ padding:11px 12px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; font-size:13px; }}
    th {{ background:var(--blue); color:#fff; font-weight:800; white-space:nowrap; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }}
    tbody tr:nth-child(even) td {{ background:#dff1fb; }}
    @media (max-width:860px) {{ .scope {{ grid-template-columns:1fr 1fr; }} .banner {{ width:55%; }} h1 {{ font-size:30px; }} }}
    @page {{ size:A4; margin:12mm; }}
    @media print {{ body {{ background:#fff; }} .page {{ width:100%; margin:0 0 12mm; box-shadow:none; break-after:page; }} }}
  </style>
</head>
<body>
  <section class="page">
    <div class="topbar"><div class="stripe"></div><div class="banner">旷湖产业链政策分析</div></div>
    <p class="kicker">REGIONAL POLICY RESEARCH</p>
    <h1>{esc(title)}</h1>
    <p class="summary">{esc(summary)}</p>
    <div class="note">本报告结合 HandaaS 政策大数据 MCP 与联网搜索背景，按地区对政策数量、重点方向、发布机构和代表性政策进行结构化分析。</div>
    <div class="scope">
      <div><span>分析关键词</span><strong>{esc(data.get('keyword') or data.get('chain') or '-')}</strong></div>
      <div><span>分析地区</span><strong>{esc(regions)}</strong></div>
      <div><span>政策类型</span><strong>{esc(query.get('pn_type') or '全部')}</strong></div>
      <div><span>报告日期</span><strong>{esc(generated_at)}</strong></div>
    </div>
  </section>
  <section class="page"><div class="topbar"><div class="stripe"></div><div class="banner">区域政策分析</div></div><h2>一、各地政策情况对比</h2>{render_table(region_rows, region_columns)}</section>
  <section class="page"><div class="topbar"><div class="stripe"></div><div class="banner">区域政策分析</div></div><h2>二、政策支持维度</h2>{render_table(dimension_rows, dimension_columns)}</section>
  <section class="page"><div class="topbar"><div class="stripe"></div><div class="banner">区域政策分析</div></div><h2>三、代表性政策与联网依据</h2>{render_table(policy_items[:80], policy_columns)}</section>
</body>
</html>
"""


def confidence_label(value: Any) -> str:
    return {"high": "高", "medium": "中", "low": "低", "weak": "弱"}.get(str(value or "").lower(), str(value or "-"))


def evidence_status_label(value: Any) -> str:
    return {
        "available": "有效",
        "empty": "无有效数据",
        "error": "接口异常",
        "upstream_warning": "接口告警",
    }.get(str(value or "").lower(), str(value or "-"))


def render_enterprise_positioning_html(data: Dict[str, Any], title: str) -> str:
    enterprise = str(data.get("enterprise") or "企业")
    summary = str(data.get("summary") or "")
    profile = data.get("enterprise_profile") if isinstance(data.get("enterprise_profile"), dict) else {}
    primary = data.get("primary_position") if isinstance(data.get("primary_position"), dict) else {}
    chain_rows = [{**item, "confidence": confidence_label(item.get("confidence"))} for item in as_list(data.get("chain_ranking")) if isinstance(item, dict)]
    node_rows = [{**item, "confidence": confidence_label(item.get("confidence"))} for item in as_list(data.get("node_ranking")) if isinstance(item, dict)]
    evidence_rows = [{**item, "status": evidence_status_label(item.get("status"))} for item in as_list(data.get("evidence_summary")) if isinstance(item, dict)]
    match_rows = [item for item in as_list(data.get("evidence_matches")) if isinstance(item, dict)]
    boundaries = as_list(data.get("positioning_boundary"))
    status = str(primary.get("status") or "证据不足")
    confidence = confidence_label(primary.get("confidence"))
    score = primary.get("score") or 0
    path_parts = [part.strip() for part in str(primary.get("path") or "").split(">") if part.strip()]
    path_html = "".join(f'<span class="position-path-node">{esc(part)}</span>' for part in path_parts) or '<span class="muted">暂无明确归属路径</span>'
    profile_rows = [
        {"name": "企业名称", "value": profile.get("name") or enterprise},
        {"name": "经营状态", "value": profile.get("oper_status") or "-"},
        {"name": "工商行业", "value": profile.get("registered_industry") or "-"},
        {"name": "所在地", "value": profile.get("address") or "-"},
        {"name": "主要产品", "value": profile.get("business_products") or "-"},
        {"name": "业务标签", "value": profile.get("business_tags") or "-"},
        {"name": "经营范围", "value": profile.get("business_scope") or "-"},
        {"name": "企业简介", "value": profile.get("profile") or "-"},
    ]
    profile_html = "".join(
        f'<div class="position-profile-item"><span>{esc(row["name"])}</span><p>{esc(row["value"])}</p></div>'
        for row in profile_rows
    )
    chain_columns = [("chain", "产业链"), ("score", "匹配分"), ("confidence", "置信度"), ("best_node", "最佳节点"), ("candidate_nodes", "候选节点"), ("evidence_sources", "主要证据")]
    node_columns = [("chain", "产业链"), ("l2_segment", "L2 环节"), ("l3_module", "L3 模块"), ("l5_node", "L5 节点"), ("score", "匹配分"), ("confidence", "置信度"), ("evidence_sources", "证据来源"), ("matched_terms", "命中词")]
    evidence_columns = [("source", "证据来源"), ("status", "状态"), ("signal_count", "有效信号"), ("representative_evidence", "代表性证据")]
    match_columns = [("source", "证据来源"), ("match_type", "匹配方式"), ("matched_term", "命中内容"), ("score", "证据分"), ("snippet", "证据摘要")]
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="icon" href="data:," />
  <title>{esc(title)}</title>
  <style>
    :root {{ --bg:#edf1f5; --page:#fff; --blue:#083b6f; --blue2:#0b5f9e; --red:#7f1d1d; --gold:#c77700; --line:#d3dce7; --text:#1f2937; --muted:#64748b; }}
    * {{ box-sizing:border-box; letter-spacing:0 !important; }}
    body {{ margin:0; background:var(--bg); color:var(--text); font-family:"Songti SC","STSong","Noto Serif CJK SC","SimSun",serif; line-height:1.72; }}
    .position-page {{ width:min(1080px,calc(100vw - 32px)); margin:28px auto; background:var(--page); border:1px solid #a8adb5; box-shadow:0 18px 44px rgba(15,23,42,.12); padding:0 30px 34px; }}
    .position-topbar {{ display:flex; height:54px; margin:0 -30px 30px; border-bottom:1px solid #333; }}
    .position-stripe {{ flex:1; background:repeating-linear-gradient(0deg,#575757 0,#575757 2px,#747474 2px,#747474 4px); }}
    .position-banner {{ width:420px; display:flex; align-items:center; justify-content:flex-end; padding:0 24px; background:#0875b9; color:#fff; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; font-weight:800; }}
    .position-kicker {{ margin:0 0 12px; color:var(--blue2); font-size:12px; font-weight:900; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }}
    h1 {{ margin:0 0 16px; color:var(--blue); font-size:36px; line-height:1.25; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }}
    h2 {{ margin:0; color:var(--blue); font-size:25px; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }}
    .position-summary {{ max-width:920px; color:#123d68; font-size:17px; font-weight:800; line-height:1.85; }}
    .position-metrics {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; margin:24px 0 0; }}
    .position-metric {{ border:1px solid #cbd5e1; background:#f8fbff; padding:14px; }}
    .position-metric strong {{ display:block; color:var(--blue); font-size:23px; line-height:1.2; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }}
    .position-metric span {{ display:block; margin-top:6px; color:var(--muted); font-size:11px; font-weight:800; }}
    .position-section-head {{ display:flex; justify-content:space-between; gap:14px; align-items:flex-start; margin-bottom:18px; }}
    .position-section-head p {{ margin:6px 0 0; color:var(--muted); font-size:13px; }}
    .position-tag {{ background:#e8f3fb; color:var(--blue); padding:5px 9px; font-size:11px; font-weight:800; white-space:nowrap; }}
    .position-profile-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; }}
    .position-profile-item {{ border:1px solid var(--line); background:#fbfdff; padding:13px; }}
    .position-profile-item span {{ color:var(--blue2); font-size:11px; font-weight:800; }}
    .position-profile-item p {{ margin:5px 0 0; color:#334155; font-size:13px; white-space:pre-wrap; }}
    .position-primary {{ border:1px solid #9fb6cf; border-left:6px solid var(--blue2); background:#f8fbff; padding:20px; }}
    .position-primary-head {{ display:flex; justify-content:space-between; gap:16px; align-items:center; }}
    .position-primary-head h3 {{ margin:0; color:var(--blue); font-size:22px; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }}
    .position-score {{ color:var(--red); font-size:28px; font-weight:900; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }}
    .position-path {{ display:flex; flex-wrap:wrap; gap:8px; margin:18px 0; }}
    .position-path-node {{ border:1px solid #b8c7d8; background:#fff; padding:7px 10px; color:#123d68; font-size:12px; font-weight:800; }}
    .position-evidence-line {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; }}
    .position-evidence-line div {{ border-top:1px solid var(--line); padding-top:10px; }}
    .position-evidence-line span {{ color:var(--muted); font-size:10px; font-weight:800; }}
    .position-evidence-line p {{ margin:4px 0 0; color:#334155; font-size:12px; }}
    .table-wrap {{ overflow:auto; border:1px solid var(--blue); }}
    table {{ width:100%; border-collapse:collapse; background:#fff; }}
    th,td {{ padding:10px 11px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; font-size:12px; overflow-wrap:anywhere; }}
    th {{ background:var(--blue); color:#fff; font-weight:800; white-space:nowrap; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }}
    tbody tr:nth-child(even) td {{ background:#e6f3fb; }}
    .position-boundary {{ margin:0; padding-left:22px; }}
    .position-boundary li {{ margin:8px 0; }}
    .muted {{ color:var(--muted); }}
    @media (max-width:760px) {{ .position-profile-grid,.position-metrics {{ grid-template-columns:1fr 1fr; }} .position-banner {{ width:55%; }} .position-primary-head {{ align-items:flex-start; }} .position-evidence-line {{ grid-template-columns:1fr; }} .table-wrap table {{ min-width:760px; }} h1 {{ font-size:29px; }} }}
    @page {{ size:A4; margin:12mm; }}
    @media print {{ body {{ background:#fff; line-height:1.5; }} .position-page {{ width:100%; margin:0; padding:0 18px 22px; box-shadow:none; break-after:page; }} .position-topbar {{ margin:0 -18px 18px; }} h1 {{ font-size:27px; }} .position-summary {{ font-size:12px; }} .position-metric {{ padding:8px; }} .position-metric strong {{ font-size:16px; }} .position-profile-item,.position-primary {{ break-inside:avoid; }} .table-wrap {{ overflow:visible; }} .table-wrap table {{ min-width:0 !important; }} th,td {{ padding:6px; font-size:8px; line-height:1.4; }} }}
  </style>
</head>
<body>
  <section class="position-page">
    <div class="position-topbar"><div class="position-stripe"></div><div class="position-banner">企业产业链定位分析</div></div>
    <p class="position-kicker">ENTERPRISE POSITIONING RESEARCH</p>
    <h1>{esc(title)}</h1>
    <p class="position-summary">{esc(summary)}</p>
    <div class="position-metrics">
      <div class="position-metric"><strong>{esc(status)}</strong><span>归属判断</span></div>
      <div class="position-metric"><strong>{esc(score)}</strong><span>综合匹配分</span></div>
      <div class="position-metric"><strong>{esc(confidence)}</strong><span>置信度</span></div>
      <div class="position-metric"><strong>{esc(primary.get('chain') or '-')}</strong><span>主产业链</span></div>
    </div>
  </section>
  <section class="position-page"><div class="position-topbar"><div class="position-stripe"></div><div class="position-banner">企业基本画像</div></div><div class="position-section-head"><div><h2>一、企业基本画像</h2><p>归纳企业工商行业、主营产品、业务标签和经营范围。</p></div><span class="position-tag">Enterprise Profile</span></div><div class="position-profile-grid">{profile_html}</div></section>
  <section class="position-page"><div class="position-topbar"><div class="position-stripe"></div><div class="position-banner">主归属定位</div></div><div class="position-section-head"><div><h2>二、主归属产业链环节</h2><p>按照产业链、价值环节、产业模块和标准节点逐层定位。</p></div><span class="position-tag">Primary Position</span></div><div class="position-primary"><div class="position-primary-head"><h3>{esc(primary.get('chain') or '暂无明确归属')}</h3><div class="position-score">{esc(score)}/100</div></div><div class="position-path">{path_html}</div><div class="position-evidence-line"><div><span>主要证据来源</span><p>{esc(primary.get('evidence_sources') or '-')}</p></div><div><span>关键命中内容</span><p>{esc(primary.get('matched_terms') or '-')}</p></div></div></div></section>
  <section class="position-page"><div class="position-topbar"><div class="position-stripe"></div><div class="position-banner">产业链对比</div></div><div class="position-section-head"><div><h2>三、候选产业链对比</h2><p>比较企业在不同产业链中的节点匹配强度和证据覆盖。</p></div><span class="position-tag">Chain Ranking</span></div>{render_table(chain_rows, chain_columns)}</section>
  <section class="position-page"><div class="position-topbar"><div class="position-stripe"></div><div class="position-banner">节点匹配分析</div></div><div class="position-section-head"><div><h2>四、候选节点匹配</h2><p>展示最相关的 L2/L3/L5 归属路径及其匹配依据。</p></div><span class="position-tag">Node Ranking</span></div>{render_table(node_rows, node_columns)}</section>
  <section class="position-page"><div class="position-topbar"><div class="position-stripe"></div><div class="position-banner">证据分析</div></div><div class="position-section-head"><div><h2>五、证据覆盖与关键命中</h2><p>说明各类企业证据的有效信号数量及主归属节点的命中情况。</p></div><span class="position-tag">Evidence</span></div>{render_table(evidence_rows, evidence_columns)}{('<h2 style="margin:28px 0 14px">主归属节点证据</h2>' + render_table(match_rows, match_columns)) if match_rows else ''}</section>
  <section class="position-page"><div class="position-topbar"><div class="position-stripe"></div><div class="position-banner">定位边界</div></div><div class="position-section-head"><div><h2>六、定位边界说明</h2><p>明确产业链归属判断的适用范围和多业务企业的解释方式。</p></div><span class="position-tag">Boundary</span></div>{render_html_list(boundaries).replace('<ul>', '<ul class="position-boundary">')}</section>
</body>
</html>
"""


def delivery_decision_rows(data: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item in normalize_decisions(data):
        matches = [
            str(match.get("source") or "")
            for match in as_list(item.get("matched_evidence"))
            if isinstance(match, Mapping) and match.get("source")
        ]
        rows.append({
            "enterprise_name": item.get("enterprise_name") or item.get("name") or "",
            "decision": decision_label(item.get("decision")),
            "review_score": item.get("review_score") or item.get("fit_score") or 0,
            "evidence_strength": strength_label(item.get("evidence_strength")),
            "evidence_source_count": item.get("evidence_source_count") or 0,
            "strong_source_count": item.get("strong_source_count") or 0,
            "evidence_sources": "、".join(dict.fromkeys(matches)) or "-",
            "reason": item.get("reason") or "",
        })
    return rows


def render_delivery_shell(
    title: str,
    kicker: str,
    summary: Any,
    metrics: Sequence[Mapping[str, Any]],
    sections: Sequence[tuple[str, str, str]],
) -> str:
    generated_at = dt.datetime.now().strftime("%Y-%m-%d")
    metrics_html = "".join(
        f'<div class="delivery-metric"><strong>{esc(item.get("value"))}</strong><span>{esc(item.get("label"))}</span></div>'
        for item in metrics
    )
    sections_html = "".join(
        f'''<section class="delivery-page"><div class="delivery-section-head"><div><span>{index:02d}</span><h2>{esc(section_title)}</h2></div><p>{esc(note)}</p></div>{body}</section>'''
        for index, (section_title, note, body) in enumerate(sections, start=1)
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{esc(title)}</title>
  <style>
    :root {{ --ink:#132337; --muted:#64748b; --line:#d8e0e8; --navy:#123a5a; --teal:#0f766e; --paper:#fff; --wash:#eef3f6; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--wash); color:var(--ink); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; line-height:1.7; }}
    .delivery-cover,.delivery-page {{ width:min(1060px,calc(100vw - 32px)); margin:24px auto; background:var(--paper); border:1px solid var(--line); box-shadow:0 12px 34px rgba(20,45,70,.09); }}
    .delivery-cover {{ min-height:620px; display:grid; grid-template-columns:minmax(0,1fr) 310px; }}
    .delivery-cover-main {{ padding:64px 58px; display:flex; flex-direction:column; justify-content:space-between; }}
    .delivery-kicker {{ margin:0; color:var(--teal); font-size:13px; font-weight:800; }}
    h1 {{ max-width:760px; margin:20px 0 26px; font-size:40px; line-height:1.25; letter-spacing:0; }}
    .delivery-summary {{ margin:0; max-width:760px; color:#3f5267; font-size:17px; }}
    .delivery-date {{ color:var(--muted); font-size:13px; }}
    .delivery-metrics {{ padding:44px 28px; background:var(--navy); color:#fff; display:flex; flex-direction:column; justify-content:center; gap:12px; }}
    .delivery-metric {{ border-bottom:1px solid rgba(255,255,255,.22); padding:14px 4px 18px; }}
    .delivery-metric:last-child {{ border-bottom:0; }}
    .delivery-metric strong {{ display:block; font-size:29px; line-height:1.2; overflow-wrap:anywhere; }}
    .delivery-metric span {{ display:block; margin-top:5px; color:#cae4e5; font-size:12px; }}
    .delivery-page {{ padding:34px 38px 42px; }}
    .delivery-section-head {{ display:flex; align-items:flex-end; justify-content:space-between; gap:24px; padding-bottom:16px; border-bottom:2px solid var(--navy); margin-bottom:22px; }}
    .delivery-section-head > div {{ display:flex; align-items:center; gap:12px; }}
    .delivery-section-head span {{ color:var(--teal); font-weight:800; }}
    .delivery-section-head h2 {{ margin:0; font-size:24px; }}
    .delivery-section-head p {{ max-width:520px; margin:0; color:var(--muted); font-size:12px; text-align:right; }}
    .table-wrap {{ overflow:auto; border:1px solid var(--line); }}
    table {{ width:100%; border-collapse:collapse; background:#fff; }}
    th,td {{ padding:11px 12px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; font-size:13px; }}
    th {{ background:#edf3f6; color:#28445c; font-weight:750; white-space:nowrap; }}
    tr:last-child td {{ border-bottom:0; }}
    .kv-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }}
    .kv {{ border:1px solid var(--line); padding:14px; background:#f8fafb; }}
    .kv-label {{ color:var(--muted); font-size:12px; }}
    .kv-value {{ margin-top:4px; font-size:14px; white-space:pre-wrap; overflow-wrap:anywhere; }}
    ul {{ margin:0; padding-left:20px; }} li {{ margin:7px 0; }} .muted {{ color:var(--muted); }}
    @media (max-width:760px) {{ .delivery-cover {{ grid-template-columns:1fr; }} .delivery-cover-main {{ padding:38px 28px; }} .delivery-metrics {{ padding:24px 28px; }} h1 {{ font-size:30px; }} .delivery-page {{ padding:26px 20px; }} .delivery-section-head {{ align-items:flex-start; flex-direction:column; }} .delivery-section-head p {{ text-align:left; }} .kv-grid {{ grid-template-columns:1fr; }} }}
    @media print {{ body {{ background:#fff; }} .delivery-cover,.delivery-page {{ width:100%; margin:0; border:0; box-shadow:none; break-after:page; }} }}
  </style>
</head>
<body>
  <article class="delivery-cover">
    <div class="delivery-cover-main"><div><p class="delivery-kicker">{esc(kicker)}</p><h1>{esc(title)}</h1><p class="delivery-summary">{esc(summary)}</p></div><p class="delivery-date">报告日期：{generated_at}</p></div>
    <aside class="delivery-metrics">{metrics_html}</aside>
  </article>
  {sections_html}
</body>
</html>
"""


def render_enterprise_node_analysis_html(data: Dict[str, Any], title: str) -> str:
    profile = data.get("enterprise_profile") if isinstance(data.get("enterprise_profile"), Mapping) else {}
    mapping = data.get("node_mapping") if isinstance(data.get("node_mapping"), Mapping) else {}
    fit = data.get("fit_assessment") if isinstance(data.get("fit_assessment"), Mapping) else {}
    evidence_rows = [
        {
            **item,
            "status": evidence_status_label(item.get("status")),
            "signal_strength": strength_label(item.get("signal_strength")),
        }
        for item in as_list(data.get("evidence_summary"))
        if isinstance(item, Mapping)
    ]
    fit_rows = {
        "目标产业链": data.get("chain") or "-",
        "目标节点": fit.get("project_node") or fit.get("target_node") or data.get("node") or "-",
        "标准路径": fit.get("project_node_path") or mapping.get("primary_project_path") or "-",
        "挂链判断": decision_label(fit.get("decision")),
        "证据强度": strength_label(fit.get("evidence_strength")),
        "综合匹配分": f"{fit.get('fit_score') or 0}/100",
        "判定依据": fit.get("reason") or "-",
    }
    sections = [
        ("企业基本画像", "呈现企业身份、经营状态、经营范围与主营能力。", render_kv_grid(profile)),
        ("产业链节点定位", "对照项目标准产业链节点，明确企业的目标归属路径。", render_kv_grid(fit_rows)),
        ("项目节点映射", "记录输入节点与项目标准节点之间的映射口径。", render_kv_grid(mapping)),
        ("证据核验", "按工商、业务、标签、专利和招投标等来源展示有效证据。", render_table(evidence_rows, [("product", "证据来源"), ("status", "状态"), ("signal_strength", "强度"), ("matched_keywords", "命中内容"), ("key_findings", "主要发现"), ("data_points", "关键数据")])) ,
        ("判断边界", "说明影响挂链结论的数据质量与复核边界。", render_html_list(as_list(data.get("risk_flags")))),
    ]
    metrics = [
        {"label": "企业", "value": data.get("enterprise") or "-"},
        {"label": "匹配分", "value": f"{fit.get('fit_score') or 0}/100"},
        {"label": "挂链判断", "value": decision_label(fit.get("decision"))},
        {"label": "证据强度", "value": strength_label(fit.get("evidence_strength"))},
    ]
    return render_delivery_shell(title, "企业产业链节点分析报告", data.get("summary") or "", metrics, sections)


def render_node_linking_html(data: Dict[str, Any], title: str) -> str:
    summary = data.get("link_summary") if isinstance(data.get("link_summary"), Mapping) else {}
    route_rows = [item for item in as_list((data.get("preview") or {}).get("route_results") if isinstance(data.get("preview"), Mapping) else []) if isinstance(item, Mapping)]
    if not route_rows and isinstance(data.get("search_plan"), Mapping):
        route_rows = [item for item in as_list(data["search_plan"].get("recall_routes")) if isinstance(item, Mapping)]
    route_rows = [{**item, "route_id": route_label(item.get("route_id") or item.get("id"))} for item in route_rows]
    decisions = delivery_decision_rows(data)
    confirmed = [item for item in decisions if item.get("decision") == "确认挂链"]
    pending = [item for item in decisions if item.get("decision") == "待复核"]
    rejected = [item for item in decisions if item.get("decision") == "不建议挂链"]
    decision_columns = [("enterprise_name", "企业"), ("review_score", "复核分"), ("evidence_strength", "证据强度"), ("evidence_source_count", "有效来源"), ("strong_source_count", "强来源"), ("evidence_sources", "证据构成"), ("reason", "判定依据")]
    target = {
        "产业链": data.get("chain") or "-",
        "L5节点": data.get("node") or "-",
        "标准路径": " > ".join(str(item) for item in as_list(data.get("path"))) or "-",
        "查询能力": "完整高筛" if not data.get("precision_limited") else "关键词召回预览",
        "证据复核": "已执行" if summary.get("evidence_reviewed") else "未执行",
    }
    sections = [
        ("挂链对象与口径", "明确本次企业筛选对应的产业链层级、目标节点和数据能力。", render_kv_grid(target)),
        ("召回路线表现", "展示各工商与业务字段组合的候选覆盖情况。", render_table(route_rows, [("route_id", "路线"), ("purpose", "筛选逻辑"), ("priority", "优先级"), ("total", "候选总量"), ("sample_count", "抽样数量")])),
        ("确认挂链企业", "仅纳入具备强证据且多来源一致的企业。", render_table(confirmed, decision_columns)),
        ("待复核企业", "现有证据尚不足以形成稳定挂链结论。", render_table(pending, decision_columns)),
        ("排除企业", "记录未发现直接节点证据或存在明显冲突信号的企业。", render_table(rejected, decision_columns)),
    ]
    metrics = [
        {"label": "候选企业", "value": summary.get("candidate_count") or 0},
        {"label": "确认挂链", "value": summary.get("confirmed") or 0},
        {"label": "待复核", "value": summary.get("manual_review") or 0},
        {"label": "排除", "value": summary.get("rejected") or 0},
    ]
    report_summary = data.get("summary") or f"围绕“{data.get('node') or ''}”节点完成企业召回与证据复核，形成确认挂链、待复核和排除三类结果。"
    return render_delivery_shell(title, "产业链节点企业挂链报告", report_summary, metrics, sections)


def render_chain_linking_html(data: Dict[str, Any], title: str) -> str:
    summary = data.get("summary") if isinstance(data.get("summary"), Mapping) else {}
    node_rows: List[Dict[str, Any]] = []
    enterprise_rows: List[Dict[str, Any]] = []
    for node in as_list(data.get("nodes")):
        if not isinstance(node, Mapping):
            continue
        reviewed = [item for item in as_list(node.get("reviewed_enterprises")) if isinstance(item, Mapping)]
        route_ids = [
            str(item.get("id") or item.get("route_id") or "") if isinstance(item, Mapping) else str(item or "")
            for item in as_list(node.get("recall_routes"))
        ]
        route_ids = [item for item in route_ids if item]
        confirmed_names = [str(item.get("enterprise_name") or "") for item in reviewed if item.get("decision") == "confirmed"]
        pending_names = [str(item.get("enterprise_name") or "") for item in reviewed if item.get("decision") == "uncertain"]
        node_rows.append({
            "node": node.get("node") or "",
            "path": " > ".join(str(item) for item in as_list(node.get("path"))),
            "candidate_count": node.get("candidate_count") or 0,
            "confirmed": node.get("confirmed") or 0,
            "manual_review": node.get("manual_review") or 0,
            "rejected": node.get("rejected") or 0,
            "recall_route_count": len(route_ids),
            "recall_routes": "、".join(route_label(item) for item in route_ids) or "-",
            "confirmed_enterprises": "、".join(confirmed_names) or "-",
            "pending_enterprises": "、".join(pending_names) or "-",
        })
        for item in reviewed:
            enterprise_rows.append({
                "node": node.get("node") or "",
                "enterprise_name": item.get("enterprise_name") or "",
                "decision": decision_label(item.get("decision")),
                "review_score": item.get("review_score") or 0,
                "evidence_source_count": item.get("evidence_source_count") or 0,
                "strong_source_count": item.get("strong_source_count") or 0,
                "reason": item.get("reason") or "",
            })
    selected = (data.get("selection") or {}).get("selected_node_count") if isinstance(data.get("selection"), Mapping) else len(node_rows)
    covered = sum(1 for item in node_rows if int(item.get("confirmed") or 0) > 0)
    node_columns = [("node", "L5节点"), ("path", "标准路径"), ("recall_route_count", "路线数"), ("recall_routes", "召回路线"), ("candidate_count", "候选"), ("confirmed", "确认"), ("manual_review", "待复核"), ("rejected", "排除"), ("confirmed_enterprises", "确认企业"), ("pending_enterprises", "待复核企业")]
    enterprise_columns = [("node", "L5节点"), ("enterprise_name", "企业"), ("decision", "判断"), ("review_score", "复核分"), ("evidence_source_count", "有效来源"), ("strong_source_count", "强来源"), ("reason", "判定依据")]
    failures = [item for item in as_list(data.get("failures")) if isinstance(item, Mapping)]
    sections = [
        ("节点覆盖总览", "按 L5 标准节点汇总候选、确认挂链、待复核及排除情况。", render_table(node_rows, node_columns)),
        ("企业挂链明细", "列示各节点下已确认或待复核企业及其证据判断。", render_table(enterprise_rows, enterprise_columns)),
    ]
    if failures:
        sections.append(("未完成节点", "记录本轮未形成有效结果的节点及原因。", render_table(failures, [("node", "节点"), ("path", "路径"), ("error", "原因")])))
    metrics = [
        {"label": "分析节点", "value": selected or 0},
        {"label": "已覆盖节点", "value": covered},
        {"label": "确认挂链企业", "value": summary.get("confirmed") or 0},
        {"label": "待复核企业", "value": summary.get("manual_review") or 0},
    ]
    report_summary = data.get("report_summary") or f"本报告围绕“{data.get('chain') or ''}”产业链的 L5 标准节点开展企业筛选与证据复核，形成节点覆盖和企业挂链明细。"
    return render_delivery_shell(title, "产业链节点企业挂链总报告", report_summary, metrics, sections)


def render_html(data: Dict[str, Any], title: str) -> str:
    if str(data.get("report_type") or "") == "industry_chain_analysis":
        return render_chain_analysis_html(data, title)
    if str(data.get("report_type") or "") == "policy_analysis":
        return render_policy_analysis_html(data, title)
    if str(data.get("report_type") or "") == "enterprise_chain_positioning":
        return render_enterprise_positioning_html(data, title)
    if str(data.get("report_type") or "") == "enterprise_node_analysis":
        return render_enterprise_node_analysis_html(data, title)
    if str(data.get("report_type") or "") == "enterprise_node_linking":
        return render_node_linking_html(data, title)
    if str(data.get("report_type") or "") == "industry_chain_linking":
        return render_chain_linking_html(data, title)
    generated_at = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    industry_map = as_list(first_present(data, ["industry_map", "map", "ontology", "industry_structure"], []))
    priority_segments = as_list(first_present(data, ["priority_segments", "segments", "focus_segments"], []))
    search_strategy = as_list(first_present(data, ["search_strategy", "strategy", "search_plan"], []))
    next_actions = as_list(first_present(data, ["next_actions", "actions", "recommendations"], []))
    candidates = normalize_candidates(data)
    decisions = normalize_decisions(data)
    counts = decision_counts(decisions)
    summary = first_present(data, ["summary", "conclusion", "overview"], "")
    preview = data.get("preview") if isinstance(data.get("preview"), dict) else {}
    total = preview.get("total") or data.get("total") or len(candidates)
    is_chain_analysis = str(data.get("report_type") or "") == "industry_chain_analysis"
    graph_summary = data.get("project_graph_summary") if isinstance(data.get("project_graph_summary"), dict) else {}

    decision_columns = [
        ("enterprise_name", "企业"),
        ("matched_segment", "匹配环节"),
        ("decision", "判断"),
        ("evidence_strength", "证据强度"),
        ("reason", "原因"),
        ("next_action", "下一步"),
    ]
    candidate_columns = [
        ("name", "企业"),
        ("id", "ID"),
        ("socialCreditCode", "统一社会信用代码"),
        ("regCapital", "注册资本"),
    ]

    if is_chain_analysis:
        metric_cards = f"""
      <div class="card"><div class="metric">{esc(graph_summary.get('l2_count', '-'))}</div><div class="label">L2 价值环节</div></div>
      <div class="card"><div class="metric">{esc(graph_summary.get('l3_count', '-'))}</div><div class="label">L3 产业模块</div></div>
      <div class="card"><div class="metric">{esc(graph_summary.get('l5_count', '-'))}</div><div class="label">L5 标准节点</div></div>
      <div class="card"><div class="metric">{esc(graph_summary.get('node_count', '-'))}</div><div class="label">项目节点数</div></div>
        """
    else:
        metric_cards = f"""
      <div class="card"><div class="metric">{esc(total)}</div><div class="label">候选企业 / 线索</div></div>
      <div class="card"><div class="metric confirmed">{counts.get('confirmed',0)}</div><div class="label">确认匹配</div></div>
      <div class="card"><div class="metric uncertain">{counts.get('uncertain',0)}</div><div class="label">待复核</div></div>
      <div class="card"><div class="metric rejected">{counts.get('rejected',0)}</div><div class="label">建议剔除</div></div>
        """

    optional_sections: List[str] = []
    if industry_map or priority_segments:
        optional_sections.append(f"""
    <section class="card">
      <h2>产业链结构与重点环节</h2>
      {render_html_list(industry_map or priority_segments)}
    </section>""")
    if search_strategy:
        optional_sections.append(f"""
    <section class="card">
      <h2>企业搜索策略</h2>
      {render_html_list(search_strategy)}
    </section>""")
    if candidates:
        optional_sections.append(f"""
    <section class="card">
      <h2>候选企业</h2>
      {render_table(candidates, candidate_columns)}
    </section>""")
    if decisions:
        optional_sections.append(f"""
    <section class="card">
      <h2>证据化判断</h2>
      {render_table(decisions, decision_columns)}
    </section>""")
    if next_actions:
        optional_sections.append(f"""
    <section class="card">
      <h2>下一步建议</h2>
      {render_html_list(next_actions)}
    </section>""")
    optional_html = "\n".join(optional_sections)

    raw_json = esc(json_dumps(data, pretty=True))
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{esc(title)}</title>
  <style>
    :root {{ --bg:#f6f7fb; --card:#ffffff; --text:#172033; --muted:#667085; --line:#e6e8ef; --blue:#2454ff; --green:#0f8a5f; --amber:#b7791f; --red:#c53030; }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; background:var(--bg); color:var(--text); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",Arial,sans-serif; line-height:1.55; }}
    header {{ padding:36px 28px 28px; background:linear-gradient(135deg,#101828,#2447ff); color:white; }}
    main {{ max-width:1120px; margin:0 auto; padding:24px; }}
    h1 {{ margin:0 0 8px; font-size:30px; }}
    h2 {{ margin:0 0 14px; font-size:20px; }}
    .subtitle {{ opacity:.82; }}
    .grid {{ display:grid; grid-template-columns: repeat(auto-fit,minmax(180px,1fr)); gap:14px; margin-top:-36px; }}
    .card {{ background:var(--card); border:1px solid var(--line); border-radius:16px; padding:18px; box-shadow:0 8px 24px rgba(16,24,40,.06); margin-bottom:18px; }}
    .metric {{ font-size:28px; font-weight:750; }}
    .label {{ color:var(--muted); font-size:13px; }}
    .confirmed {{ color:var(--green); }} .uncertain {{ color:var(--amber); }} .rejected {{ color:var(--red); }}
    .muted {{ color:var(--muted); }}
    ul {{ margin:8px 0 0 20px; padding:0; }} li {{ margin:6px 0; }}
    .table-wrap {{ overflow:auto; border:1px solid var(--line); border-radius:12px; }}
    table {{ width:100%; border-collapse:collapse; background:white; }}
    th,td {{ padding:11px 12px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; font-size:14px; }}
    th {{ background:#f8f9fc; color:#344054; font-weight:650; white-space:nowrap; }}
    tr:last-child td {{ border-bottom:0; }}
    details {{ margin-top:8px; }}
    pre {{ white-space:pre-wrap; word-break:break-word; margin:0; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:12px; }}
    .section-title {{ display:flex; justify-content:space-between; gap:12px; align-items:center; }}
    .tag {{ display:inline-flex; align-items:center; border-radius:999px; padding:3px 9px; background:#eef2ff; color:var(--blue); font-size:12px; }}
    .kv-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:12px; }}
    .kv {{ border:1px solid var(--line); border-radius:12px; padding:12px; background:#fbfcff; }}
    .kv-label {{ color:var(--muted); font-size:12px; margin-bottom:4px; }}
    .kv-value {{ font-size:14px; white-space:pre-wrap; word-break:break-word; }}
    .graph-showcase {{ overflow:hidden; border:1px solid #e2e8f0; border-radius:24px; background:#fff; box-shadow:0 12px 32px rgba(15,23,42,.08); margin-bottom:18px; }}
    .graph-topbar {{ display:flex; justify-content:space-between; gap:24px; align-items:flex-end; padding:24px; border-bottom:1px solid #e2e8f0; background:#fff; }}
    .graph-kicker {{ margin:0; color:#2563eb; font-size:11px; font-weight:800; letter-spacing:.22em; text-transform:uppercase; }}
    .graph-topbar h2 {{ margin:8px 0 0; color:#020617; font-size:28px; letter-spacing:-.04em; }}
    .graph-desc {{ margin:8px 0 0; max-width:760px; color:#64748b; font-size:13px; line-height:1.7; }}
    .graph-stats {{ display:grid; grid-template-columns:repeat(3,minmax(92px,1fr)); gap:8px; min-width:310px; }}
    .graph-stat {{ border:1px solid #e2e8f0; border-radius:16px; background:#f8fafc; padding:12px 14px; text-align:center; }}
    .graph-stat strong {{ display:block; color:#020617; font-size:22px; line-height:1; letter-spacing:-.04em; }}
    .graph-stat span {{ display:block; margin-top:5px; color:#64748b; font-size:11px; font-weight:700; }}
    .graph-hierarchy {{ display:flex; flex-wrap:wrap; gap:8px; padding:14px 24px 0; background:#f8fafc; }}
    .graph-badge {{ display:inline-flex; align-items:center; border:1px solid #e2e8f0; border-radius:999px; background:#fff; padding:5px 12px; color:#64748b; font-size:12px; font-weight:700; }}
    .graph-badge span {{ color:#2563eb; }}
    .graph-scroll {{ overflow-x:auto; padding:20px; background:#f8fafc; }}
    .graph-grid {{ display:grid; gap:20px; }}
    .graph-l2 {{ display:flex; min-width:0; flex-direction:column; overflow:hidden; border-radius:18px; border:1px solid; box-shadow:0 1px 2px rgba(15,23,42,.04), inset 0 0 0 1px rgba(255,255,255,.7); }}
    .graph-l2-blue {{ border-color:#bfdbfe; background:rgba(239,246,255,.75); }}
    .graph-l2-emerald {{ border-color:#a7f3d0; background:rgba(236,253,245,.75); }}
    .graph-l2-violet {{ border-color:#ddd6fe; background:rgba(245,243,255,.75); }}
    .graph-l2-amber {{ border-color:#fde68a; background:rgba(255,251,235,.75); }}
    .graph-l2-rose {{ border-color:#fecdd3; background:rgba(255,241,242,.75); }}
    .graph-l2-head {{ display:flex; align-items:center; justify-content:space-between; gap:12px; padding:13px 15px; border-bottom:1px solid; }}
    .graph-l2-head h3 {{ min-width:0; margin:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:17px; font-weight:800; letter-spacing:-.02em; }}
    .graph-l2-head span {{ flex-shrink:0; border-radius:999px; background:rgba(255,255,255,.82); padding:5px 9px; color:#475569; font-size:11px; font-weight:800; }}
    .graph-l2-head-blue {{ border-color:#bfdbfe; background:rgba(219,234,254,.72); color:#172554; }}
    .graph-l2-head-emerald {{ border-color:#a7f3d0; background:rgba(209,250,229,.72); color:#064e3b; }}
    .graph-l2-head-violet {{ border-color:#ddd6fe; background:rgba(237,233,254,.72); color:#2e1065; }}
    .graph-l2-head-amber {{ border-color:#fde68a; background:rgba(254,243,199,.72); color:#78350f; }}
    .graph-l2-head-rose {{ border-color:#fecdd3; background:rgba(255,228,230,.72); color:#881337; }}
    .graph-l3-stack {{ display:grid; align-content:start; gap:12px; padding:12px; }}
    .graph-l3 {{ min-width:0; border:1px solid; border-radius:14px; background:rgba(255,255,255,.9); transition:background .2s ease, border-color .2s ease; }}
    .graph-l3-blue {{ border-color:#dbeafe; }} .graph-l3-emerald {{ border-color:#d1fae5; }} .graph-l3-violet {{ border-color:#ede9fe; }} .graph-l3-amber {{ border-color:#fef3c7; }} .graph-l3-rose {{ border-color:#ffe4e6; }}
    .graph-l3-head {{ display:flex; align-items:center; gap:8px; border-bottom:1px solid #f1f5f9; padding:10px 11px; }}
    .graph-dot {{ width:8px; height:8px; flex-shrink:0; border-radius:999px; }}
    .graph-dot-blue {{ background:#3b82f6; }} .graph-dot-emerald {{ background:#10b981; }} .graph-dot-violet {{ background:#8b5cf6; }} .graph-dot-amber {{ background:#f59e0b; }} .graph-dot-rose {{ background:#f43f5e; }}
    .graph-l3-head h4 {{ min-width:0; margin:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:#0f172a; font-size:13px; font-weight:800; }}
    .graph-count {{ margin-left:auto; flex-shrink:0; border-radius:999px; background:#f1f5f9; padding:3px 7px; color:#64748b; font-size:10px; font-weight:800; }}
    .graph-l5-grid {{ display:grid; grid-template-columns:1fr; gap:8px; padding:9px; }}
    .graph-l5 {{ min-width:0; border:1px solid rgba(203,213,225,.82); border-radius:10px; background:rgba(248,250,252,.78); padding:9px 10px; color:#334155; font-size:12px; font-weight:750; line-height:1.35; }}
    .graph-l5 span {{ display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
    .graph-empty {{ margin:0; padding:8px; color:#94a3b8; font-size:11px; }}
    @media (max-width: 760px) {{
      .graph-topbar {{ align-items:stretch; flex-direction:column; }}
      .graph-stats {{ min-width:0; }}
      .graph-topbar h2 {{ font-size:22px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>{esc(title)}</h1>
    <div class="subtitle">由旷湖产业链分析 Skill 生成 · {esc(generated_at)}</div>
  </header>
  <main>
    <section class="grid">
      {metric_cards}
    </section>

    <section class="card">
      <div class="section-title"><h2>结论摘要</h2><span class="tag">Summary</span></div>
      <p>{esc(summary) if summary else '本报告根据输入结果展示产业链结构、企业搜索策略、候选企业和证据化判断。'}</p>
    </section>

    {render_professional_sections_html(data)}

    {optional_html}

    <section class="card">
      <h2>原始数据</h2>
      <details><summary>展开 JSON</summary><pre>{raw_json}</pre></details>
    </section>
  </main>
</body>
</html>
"""


def md_list(items: Iterable[Any]) -> str:
    rows = []
    for item in items:
        rows.append(f"- {text(item).replace(chr(10), ' ')}")
    return "\n".join(rows) if rows else "暂无"


def md_table(rows: Sequence[Mapping[str, Any]], columns: Sequence[tuple[str, str]]) -> str:
    if not rows:
        return "暂无"
    header = "| " + " | ".join(label for _, label in columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for row in rows:
        vals = [text(row.get(key, "")).replace("\n", " ").replace("|", "\\|") for key, _ in columns]
        body.append("| " + " | ".join(vals) + " |")
    return "\n".join([header, sep, *body])


def md_kv(data: Mapping[str, Any]) -> str:
    if not data:
        return "暂无"
    return "\n".join(f"- **{label(str(key))}**：{text(value).replace(chr(10), ' ')}" for key, value in data.items())


def md_generic_table(rows: Sequence[Any]) -> str:
    normalized: List[Dict[str, Any]] = []
    for item in rows:
        if isinstance(item, dict):
            normalized.append(item)
        else:
            normalized.append({"value": item})
    return md_table(normalized, table_columns_from_rows(normalized)) if normalized else "暂无"


def md_professional_sections(data: Mapping[str, Any]) -> str:
    parts: List[str] = []

    def add(title: str, body: str) -> None:
        parts.append(f"## {title}\n{body}")

    if data.get("executive_summary"):
        add("执行摘要", md_list(as_list(data.get("executive_summary"))))
    if data.get("professional_opinion"):
        add("专业判断", md_list(as_list(data.get("professional_opinion"))))
    if isinstance(data.get("industry_overview"), dict):
        add("产业边界与分析逻辑", md_kv(data["industry_overview"]))
    if data.get("level_definitions"):
        add("L1-L5 层级口径说明", md_generic_table(as_list(data.get("level_definitions"))))
    if isinstance(data.get("project_graph_summary"), dict) and data.get("project_graph_summary"):
        add("项目图谱口径", md_kv(data["project_graph_summary"]))
    if isinstance(data.get("node_mapping"), dict) and data.get("node_mapping"):
        add("项目节点映射", md_kv(data["node_mapping"]))
    if data.get("value_chain"):
        add("产业链结构", md_generic_table(as_list(data.get("value_chain"))))
    if data.get("project_node_records"):
        add("项目节点数据记录", md_generic_table(as_list(data.get("project_node_records"))))
    if data.get("hierarchy_analysis"):
        add("层级结构分析", md_generic_table(as_list(data.get("hierarchy_analysis"))))
    if data.get("analysis_framework"):
        add("分析框架", md_generic_table(as_list(data.get("analysis_framework"))))
    if data.get("key_observations"):
        add("关键观察", md_list(as_list(data.get("key_observations"))))
    if data.get("project_seed_links"):
        add("项目已有候选挂链/锚点", md_generic_table(as_list(data.get("project_seed_links"))))
    if isinstance(data.get("link_summary"), dict) and data.get("link_summary"):
        add("挂链总览", md_kv(data["link_summary"]))
    if isinstance(data.get("fit_assessment"), dict):
        add("企业-节点匹配评估", md_kv(data["fit_assessment"]))
    if isinstance(data.get("enterprise_profile"), dict):
        add("指定企业画像", md_kv(data["enterprise_profile"]))
    if data.get("evidence_summary"):
        add("证据摘要", md_generic_table(as_list(data.get("evidence_summary"))))
    if isinstance(data.get("data_quality"), dict):
        add("数据质量与接口状态", md_kv(data["data_quality"]))
    if data.get("risk_flags"):
        add("风险与复核点", md_list(as_list(data.get("risk_flags"))))
    if data.get("recommendations"):
        add("专业建议", md_list(as_list(data.get("recommendations"))))
    return "\n\n".join(parts)



def render_chain_analysis_markdown(data: Dict[str, Any], title: str) -> str:
    generated_at = dt.datetime.now().strftime("%Y-%m-%d")
    summary = first_present(data, ["abstract", "summary", "overview"], "")
    graph_summary = data.get("project_graph_summary") if isinstance(data.get("project_graph_summary"), dict) else {}
    market_context = [item for item in as_list(data.get("market_context")) if isinstance(item, dict)]
    industry_definition = [item for item in as_list(data.get("industry_definition")) if isinstance(item, dict)]
    segment_rows = [item for item in as_list(data.get("segment_analysis")) if isinstance(item, dict)]
    key_node_rows = [item for item in as_list(data.get("key_node_system")) if isinstance(item, dict)]
    value_flow_rows = [item for item in as_list(data.get("value_flow")) if isinstance(item, dict)]
    structural_rows = [item for item in as_list(data.get("structural_characteristics")) if isinstance(item, dict)]
    definition_columns = [("dimension", "定义维度"), ("content", "本报告界定")]
    level_columns = [("level", "层级"), ("name", "层级名称"), ("definition", "定义口径"), ("granularity", "颗粒度"), ("this_report", "本报告口径"), ("usage", "使用说明")]
    market_columns = [("topic", "主题"), ("finding", "产业背景要点"), ("source", "来源"), ("date", "日期"), ("url", "链接")]
    graph_columns = [("stage", "价值阶段"), ("segment", "L2 价值环节"), ("composition", "L3 产业模块"), ("scale", "节点规模")]
    segment_columns = [("segment", "价值环节"), ("functional_positioning", "功能定位"), ("composition", "产业模块"), ("representative_nodes", "代表性节点"), ("linkage", "上下游关系")]
    key_node_columns = [("l2_segment", "L2 价值环节"), ("l3_module", "L3 产业模块"), ("node_count", "L5 数量"), ("capability_boundary", "能力边界"), ("representative_nodes", "代表性 L5 节点")]
    flow_columns = [("from_segment", "起始环节"), ("to_segment", "承接环节"), ("relationship", "关系类型"), ("transmission_content", "传导内容"), ("transmission_logic", "传导机制")]
    structural_columns = [("feature", "结构特征"), ("evidence", "图谱依据"), ("interpretation", "结构解读")]
    cn_nums = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
    section_index = 0
    def next_heading(title_text: str) -> str:
        nonlocal section_index
        label_text = cn_nums[section_index] if section_index < len(cn_nums) else str(section_index + 1)
        section_index += 1
        return f"{label_text}、{title_text}"

    sections = [
        f"# {title}",
        f"报告日期：{generated_at}",
        "",
        f"## {next_heading('报告摘要')}",
        text(summary),
        "",
        "**报告口径**",
        f"- 产业链：{text(data.get('chain') or '')}",
        f"- 关注节点：{text(data.get('node') or '全产业链')}",
        f"- 节点规模：L2 {text(graph_summary.get('l2_count') or '-')}, L3 {text(graph_summary.get('l3_count') or '-')}, L5 {text(graph_summary.get('l5_count') or '-')}",
        "",
        f"## {next_heading('产业定义与层级口径')}",
        md_table(industry_definition, definition_columns),
        "",
        "### L1-L5 层级定义",
        md_table([row for row in as_list(data.get('level_definitions')) if isinstance(row, dict)], level_columns),
    ]
    if market_context:
        sections.extend(["", f"## {next_heading('产业发展环境')}", md_table(market_context, market_columns)])
    sections.extend([
        "",
        f"## {next_heading('产业链全景图谱')}",
        md_table(segment_rows, graph_columns),
        "",
        f"## {next_heading('价值环节深度解析')}",
        md_table(segment_rows, segment_columns),
        "",
        f"## {next_heading('关键节点与产品技术体系')}",
        md_table(key_node_rows, key_node_columns),
        "",
        f"## {next_heading('价值传导与协同关系')}",
        md_table(value_flow_rows, flow_columns),
        "",
        f"## {next_heading('产业结构特征')}",
        md_table(structural_rows, structural_columns),
    ])
    sections.extend(["", "---", f"产业链层级分析报告 · {generated_at}"])
    return "\n".join(sections) + "\n"


def render_policy_analysis_markdown(data: Dict[str, Any], title: str) -> str:
    generated_at = dt.datetime.now().strftime("%Y-%m-%d")
    query = data.get("policy_query") if isinstance(data.get("policy_query"), dict) else {}
    region_columns = [
        ("region", "地区"),
        ("policy_count", "线索数"),
        ("handaas_policy_count", "旷湖政策库"),
        ("web_policy_count", "联网补充"),
        ("policy_focus", "政策重点"),
        ("key_agencies", "主要机构/来源"),
        ("analysis", "区域政策解读"),
    ]
    dimension_columns = [("dimension", "政策维度"), ("count", "线索数")]
    policy_columns = [
        ("region", "地区"),
        ("title", "政策/信息标题"),
        ("agency", "机构/来源"),
        ("policy_type", "类型"),
        ("publish_date", "日期"),
        ("summary", "摘要"),
        ("url", "链接"),
    ]
    region_rows = [row for row in as_list(data.get("regional_policy_analysis")) if isinstance(row, dict)]
    dimension_rows = [row for row in as_list(data.get("policy_dimensions")) if isinstance(row, dict)]
    policy_items = [row for row in as_list(data.get("policy_items")) if isinstance(row, dict)]
    sections = [
        f"# {title}",
        f"报告日期：{generated_at}",
        "",
        "## 一、报告摘要",
        text(data.get("summary") or ""),
        "",
        "**查询口径**",
        f"- 关键词：{text(data.get('keyword') or data.get('chain') or '-')}",
        f"- 地区：{'、'.join(text(item) for item in as_list(data.get('regions'))) or '-'}",
        f"- 政策类型：{text(query.get('pn_type') or '全部')}",
        f"- 发布时间：{text(query.get('policy_start') or '-')} 至 {text(query.get('policy_end') or '-')}",
        "",
        "## 二、各地政策情况对比",
        md_table(region_rows, region_columns),
        "",
        "## 三、政策支持维度",
        md_table(dimension_rows, dimension_columns),
        "",
        "## 四、代表性政策与联网依据",
        md_table(policy_items[:80], policy_columns),
    ]
    return "\n".join(sections) + "\n"


def render_enterprise_positioning_markdown(data: Dict[str, Any], title: str) -> str:
    generated_at = dt.datetime.now().strftime("%Y-%m-%d")
    profile = data.get("enterprise_profile") if isinstance(data.get("enterprise_profile"), dict) else {}
    primary = data.get("primary_position") if isinstance(data.get("primary_position"), dict) else {}
    chain_rows = [{**item, "confidence": confidence_label(item.get("confidence"))} for item in as_list(data.get("chain_ranking")) if isinstance(item, dict)]
    node_rows = [{**item, "confidence": confidence_label(item.get("confidence"))} for item in as_list(data.get("node_ranking")) if isinstance(item, dict)]
    evidence_rows = [{**item, "status": evidence_status_label(item.get("status"))} for item in as_list(data.get("evidence_summary")) if isinstance(item, dict)]
    match_rows = [item for item in as_list(data.get("evidence_matches")) if isinstance(item, dict)]
    profile_rows = [
        {"name": "企业名称", "value": profile.get("name") or data.get("enterprise") or ""},
        {"name": "经营状态", "value": profile.get("oper_status") or "-"},
        {"name": "工商行业", "value": profile.get("registered_industry") or "-"},
        {"name": "所在地", "value": profile.get("address") or "-"},
        {"name": "主要产品", "value": profile.get("business_products") or "-"},
        {"name": "业务标签", "value": profile.get("business_tags") or "-"},
        {"name": "经营范围", "value": profile.get("business_scope") or "-"},
        {"name": "企业简介", "value": profile.get("profile") or "-"},
    ]
    primary_rows = [
        {"name": "归属判断", "value": primary.get("status") or "证据不足"},
        {"name": "置信度", "value": confidence_label(primary.get("confidence"))},
        {"name": "综合匹配分", "value": primary.get("score") or 0},
        {"name": "产业链", "value": primary.get("chain") or "-"},
        {"name": "L2 价值环节", "value": primary.get("l2_segment") or "-"},
        {"name": "L3 产业模块", "value": primary.get("l3_module") or "-"},
        {"name": "L5 标准节点", "value": primary.get("l5_node") or "-"},
        {"name": "完整路径", "value": primary.get("path") or "-"},
        {"name": "主要证据", "value": primary.get("evidence_sources") or "-"},
        {"name": "关键命中", "value": primary.get("matched_terms") or "-"},
    ]
    chain_columns = [("chain", "产业链"), ("score", "匹配分"), ("confidence", "置信度"), ("best_node", "最佳节点"), ("candidate_nodes", "候选节点"), ("evidence_sources", "主要证据")]
    node_columns = [("chain", "产业链"), ("l2_segment", "L2 环节"), ("l3_module", "L3 模块"), ("l5_node", "L5 节点"), ("score", "匹配分"), ("confidence", "置信度"), ("evidence_sources", "证据来源"), ("matched_terms", "命中词")]
    evidence_columns = [("source", "证据来源"), ("status", "状态"), ("signal_count", "有效信号"), ("representative_evidence", "代表性证据")]
    match_columns = [("source", "证据来源"), ("match_type", "匹配方式"), ("matched_term", "命中内容"), ("score", "证据分"), ("snippet", "证据摘要")]
    sections = [
        f"# {title}",
        f"报告日期：{generated_at}",
        "",
        "## 报告摘要",
        text(data.get("summary") or ""),
        "",
        "## 一、企业基本画像",
        md_table(profile_rows, [("name", "画像维度"), ("value", "企业信息")]),
        "",
        "## 二、主归属产业链环节",
        md_table(primary_rows, [("name", "定位维度"), ("value", "定位结果")]),
        "",
        "## 三、候选产业链对比",
        md_table(chain_rows, chain_columns),
        "",
        "## 四、候选节点匹配",
        md_table(node_rows, node_columns),
        "",
        "## 五、证据覆盖与关键命中",
        md_table(evidence_rows, evidence_columns),
    ]
    if match_rows:
        sections.extend(["", "### 主归属节点证据", md_table(match_rows, match_columns)])
    sections.extend(["", "## 六、定位边界说明", md_list(as_list(data.get("positioning_boundary"))), "", "---", f"企业产业链定位分析报告 · {generated_at}"])
    return "\n".join(sections) + "\n"


def render_enterprise_node_analysis_markdown(data: Dict[str, Any], title: str) -> str:
    generated_at = dt.datetime.now().strftime("%Y-%m-%d")
    profile = data.get("enterprise_profile") if isinstance(data.get("enterprise_profile"), Mapping) else {}
    mapping = data.get("node_mapping") if isinstance(data.get("node_mapping"), Mapping) else {}
    fit = data.get("fit_assessment") if isinstance(data.get("fit_assessment"), Mapping) else {}
    evidence_rows = [
        {**item, "status": evidence_status_label(item.get("status")), "signal_strength": strength_label(item.get("signal_strength"))}
        for item in as_list(data.get("evidence_summary")) if isinstance(item, Mapping)
    ]
    fit_rows = [
        {"dimension": "目标产业链", "value": data.get("chain") or "-"},
        {"dimension": "目标节点", "value": fit.get("project_node") or fit.get("target_node") or data.get("node") or "-"},
        {"dimension": "标准路径", "value": fit.get("project_node_path") or mapping.get("primary_project_path") or "-"},
        {"dimension": "挂链判断", "value": decision_label(fit.get("decision"))},
        {"dimension": "证据强度", "value": strength_label(fit.get("evidence_strength"))},
        {"dimension": "综合匹配分", "value": f"{fit.get('fit_score') or 0}/100"},
        {"dimension": "判定依据", "value": fit.get("reason") or "-"},
    ]
    return "\n".join([
        f"# {title}", f"报告日期：{generated_at}", "", "## 报告摘要", text(data.get("summary") or ""),
        "", "## 一、企业基本画像", md_kv(profile),
        "", "## 二、产业链节点定位", md_table(fit_rows, [("dimension", "定位维度"), ("value", "定位结果")]),
        "", "## 三、项目节点映射", md_kv(mapping),
        "", "## 四、证据核验", md_table(evidence_rows, [("product", "证据来源"), ("status", "状态"), ("signal_strength", "强度"), ("matched_keywords", "命中内容"), ("key_findings", "主要发现"), ("data_points", "关键数据")]),
        "", "## 五、判断边界", md_list(as_list(data.get("risk_flags"))),
        "", "---", f"企业产业链节点分析报告 · {generated_at}",
    ]) + "\n"


def render_node_linking_markdown(data: Dict[str, Any], title: str) -> str:
    generated_at = dt.datetime.now().strftime("%Y-%m-%d")
    summary = data.get("link_summary") if isinstance(data.get("link_summary"), Mapping) else {}
    route_rows = [item for item in as_list((data.get("preview") or {}).get("route_results") if isinstance(data.get("preview"), Mapping) else []) if isinstance(item, Mapping)]
    if not route_rows and isinstance(data.get("search_plan"), Mapping):
        route_rows = [item for item in as_list(data["search_plan"].get("recall_routes")) if isinstance(item, Mapping)]
    route_rows = [{**item, "route_id": route_label(item.get("route_id") or item.get("id"))} for item in route_rows]
    decisions = delivery_decision_rows(data)
    decision_columns = [("enterprise_name", "企业"), ("review_score", "复核分"), ("evidence_strength", "证据强度"), ("evidence_source_count", "有效来源"), ("strong_source_count", "强来源"), ("evidence_sources", "证据构成"), ("reason", "判定依据")]
    target_rows = [
        {"dimension": "产业链", "value": data.get("chain") or "-"},
        {"dimension": "L5节点", "value": data.get("node") or "-"},
        {"dimension": "标准路径", "value": " > ".join(str(item) for item in as_list(data.get("path"))) or "-"},
        {"dimension": "候选企业", "value": summary.get("candidate_count") or 0},
        {"dimension": "确认挂链", "value": summary.get("confirmed") or 0},
        {"dimension": "待复核", "value": summary.get("manual_review") or 0},
        {"dimension": "排除", "value": summary.get("rejected") or 0},
    ]
    sections = [
        f"# {title}", f"报告日期：{generated_at}", "", "## 报告摘要", text(data.get("summary") or f"围绕“{data.get('node') or ''}”节点完成企业召回与证据复核。"),
        "", "## 一、挂链对象与结果总览", md_table(target_rows, [("dimension", "维度"), ("value", "结果")]),
        "", "## 二、召回路线表现", md_table(route_rows, [("route_id", "路线"), ("purpose", "筛选逻辑"), ("priority", "优先级"), ("total", "候选总量"), ("sample_count", "抽样数量")]),
    ]
    for heading, label_value in (("三、确认挂链企业", "确认挂链"), ("四、待复核企业", "待复核"), ("五、排除企业", "不建议挂链")):
        sections.extend(["", f"## {heading}", md_table([item for item in decisions if item.get("decision") == label_value], decision_columns)])
    sections.extend(["", "---", f"产业链节点企业挂链报告 · {generated_at}"])
    return "\n".join(sections) + "\n"


def render_chain_linking_markdown(data: Dict[str, Any], title: str) -> str:
    generated_at = dt.datetime.now().strftime("%Y-%m-%d")
    summary = data.get("summary") if isinstance(data.get("summary"), Mapping) else {}
    node_rows: List[Dict[str, Any]] = []
    enterprise_rows: List[Dict[str, Any]] = []
    for node in as_list(data.get("nodes")):
        if not isinstance(node, Mapping):
            continue
        reviewed = [item for item in as_list(node.get("reviewed_enterprises")) if isinstance(item, Mapping)]
        route_ids = [
            str(item.get("id") or item.get("route_id") or "") if isinstance(item, Mapping) else str(item or "")
            for item in as_list(node.get("recall_routes"))
        ]
        route_ids = [item for item in route_ids if item]
        node_rows.append({
            "node": node.get("node") or "", "path": " > ".join(str(item) for item in as_list(node.get("path"))),
            "candidate_count": node.get("candidate_count") or 0, "confirmed": node.get("confirmed") or 0,
            "manual_review": node.get("manual_review") or 0, "rejected": node.get("rejected") or 0,
            "recall_route_count": len(route_ids), "recall_routes": "、".join(route_label(item) for item in route_ids) or "-",
            "confirmed_enterprises": "、".join(str(item.get("enterprise_name") or "") for item in reviewed if item.get("decision") == "confirmed") or "-",
        })
        for item in reviewed:
            enterprise_rows.append({
                "node": node.get("node") or "", "enterprise_name": item.get("enterprise_name") or "",
                "decision": decision_label(item.get("decision")), "review_score": item.get("review_score") or 0,
                "evidence_source_count": item.get("evidence_source_count") or 0, "strong_source_count": item.get("strong_source_count") or 0,
                "reason": item.get("reason") or "",
            })
    overview = [
        {"dimension": "完成节点", "value": summary.get("completed_nodes") or 0},
        {"dimension": "失败节点", "value": summary.get("failed_nodes") or 0},
        {"dimension": "候选企业", "value": summary.get("candidate_count") or 0},
        {"dimension": "确认挂链", "value": summary.get("confirmed") or 0},
        {"dimension": "待复核", "value": summary.get("manual_review") or 0},
        {"dimension": "排除", "value": summary.get("rejected") or 0},
    ]
    node_columns = [("node", "L5节点"), ("path", "标准路径"), ("recall_route_count", "路线数"), ("recall_routes", "召回路线"), ("candidate_count", "候选"), ("confirmed", "确认"), ("manual_review", "待复核"), ("rejected", "排除"), ("confirmed_enterprises", "确认企业")]
    enterprise_columns = [("node", "L5节点"), ("enterprise_name", "企业"), ("decision", "判断"), ("review_score", "复核分"), ("evidence_source_count", "有效来源"), ("strong_source_count", "强来源"), ("reason", "判定依据")]
    sections = [
        f"# {title}", f"报告日期：{generated_at}", "", "## 报告摘要", text(data.get("report_summary") or f"围绕“{data.get('chain') or ''}”产业链开展节点企业挂链分析。"),
        "", "## 一、挂链结果总览", md_table(overview, [("dimension", "维度"), ("value", "结果")]),
        "", "## 二、节点覆盖明细", md_table(node_rows, node_columns),
        "", "## 三、企业挂链明细", md_table(enterprise_rows, enterprise_columns),
    ]
    failures = [item for item in as_list(data.get("failures")) if isinstance(item, Mapping)]
    if failures:
        sections.extend(["", "## 四、未完成节点", md_table(failures, [("node", "节点"), ("path", "路径"), ("error", "原因")])])
    sections.extend(["", "---", f"产业链节点企业挂链总报告 · {generated_at}"])
    return "\n".join(sections) + "\n"


def render_markdown(data: Dict[str, Any], title: str) -> str:
    if str(data.get("report_type") or "") == "industry_chain_analysis":
        return render_chain_analysis_markdown(data, title)
    if str(data.get("report_type") or "") == "policy_analysis":
        return render_policy_analysis_markdown(data, title)
    if str(data.get("report_type") or "") == "enterprise_chain_positioning":
        return render_enterprise_positioning_markdown(data, title)
    if str(data.get("report_type") or "") == "enterprise_node_analysis":
        return render_enterprise_node_analysis_markdown(data, title)
    if str(data.get("report_type") or "") == "enterprise_node_linking":
        return render_node_linking_markdown(data, title)
    if str(data.get("report_type") or "") == "industry_chain_linking":
        return render_chain_linking_markdown(data, title)
    industry_map = as_list(first_present(data, ["industry_map", "map", "ontology", "industry_structure"], []))
    priority_segments = as_list(first_present(data, ["priority_segments", "segments", "focus_segments"], []))
    search_strategy = as_list(first_present(data, ["search_strategy", "strategy", "search_plan"], []))
    next_actions = as_list(first_present(data, ["next_actions", "actions", "recommendations"], []))
    candidates = normalize_candidates(data)
    decisions = normalize_decisions(data)
    summary = first_present(data, ["summary", "conclusion", "overview"], "")
    candidate_columns = [("name", "企业"), ("id", "ID"), ("socialCreditCode", "统一社会信用代码"), ("regCapital", "注册资本")]
    decision_columns = [("enterprise_name", "企业"), ("matched_segment", "匹配环节"), ("decision", "判断"), ("evidence_strength", "证据强度"), ("reason", "原因"), ("next_action", "下一步")]
    sections = [
        f"# {title}",
        f"生成时间：{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "## 结论摘要\n" + (text(summary) or "本报告根据输入结果展示产业链结构、企业搜索策略、候选企业和证据化判断。"),
    ]
    professional = md_professional_sections(data)
    if professional:
        sections.append(professional)
    if industry_map or priority_segments:
        sections.append("## 产业链结构与重点环节\n" + md_list(industry_map or priority_segments))
    if search_strategy:
        sections.append("## 企业搜索策略\n" + md_list(search_strategy))
    if candidates:
        sections.append("## 候选企业\n" + md_table(candidates, candidate_columns))
    if decisions:
        sections.append("## 证据化判断\n" + md_table(decisions, decision_columns))
    if next_actions:
        sections.append("## 下一步建议\n" + md_list(next_actions))
    return "\n\n".join(sections) + "\n"


def write_report(
    data: Dict[str, Any],
    output_path: str | pathlib.Path,
    *,
    fmt: str | None = None,
    title: str | None = None,
) -> Dict[str, Any]:
    output = pathlib.Path(output_path).expanduser()
    resolved_format = fmt or ("markdown" if output.suffix.lower() in {".md", ".markdown"} else "html")
    report_title = infer_title(data, title)
    rendered = render_markdown(data, report_title) if resolved_format in {"markdown", "md"} else render_html(data, report_title)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    return {
        "ok": True,
        "format": "markdown" if resolved_format in {"markdown", "md"} else "html",
        "output": str(output),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Render an industry-chain analysis result as HTML or Markdown.")
    parser.add_argument("--input", help="Analysis result JSON. Reads stdin when omitted.")
    parser.add_argument("--output", required=True, help="Output report path, e.g. /tmp/report.html or /tmp/report.md")
    parser.add_argument("--format", choices=["html", "markdown", "md"], help="Output format. Defaults from file extension.")
    parser.add_argument("--title", help="Report title.")
    args = parser.parse_args()

    data = load_payload(args.input)
    title = infer_title(data, args.title)
    print(json_dumps(write_report(data, args.output, fmt=args.format, title=title), pretty=True))


if __name__ == "__main__":
    main()
