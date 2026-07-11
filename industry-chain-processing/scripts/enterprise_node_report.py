#!/usr/bin/env python3
"""Generate a detailed enterprise-to-industry-node analysis report payload."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from build_condition import parse_path
from common import get_handaas_section, json_dumps, load_config, print_json
from evidence_call import call_handaas, call_remote_evidence
from link_enterprises import DEFAULT_EVIDENCE_PRODUCTS, classify_candidate, keyword_hits
from mcp_client import has_remote_mcp_config
from project_context import build_project_context
from render_report import write_report

STRONG_PRODUCTS = {"知识产权统计", "专利搜索", "企业招投标信息", "招投标公告", "中标统计", "招标统计", "采购统计"}
MEDIUM_PRODUCTS = {"工商照面", "企业基础信息", "企业简介", "企业业务", "经营业务", "企业标签"}
BAD_MARKERS = ["产品不存在", "validation error", "Error executing tool", "Traceback", "biddingType格式错误"]


def snippet(value: Any, limit: int = 180) -> str:
    if value is None:
        return ""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = " ".join(str(text).split())
    return text[:limit] + ("…" if len(text) > limit else "")


def nested_get(data: Any, *keys: str) -> Any:
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def payload_status(payload: Dict[str, Any]) -> str:
    text = json.dumps(payload, ensure_ascii=False)
    if any(marker in text for marker in BAD_MARKERS):
        return "error"
    if "请求异常" in text:
        return "upstream_warning"
    if "查询数据为空" in text:
        return "empty"
    if isinstance(payload, dict) and payload.get("error"):
        return "error"
    return "available"


def patent_total(data: Any) -> Optional[int]:
    stat = data.get("patentTypeStat") if isinstance(data, dict) else None
    if isinstance(stat, dict):
        return sum(int(v or 0) for v in stat.values() if isinstance(v, (int, float)))
    rows = data.get("resultList") if isinstance(data, dict) else None
    if isinstance(rows, list):
        return len(rows)
    return None


def summarize_product(product: str, payload: Dict[str, Any], node: str, keywords: Sequence[str]) -> Dict[str, Any]:
    data = payload.get("data") if isinstance(payload, dict) else payload
    hits = keyword_hits(data, [node, *keywords])
    status = payload_status(payload)
    strength = "strong" if product in STRONG_PRODUCTS and hits else "medium" if product in MEDIUM_PRODUCTS and hits else "weak"
    finding = ""
    datapoints = ""

    if product in {"工商照面", "企业基础信息"} and isinstance(data, dict):
        business = data.get("business")
        industry = data.get("industry") or {}
        industry_name = " / ".join(str(industry.get(k) or "") for k in ("firstIndustry", "secondIndustry", "thirdIndustry", "fourthIndustry") if industry.get(k)) if isinstance(industry, dict) else ""
        finding = snippet(business or data.get("name") or data)
        datapoints = f"状态={data.get('operStatus') or ''}; 行业={industry_name}; 注册资本={json.dumps(data.get('regCapital'), ensure_ascii=False) if data.get('regCapital') else ''}"
    elif product == "企业简介" and isinstance(data, dict):
        finding = snippet(data.get("desc") or data)
    elif product in {"企业业务", "经营业务"} and isinstance(data, dict):
        rows = data.get("resultList") or []
        if rows and isinstance(rows, list):
            first = rows[0]
            finding = snippet(first.get("desc") or first.get("productName") or first)
            datapoints = snippet({"productName": first.get("productName"), "productDomain": first.get("productDomain"), "tags": first.get("tags")})
        else:
            finding = snippet(data)
    elif product == "企业标签" and isinstance(data, dict):
        tags = data.get("businessTags") or []
        finding = snippet("、".join(str(x) for x in tags[:20]) if isinstance(tags, list) else tags)
        datapoints = f"高新={data.get('isHighTechEnterprise')}; 专精特新={data.get('isSpecializedAndNew')}; 规模={data.get('enterpriseScaleAlgValue') or ''}"
    elif product in {"知识产权统计", "专利统计"} and isinstance(data, dict):
        total = patent_total(data)
        finding = f"专利统计合计约 {total} 件" if total is not None else snippet(data)
        datapoints = snippet(data.get("patentTypeStat") or data)
    elif product in {"企业招投标信息", "招投标信息", "招投标公告"} and isinstance(data, dict):
        rows = data.get("resultList") or []
        titles = [str(item.get("title") or item.get("biddingAnncTitle") or "") for item in rows[:5] if isinstance(item, dict)] if isinstance(rows, list) else []
        finding = snippet("；".join(titles) or data)
        datapoints = f"total={data.get('total') if isinstance(data, dict) else ''}; rows={len(rows) if isinstance(rows, list) else 0}"
    else:
        finding = snippet(data)

    return {
        "product": product,
        "status": status,
        "signal_strength": strength,
        "matched_keywords": "、".join(dict.fromkeys(hits)),
        "key_findings": finding or status,
        "data_points": datapoints,
    }


def collect_remote(product: str, keyword: str, key_type: str, config: Optional[str], timeout: int) -> Dict[str, Any]:
    return call_remote_evidence(product, keyword, key_type, {"pageIndex": 1, "pageSize": 5}, config_path=config, timeout=timeout)


def collect_local(product: str, keyword: str, key_type: str, config_path: Optional[str], timeout: int) -> Dict[str, Any]:
    config, _ = load_config(config_path)
    handaas = get_handaas_section(config)
    return call_handaas(handaas, product, keyword, key_type, {"pageIndex": 1, "pageSize": 5}, timeout=timeout)


def build_report(args: argparse.Namespace) -> Dict[str, Any]:
    path = parse_path(args.path, args.chain, args.node)
    project = build_project_context(
        args.chain,
        args.project_node or args.node,
        project_root=args.project_root,
        preferred_chain=args.project_chain,
    )
    project_available = bool(project.get("available"))
    canonical_chain = str(project.get("chain", {}).get("name") or args.chain) if project_available else args.chain
    mapped_nodes = project.get("matched_nodes") or []
    primary_project_path = mapped_nodes[0].get("path") if mapped_nodes else path
    keywords = [args.node, *args.keyword]
    products = args.evidence_product or DEFAULT_EVIDENCE_PRODUCTS
    remote_enabled = not args.local and has_remote_mcp_config(args.config)
    evidence: Dict[str, Any] = {}
    for product in products:
        try:
            evidence[product] = collect_remote(product, args.enterprise, args.key_type, args.config, args.timeout) if remote_enabled else collect_local(product, args.enterprise, args.key_type, args.config, args.timeout)
        except Exception as exc:
            evidence[product] = {"product": product, "error": str(exc)}

    base_data = nested_get(evidence.get("工商照面") or {}, "data") or {}
    enterprise_name = str(base_data.get("name") or args.enterprise)
    enterprise_id = str(base_data.get("nameId") or base_data.get("_id") or args.enterprise)
    candidate = {"name": enterprise_name, "id": enterprise_id}
    decision = classify_candidate(candidate, evidence, args.node, keywords)
    strength = decision.get("evidence_strength")
    score = {"strong": 88, "medium": 68, "weak": 45}.get(strength, 50)
    if decision.get("decision") == "confirmed":
        score = max(score, 82)
    if isinstance(base_data, dict) and "注销" in str(base_data.get("operStatus") or ""):
        score = max(20, score - 25)

    evidence_summary = [summarize_product(product, payload, args.node, keywords) for product, payload in evidence.items()]
    warnings = [row for row in evidence_summary if row["status"] in {"upstream_warning", "empty", "error"}]
    text = json.dumps(evidence, ensure_ascii=False)
    bad_markers = [marker for marker in BAD_MARKERS if marker in text]
    business = base_data.get("business") if isinstance(base_data, dict) else ""
    profile = nested_get(evidence.get("企业简介") or {}, "data", "desc")

    node_fit = {
        "target_node": args.node,
        "project_node": mapped_nodes[0].get("node_name") if mapped_nodes else "",
        "project_node_path": " > ".join(primary_project_path or []),
        "recommended_link": "建议挂链" if decision.get("decision") == "confirmed" else "建议人工复核后挂链",
        "decision": decision.get("decision"),
        "evidence_strength": strength,
        "fit_score": score,
        "reason": decision.get("reason"),
        "next_action": decision.get("next_action"),
    }

    return {
        "report_type": "enterprise_node_analysis",
        "title": args.title or f"{enterprise_name} - {canonical_chain}/{args.node} 产业链节点分析报告",
        "chain": canonical_chain,
        "input_chain": args.chain,
        "node": args.node,
        "path": path,
        "project_graph_summary": {
            "canonical_chain_name": project.get("chain", {}).get("name") if project_available else "",
            "chain_id": project.get("chain", {}).get("id") if project_available else "",
            "source": project.get("source") if project_available else "",
            "source_type": project.get("chain", {}).get("source_type") if project_available else "",
            "node_count": project.get("chain", {}).get("node_count") if project_available else "",
            "enterprise_count_cache": project.get("chain", {}).get("enterprise_count_cache") if project_available else "",
            "l2_count": project.get("stats", {}).get("l2") if project_available else "",
            "l3_count": project.get("stats", {}).get("l3") if project_available else "",
            "l5_count": project.get("stats", {}).get("l5") if project_available else "",
        } if project_available else {},
        "node_mapping": {
            "input_chain": args.chain,
            "canonical_chain": canonical_chain,
            "input_node": args.node,
            "mapped_project_nodes": "、".join(str(item.get("node_name")) for item in mapped_nodes[:5]),
            "primary_project_path": " > ".join(primary_project_path or []),
            "mapping_note": "企业节点分析以当前项目 L5 标准节点为挂链目标；若输入节点不是标准 L5，则先映射到最接近项目节点。",
        } if project_available else {},
        "project_node_records": [
            {
                "node_name": item.get("node_name"),
                "path": " > ".join(item.get("path") or []),
                "condition_source": item.get("condition_source") or "暂无",
                "condition_keywords": "、".join(item.get("condition_keywords") or []),
                "link_count": item.get("link_count", 0),
                "node_id": item.get("node_id") or "",
            }
            for item in mapped_nodes[:8]
        ],
        "project_seed_links": [
            {
                "node_name": node.get("node_name"),
                "enterprise": link.get("enterprise"),
                "status": link.get("status"),
                "source": link.get("source"),
                "evidence_level": link.get("evidence_level"),
            }
            for node in mapped_nodes[:5]
            for link in (node.get("link_samples") or [])[:8]
        ],
        "enterprise": enterprise_name,
        "enterprise_profile": {
            "name": enterprise_name,
            "id_or_keyword": args.enterprise,
            "oper_status": base_data.get("operStatus") if isinstance(base_data, dict) else "",
            "address": base_data.get("address") if isinstance(base_data, dict) else "",
            "business_scope": snippet(business, 500),
            "profile": snippet(profile, 500),
        },
        "summary": (
            f"{enterprise_name} 与项目节点“{mapped_nodes[0].get('node_name') if mapped_nodes else args.node}”的挂链判断为 {decision.get('decision')}，"
            f"证据强度为 {strength}，综合匹配分 {score}/100。{decision.get('reason')}。"
        ),
        "professional_opinion": [
            f"节点定位：{' > '.join(primary_project_path or path)}。",
            f"核心依据：{decision.get('reason')}。",
            "建议将强证据企业优先进入挂链库；对中弱证据企业补充官网、产品手册、项目合同或人工复核。",
        ],
        "fit_assessment": node_fit,
        "evidence_summary": evidence_summary,
        "risk_flags": [
            *(f"{row['product']} 返回 {row['status']}，需要交付前复核。" for row in warnings),
            *(f"接口异常标记：{marker}" for marker in bad_markers),
        ] or ["未发现阻断性接口/证据风险。"],
        "recommendations": [
            node_fit["recommended_link"],
            "保留工商、简介、标签、专利和招投标作为挂链审计证据。",
            "若用于招商或投资筛选，建议补充官网产品页、客户案例和融资/股权关系。",
        ],
        "decision": decision,
        "evidence": evidence,
        "data_quality": {
            "mode": "mcp" if remote_enabled else "local",
            "bad_markers": bad_markers,
            "warning_count": len(warnings),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a detailed enterprise-node industry-chain analysis report payload.")
    parser.add_argument("--config", help="Config JSON path.")
    parser.add_argument("--chain", required=True)
    parser.add_argument("--node", required=True)
    parser.add_argument("--path", help="Full node path separated by > or /.")
    parser.add_argument("--enterprise", required=True, help="Enterprise name/nameId/social credit code/registration number")
    parser.add_argument("--key-type", default="name", help="name, nameId, socialCreditCode, regNumber")
    parser.add_argument("--keyword", action="append", default=[])
    parser.add_argument("--evidence-product", action="append", default=[])
    parser.add_argument("--output", help="Output JSON path. Prints to stdout when omitted.")
    parser.add_argument("--report-output", help="Write a business-ready HTML or Markdown report")
    parser.add_argument("--report-format", choices=["html", "markdown", "md"], help="Report format; defaults from report file extension")
    parser.add_argument("--title", help="Report title")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--local", action="store_true", help="Force legacy local credential mode even if Remote MCP is configured.")
    parser.add_argument("--project-root", help="industry-chain-map project root; defaults to INDUSTRY_CHAIN_PROJECT_ROOT or known sibling path.")
    parser.add_argument("--project-chain", help="Preferred project canonical chain name, e.g. 智能网联汽车")
    parser.add_argument("--project-node", help="Preferred project node query, e.g. 自动驾驶解决方案")
    args = parser.parse_args()

    payload = build_report(args)
    report_result = None
    if args.report_output:
        payload["report_artifacts"] = {"enterprise_node_report": str(Path(args.report_output).expanduser())}
        report_result = write_report(payload, args.report_output, fmt=args.report_format, title=args.title)
    if args.output:
        output = Path(args.output).expanduser()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json_dumps(payload, pretty=True), encoding="utf-8")
        print_json({"ok": True, "output": str(output), "report": report_result, "decision": payload.get("fit_assessment", {}).get("decision")})
    elif report_result:
        print_json({"ok": True, "report": report_result, "decision": payload.get("fit_assessment", {}).get("decision")})
    else:
        print_json(payload)


if __name__ == "__main__":
    main()
