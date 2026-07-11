#!/usr/bin/env python3
"""Project-local industry graph and node-record context helpers.

This adapter lets the standalone skill reuse the current visualization project's
industry-chain ontology, high-screen condition records, and enterprise-link
records instead of inventing a generic report structure.
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def normalize_text(value: Any) -> str:
    return (
        str(value or "")
        .strip()
        .replace("产业链", "")
        .replace("产业", "")
        .replace(" ", "")
        .replace("（", "(")
        .replace("）", ")")
        .lower()
    )


def relevant_tokens(value: str) -> List[str]:
    candidates = [
        "智能", "网联", "汽车", "自动驾驶", "智能驾驶", "ADAS", "座舱", "车联网", "低空", "无人机",
        "机器人", "传感器", "芯片", "软件", "云服务", "新能源", "半导体", "数字", "创意",
        "制造", "工业", "母机", "增材", "激光", "精密", "仪器", "自动化", "工厂",
    ]
    text = value.lower()
    return [token.lower() for token in candidates if token.lower() in text]


def name_score(query: str, candidate: str) -> int:
    q = normalize_text(query)
    c = normalize_text(candidate)
    if not q or not c:
        return 0
    if q == c:
        return 100
    if q in c or c in q:
        return 85
    q_tokens = set(relevant_tokens(query))
    c_tokens = set(relevant_tokens(candidate))
    if q_tokens:
        overlap = q_tokens & c_tokens
        if overlap:
            return 45 + int(40 * len(overlap) / max(len(q_tokens), 1))
    # Character-level fallback for short Chinese names.
    q_chars = {ch for ch in q if "\u4e00" <= ch <= "\u9fff"}
    c_chars = {ch for ch in c if "\u4e00" <= ch <= "\u9fff"}
    if q_chars:
        ratio = len(q_chars & c_chars) / len(q_chars)
        if ratio >= 0.7:
            return int(35 + ratio * 35)
    return 0


def resolve_project_root(project_root: Optional[str] = None) -> Optional[Path]:
    repository_root = Path(__file__).resolve().parents[2]
    current_dir = Path.cwd()
    candidates = [
        project_root,
        os.environ.get("INDUSTRY_CHAIN_PROJECT_ROOT"),
        os.environ.get("INDUSTRY_CHAIN_MAP_ROOT"),
        current_dir / "industry-chain-map",
        current_dir.parent / "industry-chain-map",
        repository_root.parent / "industry-chain-map",
        repository_root.parent / "industrychainvisualization" / "industry-chain-map",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate).expanduser().resolve()
        if (path / "src" / "data").exists() or (path / ".data" / "industry-chain-archive.sqlite").exists():
            return path
    return None


def safe_json_loads(value: Any, default: Any = None) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except Exception:
        return default


def flatten_graph(data: Dict[str, Any]) -> Dict[str, Any]:
    chain_name = str(data.get("name") or data.get("产业链") or "")
    raw_l2 = data.get("children")
    if raw_l2 is None and isinstance(data.get("环节"), list):
        raw_l2 = [
            {
                "name": item.get("环节名称"),
                "children": [
                    {
                        "name": sub.get("子环节名称"),
                        "children": [
                            {
                                "name": leaf.get("子-子环节名称"),
                                "representative_companies": leaf.get("代表公司") or [],
                                "children": [],
                            }
                            for leaf in (sub.get("子-子环节") or [])
                        ],
                    }
                    for sub in (item.get("子环节") or [])
                ],
            }
            for item in (data.get("环节") or [])
        ]
    raw_l2 = raw_l2 or []
    value_chain: List[Dict[str, Any]] = []
    l5_nodes: List[Dict[str, Any]] = []
    representative_links: List[Dict[str, Any]] = []
    for l2 in raw_l2:
        l2_name = str(l2.get("name") or "")
        l3_items = l2.get("children") or []
        l3_names: List[str] = []
        l5_samples: List[str] = []
        l5_count = 0
        for l3 in l3_items:
            l3_name = str(l3.get("name") or "")
            if l3_name:
                l3_names.append(l3_name)
            for l5 in (l3.get("children") or []):
                l5_name = str(l5.get("name") or "")
                if not l5_name:
                    continue
                path = [chain_name, l2_name, l3_name, l5_name]
                reps = list(l5.get("representative_companies") or [])
                # Some archived normalized graphs keep seed enterprises as children under L5.
                for child in (l5.get("children") or []):
                    child_name = child.get("name") if isinstance(child, dict) else child
                    if child_name:
                        reps.append(str(child_name))
                l5_nodes.append({"name": l5_name, "path": path, "representative_companies": sorted(set(reps))[:20]})
                for company in sorted(set(reps))[:12]:
                    representative_links.append({"node": l5_name, "path": path, "enterprise": company, "source": "project_graph_seed"})
                if len(l5_samples) < 10:
                    l5_samples.append(l5_name)
                l5_count += 1
        value_chain.append({
            "l2_segment": l2_name,
            "l3_count": len(l3_names),
            "l5_count": l5_count,
            "l3_segments": "、".join(l3_names[:12]),
            "l5_samples": "、".join(l5_samples[:12]),
        })
    return {
        "chain_name": chain_name,
        "value_chain": value_chain,
        "l5_nodes": l5_nodes,
        "representative_links": representative_links,
        "stats": {
            "l2": len(value_chain),
            "l3": sum(int(item["l3_count"]) for item in value_chain),
            "l5": len(l5_nodes),
            "seed_enterprises": len(representative_links),
        },
    }


def read_static_chains(project_root: Path) -> List[Dict[str, Any]]:
    data_dir = project_root / "src" / "data" / "industries"
    chains: List[Dict[str, Any]] = []
    if not data_dir.exists():
        return chains
    for path in sorted(data_dir.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            flat = flatten_graph(raw)
            chains.append({"source": "static_json", "source_ref": str(path), "raw": raw, **flat})
        except Exception:
            continue
    return chains


def connect_archive(project_root: Path) -> Optional[sqlite3.Connection]:
    db_path = project_root / ".data" / "industry-chain-archive.sqlite"
    if not db_path.exists():
        return None
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def read_archive_chains(project_root: Path) -> List[Dict[str, Any]]:
    conn = connect_archive(project_root)
    if not conn:
        return []
    chains: List[Dict[str, Any]] = []
    try:
        for row in conn.execute("SELECT id,name,category,source_type,node_count,enterprise_count_cache,current_data_json,updated_at FROM chain_definitions WHERE status='active'"):
            raw = safe_json_loads(row["current_data_json"], {}) or {}
            flat = flatten_graph(raw)
            chains.append({
                "source": "sqlite_archive",
                "source_ref": str(project_root / ".data" / "industry-chain-archive.sqlite"),
                "chain_id": row["id"],
                "category": row["category"],
                "source_type": row["source_type"],
                "node_count": row["node_count"],
                "enterprise_count_cache": row["enterprise_count_cache"],
                "updated_at": row["updated_at"],
                "raw": raw,
                **({**flat, "chain_name": row["name"] or flat.get("chain_name")}),
            })
    finally:
        conn.close()
    return chains


def choose_chain(chains: Iterable[Dict[str, Any]], query: str, preferred: Optional[str] = None) -> Optional[Dict[str, Any]]:
    target = preferred or query
    scored: List[Tuple[int, Dict[str, Any]]] = []
    for chain in chains:
        score = name_score(target, str(chain.get("chain_name") or ""))
        if score < 70:
            continue
        if preferred and str(chain.get("chain_name")) == preferred:
            score += 50
        # Prefer archived chain with enterprise/node records over static JSON when scores tie.
        if chain.get("source") == "sqlite_archive":
            score += 5
        scored.append((score, chain))
    if not scored:
        return None
    scored.sort(key=lambda item: (item[0], int(item[1].get("enterprise_count_cache") or 0), int(item[1].get("node_count") or 0)), reverse=True)
    return scored[0][1]


def archive_node_records(project_root: Path, chain_id: str, node_query: str, limit: int = 8) -> List[Dict[str, Any]]:
    conn = connect_archive(project_root)
    if not conn:
        return []
    rows: List[Dict[str, Any]] = []
    try:
        for row in conn.execute(
            """
            SELECT e.id AS edge_id, e.path_json, e.display_name, e.level,
                   n.id AS node_id, n.name AS node_name, n.node_type,
                   h.id AS condition_group_id, h.source AS condition_source, h.status AS condition_status,
                   h.keywords_json, h.condition_json
            FROM chain_node_edges e
            JOIN canonical_nodes n ON e.child_node_id = n.id
            LEFT JOIN high_screen_condition_groups h ON h.chain_id = e.chain_id AND h.node_id = n.id AND h.status='active'
            WHERE e.chain_id = ? AND e.level = 5
            """,
            (chain_id,),
        ):
            path = safe_json_loads(row["path_json"], []) or []
            score = max(name_score(node_query, row["node_name"]), name_score(node_query, " ".join(path)))
            if score <= 0:
                continue
            links = []
            for link in conn.execute(
                """
                SELECT enterprise_name, enterprise_external_id, link_status, evidence_json
                FROM enterprise_node_links
                WHERE chain_id = ? AND node_id = ?
                ORDER BY updated_at DESC
                LIMIT 20
                """,
                (chain_id, row["node_id"]),
            ):
                evidence = safe_json_loads(link["evidence_json"], {}) or {}
                links.append({
                    "enterprise": link["enterprise_name"],
                    "enterprise_external_id": link["enterprise_external_id"],
                    "status": link["link_status"],
                    "evidence_level": evidence.get("evidence_level") if isinstance(evidence, dict) else None,
                    "source": evidence.get("source") if isinstance(evidence, dict) else None,
                })
            rows.append({
                "score": score,
                "edge_id": row["edge_id"],
                "node_id": row["node_id"],
                "node_name": row["node_name"],
                "node_type": row["node_type"],
                "path": path,
                "condition_group_id": row["condition_group_id"],
                "condition_source": row["condition_source"],
                "condition_status": row["condition_status"],
                "condition_keywords": safe_json_loads(row["keywords_json"], []) or [],
                "condition": safe_json_loads(row["condition_json"], {}) or {},
                "link_count": len(links),
                "link_samples": links[:8],
            })
    finally:
        conn.close()
    rows.sort(key=lambda item: (item["score"], item["link_count"]), reverse=True)
    return rows[:limit]


def static_node_records(chain: Dict[str, Any], node_query: str, limit: int = 8) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item in chain.get("l5_nodes") or []:
        score = max(name_score(node_query, item.get("name", "")), name_score(node_query, " ".join(item.get("path") or [])))
        if score <= 0:
            continue
        reps = [{"enterprise": company, "status": "seed", "source": "static_representative_company", "evidence_level": "weak_seed_candidate"} for company in item.get("representative_companies") or []]
        rows.append({
            "score": score,
            "node_name": item.get("name"),
            "node_type": "product_tech",
            "path": item.get("path") or [],
            "condition_keywords": [],
            "condition_source": None,
            "link_count": len(reps),
            "link_samples": reps[:8],
        })
    rows.sort(key=lambda item: (item["score"], item["link_count"]), reverse=True)
    return rows[:limit]


SMART_MANUFACTURING_SOURCES = [
    ("半导体与集成电路", "上游：工业基础与核心部件", "工业芯片与电子基础", 8),
    ("智能传感器", "上游：工业基础与核心部件", "感知与检测", 8),
    ("精密仪器设备", "上游：工业基础与核心部件", "测量与质量控制", 8),
    ("工业母机", "中游：智能装备与工艺系统", "数控机床与工业母机", 10),
    ("智能机器人", "中游：智能装备与工艺系统", "机器人与自动化单元", 10),
    ("激光与增材制造", "中游：智能装备与工艺系统", "激光加工与增材制造", 8),
    ("软件与信息服务", "中游：工业软件与数字平台", "工业软件与数字平台", 10),
]


SMART_MANUFACTURING_NODE_PREFERENCES = {
    "半导体与集成电路": [
        "CPU/GPU", "FPGA/CPLD", "AI芯片", "模拟芯片", "功率半导体", "传感器芯片", "电子设计自动化软件", "工业控制",
    ],
    "智能传感器": [
        "物理量传感器（温度、压力、湿度、流量、位移、加速度等）", "图像传感器", "光电传感器",
        "惯性传感器（陀螺仪、加速度计、IMU）", "传感器数据融合", "嵌入式系统开发", "工业自动化", "过程控制", "预测性维护",
    ],
    "精密仪器设备": [
        "三坐标测量机", "光学测量仪", "长度/角度测量仪", "机器视觉系统", "检测设备", "位置传感器",
        "压力/流量/温度传感器", "伺服电机/驱动器",
    ],
    "工业母机": [
        "高端数控系统", "伺服电机", "伺服驱动器", "滚珠丝杠", "直线导轨", "电主轴", "CAD/CAM/CAE软件",
        "仿真软件", "数控车床", "加工中心（立式、卧式、龙门）",
    ],
    "智能机器人": [
        "多关节机器人", "SCARA机器人", "协作机器人", "Delta机器人", "机器人操作系统（ROS）及中间件",
        "运动控制卡/器", "伺服电机", "减速器", "工业机器人系统集成", "视觉传感器（摄像头）",
    ],
    "激光与增材制造": [
        "激光加工控制系统", "运动控制卡", "激光切割设备", "激光焊接设备", "激光清洗设备", "激光微纳加工设备",
        "金属3D打印设备", "自动化集成",
    ],
    "软件与信息服务": [
        "数据采集", "行业应用软件", "嵌入式软件", "系统集成", "机器学习平台", "数据分析平台",
        "企业资源管理 (ERP)", "供应链管理 (SCM)", "工业物联网平台", "工业数据分析",
    ],
}


SMART_MANUFACTURING_APPLICATIONS = [
    "智能工厂总体解决方案",
    "数字化车间改造",
    "离散制造智能化",
    "流程制造智能化",
    "柔性生产与个性化定制",
    "质量追溯与预测性维护",
    "供应链协同与智能物流",
    "绿色制造与能碳管理",
]


def build_smart_manufacturing_composite(chains: Iterable[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Compose intelligent manufacturing from existing project graph assets."""
    by_name = {normalize_text(chain.get("chain_name")): chain for chain in chains}
    selected_nodes: List[Dict[str, Any]] = []
    source_names: List[str] = []
    enterprise_count = 0
    updated_values: List[str] = []
    for source_name, l2_name, l3_name, limit in SMART_MANUFACTURING_SOURCES:
        source = by_name.get(normalize_text(source_name))
        if not source:
            continue
        source_names.append(source_name)
        enterprise_count += int(source.get("enterprise_count_cache") or 0)
        if source.get("updated_at"):
            updated_values.append(str(source["updated_at"]))
        available_nodes = {str(node.get("name") or ""): node for node in source.get("l5_nodes") or []}
        preferred_names = SMART_MANUFACTURING_NODE_PREFERENCES.get(source_name) or []
        preferred_nodes = [available_nodes[name] for name in preferred_names if name in available_nodes]
        source_nodes = preferred_nodes[:limit] or (source.get("l5_nodes") or [])[:limit]
        for node in source_nodes:
            node_name = str(node.get("name") or "").strip()
            if not node_name:
                continue
            selected_nodes.append({
                "name": node_name,
                "path": ["智能制造", l2_name, l3_name, node_name],
                "source_chain": source_name,
                "representative_companies": [],
            })
    if not selected_nodes:
        return None
    for node_name in SMART_MANUFACTURING_APPLICATIONS:
        selected_nodes.append({
            "name": node_name,
            "path": ["智能制造", "下游：智能工厂集成与行业应用", "场景集成与运营服务", node_name],
            "source_chain": "skill_composite_extension",
            "representative_companies": [],
        })

    grouped: Dict[str, Dict[str, List[str]]] = {}
    for node in selected_nodes:
        _, l2_name, l3_name, node_name = node["path"]
        grouped.setdefault(l2_name, {}).setdefault(l3_name, []).append(node_name)
    value_chain: List[Dict[str, Any]] = []
    for l2_name, l3_groups in grouped.items():
        samples = [name for names in l3_groups.values() for name in names]
        value_chain.append({
            "l2_segment": l2_name,
            "l3_count": len(l3_groups),
            "l5_count": len(samples),
            "l3_segments": "、".join(l3_groups.keys()),
            "l5_samples": "、".join(samples[:12]),
            "analysis": f"该环节覆盖 {len(l3_groups)} 个 L3 模块和 {len(samples)} 个代表性 L5 节点。",
        })
    return {
        "source": "composite_project_chains",
        "source_ref": "industry-chain-archive.sqlite",
        "chain_id": "composite_smart_manufacturing",
        "chain_name": "智能制造",
        "category": "strategic_composite",
        "source_type": "project_composite",
        "node_count": len(selected_nodes),
        "enterprise_count_cache": enterprise_count,
        "updated_at": max(updated_values) if updated_values else "",
        "value_chain": value_chain,
        "l5_nodes": selected_nodes,
        "representative_links": [],
        "source_chains": source_names,
        "stats": {
            "l2": len(value_chain),
            "l3": sum(len(groups) for groups in grouped.values()),
            "l5": len(selected_nodes),
            "seed_enterprises": 0,
        },
    }


