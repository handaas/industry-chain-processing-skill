#!/usr/bin/env python3
"""Compose a project-aware industry-chain analysis report payload.

This report is intentionally about industry hierarchy and analysis only. It does
not require enterprise recall, enterprise evidence, or enterprise-node linking.
Use link_enterprises.py / enterprise_node_report.py for those separate workflows.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping

from common import json_dumps, print_json
from enterprise_search_preview import extract_keywords_from_condition
from project_context import build_project_context


def as_list(value: Any) -> List[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    return [value]


def load_json(path: str) -> Dict[str, Any]:
    data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("输入必须是 JSON object")
    return data


def load_market_context(path: str | None = None, notes: List[str] | None = None) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if path:
        raw = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            raw_items = raw.get("market_context") or raw.get("sources") or raw.get("items") or []
        elif isinstance(raw, list):
            raw_items = raw
        else:
            raw_items = []
        for item in raw_items:
            if isinstance(item, dict):
                items.append({
                    "topic": str(item.get("topic") or item.get("title") or "产业背景"),
                    "finding": str(item.get("finding") or item.get("summary") or item.get("content") or ""),
                    "source": str(item.get("source") or item.get("publisher") or ""),
                    "url": str(item.get("url") or item.get("link") or item.get("source_url") or ""),
                    "date": str(item.get("date") or item.get("published_at") or ""),
                })
            else:
                items.append({"topic": "产业背景", "finding": str(item), "source": "", "url": "", "date": ""})
    for note in notes or []:
        parts = [part.strip() for part in str(note).split("|")]
        items.append({
            "topic": parts[0] if len(parts) > 0 and parts[0] else "产业背景",
            "finding": parts[1] if len(parts) > 1 else str(note),
            "source": parts[2] if len(parts) > 2 else "",
            "url": parts[3] if len(parts) > 3 else "",
            "date": parts[4] if len(parts) > 4 else "",
        })
    return [item for item in items if item.get("finding")][:12]


def compact_text(value: Any, limit: int = 130) -> str:
    text = " ".join(str(value or "").replace("\n", " ").split()).strip(" ；;。")
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip("，,；;。 ") + "…"


def unique_nonempty(values: List[Any], limit: int = 6) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for value in values:
        item = str(value or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
        if len(out) >= limit:
            break
    return out


def parse_path(value: str | None, chain: str, node: str) -> List[str]:
    if value:
        return [part.strip() for part in str(value).replace("/", ">").split(">") if part.strip()]
    return [part for part in [chain, node] if part]


def build_value_chain(chain: str, node: str, path: List[str]) -> List[Dict[str, Any]]:
    """Fallback value-chain rows when project graph is unavailable."""
    focus = node or (path[-1] if len(path) > 1 else "") or f"{chain}核心产品"
    upstream_modules = ["核心材料与关键零部件", "研发工具与基础设施"]
    upstream_nodes = ["核心材料", "关键零部件", "基础软件", "研发工具链"]
    core_modules = ["核心产品与关键技术", "系统平台与解决方案"]
    core_nodes = unique_nonempty([focus, f"{focus}关键技术", f"{focus}系统平台", f"{focus}解决方案"], limit=6)
    downstream_modules = ["系统集成与场景应用", "运营服务与终端市场"]
    downstream_nodes = ["系统集成服务", "行业应用方案", "运营服务", "终端产品与项目"]
    if "汽车" in chain or "自动驾驶" in node:
        upstream_modules = ["车规芯片与传感器", "计算平台与测试工具"]
        upstream_nodes = ["车规芯片", "环境感知传感器", "域控与计算平台", "地图定位", "仿真测试", "数据闭环工具"]
        downstream_modules = ["整车与系统集成", "出行物流与示范应用"]
        downstream_nodes = ["智能整车", "Robotaxi/Robobus", "干线物流", "园区港口矿山", "智能网联示范区"]

    def row(segment: str, modules: List[str], nodes: List[str], analysis: str) -> Dict[str, Any]:
        clean_modules = unique_nonempty(modules, limit=8)
        clean_nodes = unique_nonempty(nodes, limit=12)
        return {
            "segment": segment,
            "l2_segment": segment,
            "role": "、".join(clean_modules),
            "l3_segments": "、".join(clean_modules),
            "l5_samples": "、".join(clean_nodes),
            "l3_count": len(clean_modules),
            "l5_count": len(clean_nodes),
            "analysis": analysis,
        }

    return [
        row("上游：基础要素与核心支撑", upstream_modules, upstream_nodes, "分析核心投入、技术门槛、国产替代空间和供应约束。"),
        row("中游：核心产品与系统集成", core_modules, core_nodes, "分析产品/技术边界、产业价值位置、关键能力和与相邻环节的接口关系。"),
        row("下游：场景应用与运营服务", downstream_modules, downstream_nodes, "分析商业化场景、需求来源、项目落地路径和生态协同关系。"),
    ]


def project_graph_summary(project: Mapping[str, Any]) -> Dict[str, Any]:
    if not project.get("available"):
        return {}
    chain_info = project.get("chain") or {}
    stats = project.get("stats") or {}
    summary = {
        "canonical_chain_name": chain_info.get("name"),
        "chain_id": chain_info.get("id") or "",
        "source": project.get("source"),
        "source_type": chain_info.get("source_type") or "",
        "node_count": chain_info.get("node_count") or stats.get("l5"),
        "enterprise_count_cache": chain_info.get("enterprise_count_cache") or "",
        "updated_at": chain_info.get("updated_at") or "",
        "l2_count": stats.get("l2"),
        "l3_count": stats.get("l3"),
        "l5_count": stats.get("l5"),
    }
    if project.get("source_chains"):
        summary["composite_sources"] = "、".join(str(item) for item in project.get("source_chains") or [])
    return summary


def project_node_rows(project: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item in project.get("matched_nodes") or []:
        rows.append({
            "node_name": item.get("node_name"),
            "path": " > ".join(item.get("path") or []),
            "condition_source": item.get("condition_source") or "暂无",
            "condition_keywords": "、".join(item.get("condition_keywords") or []),
            "node_id": item.get("node_id") or "",
        })
    return rows


def value_chain_to_industry_map(value_chain: List[Mapping[str, Any]], chain: str) -> List[str]:
    if not value_chain:
        return [f"{chain}：暂无项目图谱层级，需补充 L2/L3/L5 结构。"]
    rows: List[str] = []
    for item in value_chain:
        l2 = item.get("l2_segment") or item.get("segment") or "未命名环节"
        l3 = item.get("l3_segments") or item.get("role") or ""
        l5 = item.get("l5_samples") or ""
        if l5:
            rows.append(f"{l2}：覆盖 L3 {item.get('l3_count', '')} 个、L5 {item.get('l5_count', '')} 个；典型 L5：{l5}")
        else:
            rows.append(f"{l2}：{l3}")
    return rows


def project_graph_tree(project: Mapping[str, Any], chain: str) -> Dict[str, Any]:
    """Build a L2/L3/L5 tree for static graph rendering."""
    sections: List[Dict[str, Any]] = []
    l2_index: Dict[str, Dict[str, Any]] = {}
    l3_index: Dict[tuple[str, str], Dict[str, Any]] = {}
    for item in project.get("l5_nodes") or []:
        path = [str(part) for part in (item.get("path") or []) if str(part or "").strip()]
        if len(path) < 4:
            continue
        l2, l3, l5 = path[1], path[2], path[-1]
        if not l2 or not l3 or not l5:
            continue
        section = l2_index.get(l2)
        if not section:
            section = {"name": l2, "children": []}
            l2_index[l2] = section
            sections.append(section)
        sub_key = (l2, l3)
        subsection = l3_index.get(sub_key)
        if not subsection:
            subsection = {"name": l3, "children": []}
            l3_index[sub_key] = subsection
            section["children"].append(subsection)
        if not any(str(child.get("name") or "") == l5 for child in subsection["children"]):
            subsection["children"].append({"name": l5})

    if not sections:
        for item in project.get("value_chain") or []:
            l2 = str(item.get("l2_segment") or item.get("segment") or "").strip()
            if not l2:
                continue
            l3_names = split_names(item.get("l3_segments") or item.get("role"), limit=10)
            l5_names = split_names(item.get("l5_samples"), limit=20)
            if not l3_names:
                l3_names = ["核心产品与技术"]
            if not l5_names:
                l5_names = [f"{name}代表产品与技术" for name in l3_names]
            grouped: List[List[str]] = [[] for _ in l3_names]
            for index, name in enumerate(l5_names):
                grouped[index % len(grouped)].append(name)
            children = [
                {
                    "name": l3,
                    "children": [{"name": name} for name in (grouped[index] or [f"{l3}代表产品与技术"])],
                }
                for index, l3 in enumerate(l3_names)
            ]
            sections.append({"name": l2, "children": children})
    return {"name": chain, "children": sections}


def graph_tree_stats(tree: Mapping[str, Any]) -> Dict[str, int]:
    l2_count = 0
    l3_count = 0
    l5_count = 0
    for l2 in as_list(tree.get("children")):
        if not isinstance(l2, Mapping) or not str(l2.get("name") or "").strip():
            continue
        l2_count += 1
        for l3 in as_list(l2.get("children")):
            if not isinstance(l3, Mapping) or not str(l3.get("name") or "").strip():
                continue
            l3_count += 1
            l5_count += sum(
                1
                for l5 in as_list(l3.get("children"))
                if isinstance(l5, Mapping) and str(l5.get("name") or "").strip()
            )
    return {"l2": l2_count, "l3": l3_count, "l5": l5_count}


def graph_tree_is_complete(tree: Mapping[str, Any]) -> bool:
    sections = [item for item in as_list(tree.get("children")) if isinstance(item, Mapping)]
    if not sections:
        return False
    for section in sections:
        if not str(section.get("name") or "").strip():
            return False
        modules = [item for item in as_list(section.get("children")) if isinstance(item, Mapping)]
        if not modules:
            return False
        for module in modules:
            if not str(module.get("name") or "").strip():
                return False
            leaves = [item for item in as_list(module.get("children")) if isinstance(item, Mapping) and str(item.get("name") or "").strip()]
            if not leaves:
                return False
    stats = graph_tree_stats(tree)
    return stats["l2"] > 0 and stats["l3"] > 0 and stats["l5"] > 0


def level_definition_rows(canonical_chain: str, node: str, graph_summary: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Detailed L1-L5 interpretation口径 for the report."""
    l2_count = graph_summary.get("l2_count") or "若干"
    l3_count = graph_summary.get("l3_count") or "若干"
    l5_count = graph_summary.get("l5_count") or "若干"
    focus = node or "具体产品/技术/服务节点"
    return [
        {
            "level": "L1",
            "name": "产业链主题 / 分析边界",
            "definition": "定义本报告讨论的产业链总体范围，回答“分析哪条产业链、边界到哪里为止”。",
            "granularity": "行业级或赛道级。",
            "this_report": f"本报告 L1 为“{canonical_chain}”。",
            "usage": "用于确定后续 L2/L3/L4/L5 的归属边界，避免把相邻产业、应用场景或支撑能力混入同一分析层级。",
        },
        {
            "level": "L2",
            "name": "价值环节 / 主链条分工",
            "definition": "把 L1 拆成若干价值创造环节，表达产业链中的主要分工、上游支撑、中游集成、下游应用或行业特有价值段。",
            "granularity": "价值环节级。",
            "this_report": f"当前项目图谱约包含 {l2_count} 个 L2 价值环节。",
            "usage": "用于观察产业链的横向分工、供需承接和价值传导关系。",
        },
        {
            "level": "L3",
            "name": "产业模块 / 业务系统",
            "definition": "在 L2 下继续拆分为可理解的产业模块、系统、场景或业务子链，回答“这个价值环节由哪些模块构成”。",
            "granularity": "模块级或系统级。",
            "this_report": f"当前项目图谱约包含 {l3_count} 个 L3 产业模块。",
            "usage": "用于承接 L2 与 L5，帮助解释 L5 节点为何属于某一价值环节。",
        },
        {
            "level": "L4",
            "name": "细分方向 / 能力组（兼容层）",
            "definition": "位于 L3 与 L5 之间的可选解释层，用于表达技术路线、能力组、应用方向、产品族或场景簇。",
            "granularity": "方向级或能力组级。",
            "this_report": "当前项目多数图谱未单独落 L4 节点，实际展示为 L3 直接连接 L5；报告保留 L4 口径用于解释和未来扩展。",
            "usage": "当 L3 下 L5 过多或需要按技术路线/应用方向再分组时，可启用 L4；未启用时不强行补造层级。",
        },
        {
            "level": "L5",
            "name": "标准产品 / 技术 / 服务 / 能力节点",
            "definition": "最细的标准产业链节点，应能对应具体产品、技术、服务、材料、设备、平台、解决方案或可验证能力。",
            "granularity": "可匹配企业的终端节点级。",
            "this_report": f"当前项目图谱约包含 {l5_count} 个 L5 标准节点；本次关注“{focus}”相关 L5 映射。",
            "usage": "用于统一最细颗粒度的产业节点口径，并解释其在上游支撑、中游集成或下游应用中的位置与作用。",
        },
    ]