def build_project_context(
    chain_query: str,
    node_query: str,
    *,
    project_root: Optional[str] = None,
    preferred_chain: Optional[str] = None,
    limit: int = 8,
) -> Dict[str, Any]:
    root = resolve_project_root(project_root)
    if not root:
        return {"available": False, "reason": "未找到 industry-chain-map 项目根目录；可传 --project-root 或设置 INDUSTRY_CHAIN_PROJECT_ROOT"}
    chains = read_archive_chains(root) + read_static_chains(root)
    chain = None
    if normalize_text(chain_query) == normalize_text("智能制造") and not preferred_chain:
        chain = build_smart_manufacturing_composite(chains)
    if not chain:
        chain = choose_chain(chains, chain_query, preferred_chain)
    if not chain:
        return {"available": False, "project_root": str(root), "reason": f"未找到匹配产业链：{chain_query}"}
    if chain.get("source") == "sqlite_archive" and chain.get("chain_id"):
        node_records = archive_node_records(root, str(chain["chain_id"]), node_query, limit=limit)
    else:
        node_records = static_node_records(chain, node_query, limit=limit)
    if not node_records:
        node_records = static_node_records(chain, node_query, limit=limit)
    return {
        "available": True,
        "project_root": str(root),
        "source": chain.get("source"),
        "source_ref": chain.get("source_ref"),
        "chain": {
            "id": chain.get("chain_id"),
            "name": chain.get("chain_name"),
            "category": chain.get("category"),
            "source_type": chain.get("source_type"),
            "node_count": chain.get("node_count") or chain.get("stats", {}).get("l5"),
            "enterprise_count_cache": chain.get("enterprise_count_cache"),
            "updated_at": chain.get("updated_at"),
        },
        "stats": chain.get("stats") or {},
        "value_chain": chain.get("value_chain") or [],
        "l5_nodes": chain.get("l5_nodes") or [],
        "matched_nodes": node_records,
        "representative_links": (chain.get("representative_links") or [])[:50],
        "source_chains": chain.get("source_chains") or [],
    }