def hierarchy_analysis_rows(value_chain: List[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for index, item in enumerate(value_chain):
        l2 = item.get("l2_segment") or item.get("segment") or f"环节{index + 1}"
        rows.append({
            "segment": l2,
            "analysis": item.get("analysis") or f"该环节连接 {item.get('l3_count', 0)} 个 L3 模块与 {item.get('l5_count', 0)} 个 L5 节点，是理解产业分工和价值传导的关键层级。",
            "l3_segments": item.get("l3_segments") or "",
            "l5_samples": item.get("l5_samples") or "",
        })
    return rows


def split_names(value: Any, limit: int = 12) -> List[str]:
    text = str(value or "").replace("；", "、")
    parts: List[str] = []
    current: List[str] = []
    depth = 0
    for char in text:
        if char in "（([":
            depth += 1
        elif char in "）)]" and depth > 0:
            depth -= 1
        if char == "、" and depth == 0:
            item = "".join(current).strip()
            if item:
                parts.append(item)
            current = []
            continue
        current.append(char)
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return unique_nonempty(parts, limit=limit)


def segment_stage(segment: str) -> str:
    prefix = str(segment or "").replace(":", "：").split("：", 1)[0].strip()
    if prefix in {"上游", "中游", "下游"}:
        return prefix
    if "上游" in prefix:
        return "上游"
    if "下游" in prefix:
        return "下游"
    if "核心" in prefix or "中游" in prefix:
        return "中游"
    return "产业环节"


def segment_functional_positioning(segment: str, stage: str) -> str:
    if stage == "上游":
        return "承担核心部件、基础技术与检测能力供给，决定中游系统的性能上限、可靠性基础和供应保障水平。"
    if stage == "下游":
        return "承接装备、软件与平台能力，通过系统集成和行业场景转化形成智能工厂及数字化生产的实际应用价值。"
    if any(keyword in segment for keyword in ("软件", "平台", "数据", "信息")):
        return "连接设备层与经营管理层，承担数据汇聚、模型计算、生产协同和业务决策，是产业链数字化贯通的中枢。"
    if any(keyword in segment for keyword in ("装备", "工艺", "制造", "机器人", "母机")):
        return "将基础部件、控制能力和工艺知识集成为可执行的生产装备与自动化单元，是制造能力形成的核心载体。"
    return "承接上游专业能力并形成系统化产品、技术或服务，推动产业价值向应用端传递。"


def segment_linkage(stage: str) -> str:
    if stage == "上游":
        return "通过芯片、传感、测量、控制等能力向装备、自动化系统和数字平台提供底层支撑。"
    if stage == "下游":
        return "通过方案集成、车间改造和运营服务吸收中游能力，并以生产效率、质量、柔性和能碳绩效体现产业价值。"
    return "向上整合核心部件与基础技术，向下输出装备能力、工艺模型、生产数据和系统解决方案。"


def segment_analysis_rows(value_chain: List[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for index, item in enumerate(value_chain):
        segment = str(item.get("l2_segment") or item.get("segment") or f"价值环节{index + 1}")
        stage = segment_stage(segment)
        modules = split_names(item.get("l3_segments") or item.get("role"), limit=8)
        nodes = split_names(item.get("l5_samples"), limit=10)
        l3_count = item.get("l3_count") or len(modules)
        l5_count = item.get("l5_count") or len(nodes)
        rows.append({
            "segment": segment,
            "stage": stage,
            "functional_positioning": segment_functional_positioning(segment, stage),
            "composition": "、".join(modules) or "按核心能力与业务模块展开",
            "representative_nodes": "、".join(nodes) or "按产品、技术、服务或能力节点展开",
            "scale": f"L3 {l3_count} 个；L5 {l5_count} 个",
            "linkage": segment_linkage(stage),
        })
    return rows


def module_capability_boundary(module: str) -> str:
    if any(keyword in module for keyword in ("芯片", "电子", "半导体")):
        return "提供计算、控制与功率转换等电子基础能力。"
    if any(keyword in module for keyword in ("传感", "检测", "测量", "质量")):
        return "实现生产状态感知、测量检测与质量反馈。"
    if any(keyword in module for keyword in ("软件", "平台", "数据", "信息")):
        return "承担数据连接、模型计算、业务协同与生产决策。"
    if any(keyword in module for keyword in ("机床", "机器人", "装备", "激光", "制造")):
        return "形成加工、装配、搬运或特种工艺的可执行生产能力。"
    if any(keyword in module for keyword in ("场景", "运营", "服务", "应用", "集成")):
        return "将多类技术能力组合为面向工厂和行业场景的系统方案。"
    return "在所属价值环节内形成相对独立的产品技术与服务能力。"


def key_node_system_rows(graph_tree: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for l2 in as_list(graph_tree.get("children")):
        if not isinstance(l2, Mapping):
            continue
        l2_name = str(l2.get("name") or "价值环节")
        for l3 in as_list(l2.get("children")):
            if not isinstance(l3, Mapping):
                continue
            module = str(l3.get("name") or "产业模块")
            nodes = unique_nonempty([
                node.get("name")
                for node in as_list(l3.get("children"))
                if isinstance(node, Mapping)
            ], limit=8)
            rows.append({
                "l2_segment": l2_name,
                "l3_module": module,
                "node_count": len(as_list(l3.get("children"))),
                "representative_nodes": "、".join(nodes) or "暂无标准节点",
                "capability_boundary": module_capability_boundary(module),
            })
    return rows


def value_flow_rows(value_chain: List[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for index in range(len(value_chain) - 1):
        current = value_chain[index]
        following = value_chain[index + 1]
        source = str(current.get("l2_segment") or current.get("segment") or f"环节{index + 1}")
        target = str(following.get("l2_segment") or following.get("segment") or f"环节{index + 2}")
        source_stage = segment_stage(source)
        target_stage = segment_stage(target)
        if source_stage == "上游" and target_stage == "中游":
            relationship = "基础供给"
            logic = "核心部件、感知测量与控制能力进入装备和工艺系统，形成可执行的生产能力。"
        elif source_stage == "中游" and target_stage == "中游":
            relationship = "系统协同"
            logic = "装备运行、工艺控制与生产数据在软件平台中汇聚，实现设备层、控制层和管理层协同。"
        elif source_stage == "中游" and target_stage == "下游":
            relationship = "集成转化"
            logic = "装备、软件和平台能力组合为车间、工厂及行业解决方案，并在具体生产场景中形成价值闭环。"
        else:
            relationship = "价值承接"
            logic = "前序环节的产品技术与服务能力进入后续环节，形成连续的供需承接和能力组合。"
        rows.append({
            "from_segment": source,
            "to_segment": target,
            "relationship": relationship,
            "transmission_content": "、".join(split_names(current.get("l3_segments") or current.get("role"), limit=4)),
            "transmission_logic": logic,
        })
    return rows


def structural_characteristic_rows(
    canonical_chain: str,
    graph_summary: Mapping[str, Any],
    value_chain: List[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    l2_count = graph_summary.get("l2_count") or len(value_chain)
    l3_count = graph_summary.get("l3_count") or sum(int(item.get("l3_count") or 0) for item in value_chain)
    l5_count = graph_summary.get("l5_count") or sum(int(item.get("l5_count") or 0) for item in value_chain)
    largest = max(value_chain, key=lambda item: int(item.get("l5_count") or 0), default={})
    largest_name = largest.get("l2_segment") or largest.get("segment") or "核心环节"
    largest_count = largest.get("l5_count") or 0
    middle = [str(item.get("l2_segment") or item.get("segment") or "") for item in value_chain if segment_stage(str(item.get("l2_segment") or item.get("segment") or "")) == "中游"]
    downstream = [str(item.get("l2_segment") or item.get("segment") or "") for item in value_chain if segment_stage(str(item.get("l2_segment") or item.get("segment") or "")) == "下游"]
    return [
        {
            "feature": "多层级专业分工",
            "evidence": f"图谱包含 {l2_count} 个 L2、{l3_count} 个 L3 和 {l5_count} 个 L5 节点。",
            "interpretation": f"“{canonical_chain}”不是单一装备或软件赛道，而是由基础供给、系统集成和应用服务共同构成的复合型产业体系。",
        },
        {
            "feature": "核心能力集中",
            "evidence": f"“{largest_name}”覆盖 {largest_count} 个 L5 标准节点，为节点数量最集中的价值环节。",
            "interpretation": "节点密度反映该环节承载的产品技术类型更丰富，也是上下游能力组合和分工最复杂的区域。",
        },
        {
            "feature": "装备与数字能力协同",
            "evidence": f"中游由{'、'.join(middle) or '核心系统环节'}共同构成。",
            "interpretation": "产业价值形成依赖物理装备、工艺控制、工业软件和数据平台协同，单点自动化难以覆盖完整生产闭环。",
        },
        {
            "feature": "应用端形成价值闭环",
            "evidence": f"下游以{'、'.join(downstream) or '行业应用与运营服务'}承接产业能力。",
            "interpretation": "上游与中游能力最终通过工厂建设、车间改造、质量追溯、供应链协同和绿色制造等场景体现应用价值。",
        },
    ]


def industry_definition_rows(
    canonical_chain: str,
    node: str,
    graph_summary: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    sources = str(graph_summary.get("composite_sources") or "").strip()
    graph_scope = (
        f"覆盖 {graph_summary.get('l2_count', '若干')} 个价值环节、{graph_summary.get('l3_count', '若干')} 个产业模块和"
        f" {graph_summary.get('l5_count', '若干')} 个标准节点。"
    )
    if sources:
        graph_scope += f"产业基础覆盖{sources}等相关链条。"
    return [
        {"dimension": "产业定义", "content": f"以“{canonical_chain}”作为产业链总体对象，观察从基础供给到系统集成、再到行业应用的完整价值体系。"},
        {"dimension": "分析边界", "content": "纳入材料、部件、设备、软件、平台、解决方案与应用服务等产业节点，按其价值功能确定层级归属。"},
        {"dimension": "层级体系", "content": "L1 定义产业主题，L2 表达价值环节，L3 表达产业模块，L4 作为可选细分方向，L5 表达标准产品、技术、服务或能力节点。"},
        {"dimension": "图谱范围", "content": graph_scope},
        {"dimension": "重点范围", "content": f"重点分析“{node}”相关节点及其上下游关系。" if node else "覆盖全产业链主要价值环节、产业模块和代表性产品技术节点。"},
    ]


def summarize_market_context(market_context: List[Mapping[str, Any]]) -> str:
    """Synthesize policy, market, and technology context for the report."""
    if not market_context:
        return ""
    statements: List[str] = []
    for item in market_context[:4]:
        finding = compact_text(item.get("finding"), 110)
        if not finding:
            continue
        topic = compact_text(item.get("topic"), 18)
        source = compact_text(item.get("source"), 18)
        if source and topic:
            prefix = f"{source}发布的“{topic}”相关信息表明"
        elif source:
            prefix = f"{source}相关政策与公开信息表明"
        elif topic:
            prefix = f"“{topic}”相关政策与行业信息表明"
        else:
            prefix = "相关政策与行业信息表明"
        statements.append(f"{prefix}，{finding}")
    if not statements:
        return ""
    return "从政策、市场与技术环境看，" + "；".join(statements) + "。"


def summarize_structure(canonical_chain: str, graph_summary: Mapping[str, Any], value_chain: List[Mapping[str, Any]]) -> str:
    l2 = graph_summary.get("l2_count") or len(value_chain) or "若干"
    l3 = graph_summary.get("l3_count") or "若干"
    l5 = graph_summary.get("l5_count") or "若干"
    l2_names = unique_nonempty([
        item.get("l2_segment") or item.get("segment")
        for item in value_chain[:5]
        if isinstance(item, Mapping)
    ], limit=5)
    l2_text = "、".join(l2_names) if l2_names else "主要价值环节"
    module_samples: List[str] = []
    for item in value_chain[:3]:
        if not isinstance(item, Mapping):
            continue
        module_samples.extend([part.strip() for part in str(item.get("l3_segments") or "").split("、") if part.strip()])
    module_text = "、".join(unique_nonempty(module_samples, limit=8))
    module_clause = f"；典型 L3 模块包括{module_text}" if module_text else ""
    return (
        f"从产业结构看，项目图谱将“{canonical_chain}”拆解为 {l2} 个 L2 价值环节、"
        f"{l3} 个 L3 产业模块与 {l5} 个 L5 标准节点，主链条由{l2_text}构成{module_clause}。"
    )


def summarize_focus_node(node: str, node_records: List[Mapping[str, Any]]) -> str:
    if not node:
        return "本报告覆盖全产业链主要层级，重点刻画价值环节之间的分工、承接关系与标准节点边界。"
    names = unique_nonempty([item.get("node_name") for item in node_records if isinstance(item, Mapping)], limit=4)
    if not names:
        return f"本次关注“{node}”相关方向，重点说明其在产业链中的层级位置、相邻模块关系与产品/技术边界。"
    first_path = str(node_records[0].get("path") or "") if node_records else ""
    path_parts = [part.strip() for part in first_path.split(">") if part.strip()]
    position = ""
    if len(path_parts) >= 3:
        position = f"，主要处于“{path_parts[1]} / {path_parts[2]}”层级"
    path_clause = f"，主路径为“{first_path}”" if first_path else ""
    return (
        f"本次关注的“{node}”映射为“{'、'.join(names)}”等 L5 标准节点{position}{path_clause}，"
        "用于解释该方向如何连接上游基础能力、中游系统集成与下游应用场景。"
    )


def build_professional_summary(
    canonical_chain: str,
    node: str,
    graph_summary: Mapping[str, Any],
    value_chain: List[Mapping[str, Any]],
    market_context: List[Mapping[str, Any]],
    node_records: List[Mapping[str, Any]],
) -> str:
    basis = "项目产业图谱"
    if market_context:
        basis += "、政策文件及行业公开资料"
    parts = [
        (
            f"本报告以“{canonical_chain}”作为 L1 产业链分析边界，基于{basis}建立"
            " L1 产业链、L2 价值环节、L3 产业模块、L4 可选细分方向与 L5 标准产品/技术/服务节点的统一口径。"
        ),
        summarize_market_context(market_context),
        summarize_structure(canonical_chain, graph_summary, value_chain),
        summarize_focus_node(node, node_records),
        "整体上，该图谱把基础能力、系统集成与应用服务之间的价值传导关系显性化，为产业研究与节点复用提供统一结构口径。",
    ]
    return "".join(part for part in parts if part)


def build_report_abstract(
    canonical_chain: str,
    graph_summary: Mapping[str, Any],
    value_chain: List[Mapping[str, Any]],
    market_context: List[Mapping[str, Any]],
) -> str:
    """Build a cover-length abstract without repeating source-by-source detail."""
    l2_count = graph_summary.get("l2_count") or len(value_chain) or "若干"
    l3_count = graph_summary.get("l3_count") or "若干"
    l5_count = graph_summary.get("l5_count") or "若干"
    segments = unique_nonempty([
        item.get("l2_segment") or item.get("segment")
        for item in value_chain
        if isinstance(item, Mapping)
    ], limit=5)
    segment_text = "、".join(segments) if segments else "主要价值环节"
    topics = unique_nonempty([
        item.get("topic")
        for item in market_context
        if isinstance(item, Mapping)
    ], limit=4)
    context_clause = (
        f"外部背景重点覆盖{'、'.join(topics)}，用于校准产业标准、技术演进与应用环境。"
        if topics
        else ""
    )
    return (
        f"本报告以“{canonical_chain}”为 L1 分析边界，基于项目图谱识别 {l2_count} 个 L2 价值环节、"
        f"{l3_count} 个 L3 产业模块和 {l5_count} 个 L5 标准节点。产业主链由{segment_text}构成，"
        "重点刻画基础能力、装备与系统、数字平台及应用服务之间的分工与价值传导。"
        f"{context_clause}"
    )


def build_payload(
    data: Dict[str, Any] | None = None,
    title: str | None = None,
    *,
    chain_arg: str | None = None,
    node_arg: str | None = None,
    path_arg: str | None = None,
    project_root: str | None = None,
    project_chain: str | None = None,
    project_node: str | None = None,
    market_context: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    data = data or {}
    chain = str(chain_arg or data.get("chain") or data.get("industry") or data.get("industry_chain") or "产业链")
    node = str(node_arg or data.get("node") or data.get("segment") or "").strip()
    path = parse_path(path_arg, chain, node) or [chain]
    node_query = project_node or node or chain
    project = build_project_context(
        chain,
        node_query,
        project_root=project_root,
        preferred_chain=project_chain,
    )
    project_available = bool(project.get("available"))
    canonical_chain = str(project.get("chain", {}).get("name") or chain) if project_available else chain
    mapped_nodes = (project.get("matched_nodes") or []) if node else []
    primary_project_path = mapped_nodes[0].get("path") if mapped_nodes else []
    graph_summary = project_graph_summary(project)
    project_value_chain = (project.get("value_chain") or []) if project_available else []
    graph_tree = project_graph_tree(project, canonical_chain) if project_available else {}
    value_chain = project_value_chain or build_value_chain(canonical_chain, node, path)
    graph_source = "project_graph"
    if not graph_tree_is_complete(graph_tree):
        graph_tree = project_graph_tree({"value_chain": value_chain}, canonical_chain)
        graph_source = "value_chain_reconstruction"
    if not graph_tree_is_complete(graph_tree):
        value_chain = build_value_chain(canonical_chain, node, path)
        graph_tree = project_graph_tree({"value_chain": value_chain}, canonical_chain)
        graph_source = "generated_fallback"
    if not graph_tree_is_complete(graph_tree):
        raise ValueError(f"产业链图谱构建失败：{canonical_chain} 未形成有效的 L2/L3/L5 节点")
    actual_graph_stats = graph_tree_stats(graph_tree)
    graph_summary = {
        **graph_summary,
        "l2_count": actual_graph_stats["l2"],
        "l3_count": actual_graph_stats["l3"],
        "l5_count": actual_graph_stats["l5"],
        "graph_source": graph_source,
        "graph_validation": "complete",
    }
    market_context = market_context or []
    node_records = project_node_rows({**project, "matched_nodes": mapped_nodes}) if mapped_nodes else []
    condition = data.get("condition") if isinstance(data.get("condition"), dict) else {}
    keywords = extract_keywords_from_condition(condition, [item for item in [node, chain] if item], limit=12) if condition else [item for item in [node, chain] if item]

    summary = build_professional_summary(canonical_chain, node, graph_summary, value_chain, market_context, node_records)
    abstract = build_report_abstract(canonical_chain, graph_summary, value_chain, market_context)
    industry_definition = industry_definition_rows(canonical_chain, node, graph_summary)
    segment_analysis = segment_analysis_rows(value_chain)
    key_node_system = key_node_system_rows(graph_tree)
    value_flow = value_flow_rows(value_chain)
    structural_characteristics = structural_characteristic_rows(canonical_chain, graph_summary, value_chain)

    node_mapping = {}
    if project_available:
        node_mapping = {
            "input_chain": chain,
            "canonical_chain": canonical_chain,
            "input_node": node or "全产业链",
            "mapped_project_nodes": "、".join(row["node_name"] for row in node_records[:5]) if node_records else "未指定或未命中 L5 节点",
            "primary_project_path": " > ".join(primary_project_path) if primary_project_path else canonical_chain,
            "mapping_note": "本报告按项目图谱层级、标准节点和节点记录进行结构化分析。",
        }

    return {
        "report_type": "industry_chain_analysis",
        "title": title or (f"{canonical_chain}-{node} 产业链层级分析报告" if node else f"{canonical_chain} 产业链分析报告"),
        "chain": canonical_chain,
        "input_chain": chain,
        "node": node,
        "path": path,
        "abstract": abstract,
        "summary": summary,
        "executive_summary": [
            f"分析对象：{canonical_chain}{(' / ' + node) if node else ''}。",
            f"研究资料：纳入 {len(market_context)} 项政策、市场或技术信息。" if market_context else "研究基础：产业链层级结构与标准产品技术节点。",
            "图谱层级：L1/L2/L3/L5；当前项目多数图谱未单独落 L4。",
            f"图谱节点规模：L2 {graph_summary.get('l2_count', '未知')}、L3 {graph_summary.get('l3_count', '未知')}、L5 {graph_summary.get('l5_count', '未知')}。" if graph_summary else "结构基础：采用产业层级分析框架。",
            f"核心分析词：{'、'.join(dict.fromkeys(keywords)) or canonical_chain}。",
        ],
        "industry_overview": {
            "industry_boundary": f"以“{canonical_chain}”作为 L1 产业链边界。" if project_available else f"以“{chain}”作为产业链边界。",
            "hierarchy_logic": "按 L1 产业链边界、L2 价值环节、L3 产业模块、L4 可选细分方向/能力组、L5 可匹配产品/技术/服务/能力节点展开；当前项目多数图谱为 L3 直连 L5。",
            "analysis_focus": "重点分析层级关系、关键节点、价值传导、技术/产品边界和下游应用路径。",
            "node_boundary": "产业层级只表达价值环节、产业模块和标准产品、技术、服务或能力节点。",
        },
        "industry_definition": industry_definition,
        "level_definitions": level_definition_rows(canonical_chain, node, graph_summary),
        "market_context": market_context,
        "project_graph_summary": graph_summary,
        "node_mapping": node_mapping,
        "project_graph_tree": graph_tree,
        "value_chain": value_chain,
        "project_value_chain": project_value_chain,
        "project_node_records": node_records,
        "industry_map": value_chain_to_industry_map(value_chain, canonical_chain),
        "hierarchy_analysis": hierarchy_analysis_rows(value_chain),
        "segment_analysis": segment_analysis,
        "key_node_system": key_node_system,
        "value_flow": value_flow,
        "structural_characteristics": structural_characteristics,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compose a project-aware industry-chain hierarchy and analysis report payload.")
    parser.add_argument("--input", help="Optional existing JSON for inferring chain/node/context. Enterprise linking data is not rendered in this report.")
    parser.add_argument("--chain", help="Industry chain name, e.g. 智能汽车. Required when --input has no chain.")
    parser.add_argument("--node", help="Optional focus node/segment, e.g. 自动驾驶.")
    parser.add_argument("--path", help="Optional full node path separated by > or /.")
    parser.add_argument("--output", help="Output composed report JSON. Prints to stdout when omitted.")
    parser.add_argument("--title", help="Report title")
    parser.add_argument("--project-root", help="industry-chain-map project root; defaults to INDUSTRY_CHAIN_PROJECT_ROOT or known sibling path.")
    parser.add_argument("--project-chain", help="Preferred project canonical chain name, e.g. 智能网联汽车")
    parser.add_argument("--project-node", help="Preferred project node query, e.g. 自动驾驶解决方案")
    parser.add_argument("--market-context", help="Optional JSON file with web-collected industry background/context items.")
    parser.add_argument("--market-note", action="append", default=[], help="Optional context note. Format: topic|finding|source|url|date. Repeatable.")
    args = parser.parse_args()

    data = load_json(args.input) if args.input else {}
    if not (args.chain or data.get("chain") or data.get("industry") or data.get("industry_chain")):
        raise SystemExit("请提供 --chain，或通过 --input 传入包含 chain/industry 的 JSON")

    try:
        payload = build_payload(
            data,
            args.title,
            chain_arg=args.chain,
            node_arg=args.node,
            path_arg=args.path,
            project_root=args.project_root,
            project_chain=args.project_chain,
            project_node=args.project_node,
            market_context=load_market_context(args.market_context, args.market_note),
        )
    except ValueError as exc:
        raise SystemExit(f"报告生成失败：{exc}") from exc
    if args.output:
        output = Path(args.output).expanduser()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json_dumps(payload, pretty=True), encoding="utf-8")
        print_json({"ok": True, "output": str(output)})
    else:
        print_json(payload)


if __name__ == "__main__":
    main()
