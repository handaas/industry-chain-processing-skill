#!/usr/bin/env python3
"""End-to-end enterprise matching helper for one refined industry segment."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Sequence

from build_condition import build_search_plan, dedupe, normalize_legacy_negative_groups, parse_path
from common import ConfigError, get_handaas_section, get_high_screen_section, json_dumps, load_config, print_json, redact
from enterprise_chain_positioning import evidence_error, evidence_signals
from evidence_call import call_handaas, call_remote_evidence
from enterprise_search_preview import (
    REMOTE_SEARCH_TOOL,
    build_enterprise_search_request,
    call_enterprise_search_preview,
    call_remote_enterprise_search_preview,
    extract_keywords_from_condition,
)
from mcp_client import has_remote_mcp_config
from project_context import build_project_context, name_score
from render_report import write_report

CORE_BUSINESS_EVIDENCE_PRODUCTS = ["工商照面", "企业简介", "企业标签", "专利搜索", "企业招投标信息"]
OPTIONAL_BUSINESS_EVIDENCE_PRODUCTS = ["企业业务"]
DEFAULT_EVIDENCE_PRODUCTS = [*CORE_BUSINESS_EVIDENCE_PRODUCTS, *OPTIONAL_BUSINESS_EVIDENCE_PRODUCTS]
STRONG_REVIEW_SOURCES = {"企业业务", "专利搜索", "企业招投标信息", "招投标公告"}
MEDIUM_REVIEW_SOURCES = {"企业标签", "企业简介", "工商照面"}
ROUTE_WEIGHTS = {
    "operator_confirmed": 6,
    "industry_business_consensus": 6,
    "industry_business_keyword": 4,
    "project_seed": 8,
    "industry_registration_scope": 5,
    "business_consensus_precision": 5,
    "business_keyword_precision": 3,
    "registration_scope_precision": 4,
    "web_presence_recall": 1,
    "external_condition": 3,
}
SEED_SUFFIX_RE = re.compile(
    r"(?:股份有限公司|有限责任公司|有限公司|集团有限公司|集团|控股|公司)$"
)


def keyword_hits(payload: Any, keywords: Sequence[str]) -> List[str]:
    text = normalize_match_text(json.dumps(payload, ensure_ascii=False))
    return [kw for kw in keywords if kw and normalize_match_text(kw) in text][:12]


def normalize_match_text(value: Any) -> str:
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", str(value or "").lower())


def evidence_query_for_company(product: str, company: Dict[str, Any]) -> Dict[str, Any]:
    name = str(company.get("name") or "")
    company_id = str(company.get("id") or name)
    if product == "专利搜索":
        return {
            "keyword": name,
            "key_type": "申请人",
            "extra": {"pageIndex": 1, "pageSize": 10, "keywordType": "申请人"},
        }
    return {
        "keyword": company_id,
        "key_type": "nameId" if company.get("id") else "name",
        "extra": {"pageIndex": 1, "pageSize": 10},
    }


def seed_aliases(value: Any) -> List[str]:
    """Return searchable aliases for a representative-company display name."""
    text = str(value or "").strip()
    if not text:
        return []
    aliases = [text]
    chinese = re.split(r"[（(]", text, maxsplit=1)[0].strip()
    if chinese:
        aliases.append(chinese)
        short = SEED_SUFFIX_RE.sub("", chinese).strip()
        if len(short) >= 2:
            aliases.append(short)
    parenthetical = re.findall(r"[（(]([^）)]+)[）)]", text)
    aliases.extend(item.strip() for item in parenthetical if len(item.strip()) >= 2)
    return dedupe(aliases, 6)


def project_seed_names(project: Dict[str, Any], node: str, path: Sequence[str], limit: int = 8) -> List[str]:
    if limit <= 0:
        return []
    seeds: List[str] = []
    matched_nodes = project.get("matched_nodes") if isinstance(project, dict) else None
    if isinstance(matched_nodes, list):
        for item in matched_nodes:
            if not isinstance(item, dict):
                continue
            if name_score(node, str(item.get("node_name") or "")) < 70:
                continue
            for link in item.get("link_samples") or []:
                if isinstance(link, dict) and link.get("enterprise"):
                    seeds.append(str(link["enterprise"]))
    for link in project.get("representative_links") or []:
        if not isinstance(link, dict) or not link.get("enterprise"):
            continue
        link_path = [str(item) for item in link.get("path") or []]
        same_path = bool(path and link_path and path == link_path)
        if same_path or name_score(node, str(link.get("node") or "")) >= 70:
            seeds.append(str(link["enterprise"]))
    return dedupe(seeds, limit)


def seed_lookup_condition(seed_name: str) -> Dict[str, Any]:
    aliases = seed_aliases(seed_name)
    return {
        "must": [
            {"operStatus_v2": [{"eq": [["营业"]]}]},
            {"enterpriseType": [{"neq": [["个体户"]]}]},
            {"name": [{"in": aliases[:10]}]},
        ]
    }


def merge_candidate(
    merged: Dict[str, Dict[str, Any]],
    company: Dict[str, Any],
    route_id: str,
    *,
    seed_name: str | None = None,
) -> None:
    name = str(company.get("name") or "").strip()
    if not name:
        return
    key = str(company.get("id") or normalize_match_text(name))
    if not key:
        return
    current = merged.get(key)
    if not current:
        current = dict(company)
        current["recall_routes"] = []
        current["project_seeds"] = []
        current["recall_score"] = 0
        merged[key] = current
    if route_id not in current["recall_routes"]:
        current["recall_routes"].append(route_id)
        weights = [int(ROUTE_WEIGHTS.get(item, 1)) for item in current["recall_routes"]]
        current["recall_score"] = max(weights) + min(max(len(weights) - 1, 0), 3)
    if seed_name and seed_name not in current["project_seeds"]:
        current["project_seeds"].append(seed_name)


def seed_match_score(seed_name: str, candidate_name: str) -> int:
    aliases = seed_aliases(seed_name)
    chinese_alias = next((item for item in aliases if re.search(r"[\u4e00-\u9fff]", item) and "(" not in item and "（" not in item), "")
    if not chinese_alias or chinese_alias not in candidate_name:
        return max((name_score(alias, candidate_name) for alias in aliases), default=0)
    prefix, suffix = candidate_name.split(chinese_alias, 1)
    score = 100
    if prefix and not re.fullmatch(r"[\u4e00-\u9fff]{1,8}(?:省|市|县|区)", prefix):
        score -= 15
    suffix_without_legal = SEED_SUFFIX_RE.sub("", suffix).strip()
    if not suffix_without_legal:
        score += 30
    elif re.fullmatch(r"[（(](?:中国|中国大陆|香港|澳门)[）)]", suffix_without_legal):
        score += 25
    elif "自动化" in suffix_without_legal:
        score += 5
    if any(term in candidate_name for term in ("分公司", "工会委员会", "办事处")):
        score -= 40
    if candidate_name.endswith("厂"):
        score -= 20
    return score


def select_seed_matches(seed_name: str, rows: Sequence[Dict[str, Any]], limit: int = 1) -> List[Dict[str, Any]]:
    ranked: List[tuple[int, int, Dict[str, Any]]] = []
    for index, row in enumerate(rows):
        candidate_name = str(row.get("name") or "")
        score = seed_match_score(seed_name, candidate_name)
        if score >= 70:
            ranked.append((score, -index, row))
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [item[2] for item in ranked[:limit]]


def collect_candidate_evidence(
    company: Dict[str, Any],
    products: Sequence[str],
    *,
    remote: bool,
    config_path: str | None = None,
    handaas: Dict[str, Any] | None = None,
    timeout: int = 120,
) -> Dict[str, Any]:
    evidence: Dict[str, Any] = {}
    for product in products:
        query = evidence_query_for_company(product, company)
        try:
            if remote:
                evidence[product] = call_remote_evidence(
                    product,
                    query["keyword"],
                    query["key_type"],
                    query["extra"],
                    config_path=config_path,
                    timeout=timeout,
                )
            else:
                if not handaas:
                    raise ConfigError("本地证据复核缺少 handaas 配置")
                evidence[product] = call_handaas(
                    handaas,
                    product,
                    query["keyword"],
                    query["key_type"],
                    query["extra"],
                    timeout=timeout,
                )
        except Exception as exc:
            evidence[product] = {"product": product, "error": str(exc)}
    return evidence


def signal_hits(text: Any, terms: Sequence[str], limit: int = 8) -> List[str]:
    normalized_text = normalize_match_text(text)
    return dedupe([
        term
        for term in terms
        if len(normalize_match_text(term)) >= 2 and normalize_match_text(term) in normalized_text
    ], limit)


def assess_business_fit(score: int, source_count: int, conflict_hits: Sequence[str], evidence_present: bool) -> Dict[str, str]:
    if not evidence_present:
        return {"status": "unreviewed", "reason": "尚未采集企业业务证据"}
    if score >= 50 and source_count >= 2 and not conflict_hits:
        return {"status": "matched", "reason": f"{source_count} 个独立来源支持该企业从事目标节点相关业务"}
    if score >= 30 or source_count >= 1:
        return {"status": "partial", "reason": "存在相关业务信号，但来源覆盖或匹配强度不足"}
    return {"status": "not_matched", "reason": "未发现足够的目标节点主营业务信号"}


def classify_candidate(
    company: Dict[str, Any],
    evidence: Dict[str, Any],
    node: str,
    keywords: Sequence[str],
    *,
    keyword_profile: Dict[str, List[str]] | None = None,
) -> Dict[str, Any]:
    profile = keyword_profile or {
        "exact": dedupe([node, *keywords], 10),
        "supporting": [],
        "name_noise": [],
        "text_noise": [],
    }
    exact_terms = dedupe([node, *keywords, *(profile.get("exact") or [])], 12)
    supporting_terms = dedupe(profile.get("supporting") or [], 16)
    name_conflicts = signal_hits(company.get("name"), profile.get("name_noise") or [])
    text_noise_terms = dedupe(profile.get("text_noise") or [], 20)
    per_source: Dict[str, Dict[str, Any]] = {}
    conflict_hits: List[str] = list(name_conflicts)
    for signal in evidence_signals(evidence):
        source = str(signal.get("source") or "其他证据")
        text = str(signal.get("text") or "")
        exact_hits = signal_hits(text, exact_terms)
        supporting_hits = signal_hits(text, supporting_terms)
        conflicts = signal_hits(text, text_noise_terms)
        conflict_hits.extend(conflicts)
        if source in STRONG_REVIEW_SOURCES:
            score = (34 if exact_hits else 20 if supporting_hits else 0) + min(len(exact_hits) + len(supporting_hits), 4) * 2
            tier = "strong"
        elif source in MEDIUM_REVIEW_SOURCES:
            score = (24 if exact_hits else 12 if supporting_hits else 0) + min(len(exact_hits) + len(supporting_hits), 4)
            tier = "medium"
        else:
            score = 16 if exact_hits else 8 if supporting_hits else 0
            tier = "weak"
        if score <= 0:
            continue
        row = {
            "source": source,
            "tier": tier,
            "score": score,
            "exact_hits": exact_hits,
            "supporting_hits": supporting_hits,
            "snippet": text[:180],
        }
        current = per_source.get(source)
        if not current or score > int(current.get("score") or 0):
            per_source[source] = row

    matches = sorted(per_source.values(), key=lambda item: int(item["score"]), reverse=True)
    source_count = len(matches)
    strong_source_count = sum(1 for item in matches if item["source"] in STRONG_REVIEW_SOURCES)
    score = min(100, sum(int(item["score"]) for item in matches[:3]) + max(source_count - 1, 0) * 4)
    if conflict_hits:
        score = max(0, score - min(25, len(set(conflict_hits)) * 10))
    business_fit = assess_business_fit(score, source_count, conflict_hits, bool(evidence))

    if not evidence:
        decision, strength, action = "uncertain", "weak", "collect evidence"
        reason = "高筛候选尚未执行企业级证据复核"
    elif score >= 65 and strong_source_count >= 1 and source_count >= 2 and not conflict_hits:
        decision, strength, action = "confirmed", "strong", "confirm link"
        reason = f"{source_count} 个独立证据来源共同命中，含 {strong_source_count} 个强证据来源"
    elif score >= 30 or strong_source_count >= 1:
        decision, strength, action = "uncertain", "medium", "manual review"
        reason = f"现有证据得分 {score}/100，尚未同时满足强证据与独立来源要求"
    else:
        decision, strength, action = "rejected", "weak", "reject and refine exclusions"
        reason = "未发现与目标 L5 节点直接相关的产品、技术或项目证据"
    if conflict_hits:
        reason += f"；检测到噪声信号：{'、'.join(dedupe(conflict_hits, 4))}"
    return {
        "enterprise_name": company.get("name"),
        "enterprise_id": company.get("id"),
        "decision": decision,
        "evidence_strength": strength,
        "matched_segment": node,
        "review_score": score,
        "evidence_source_count": source_count,
        "strong_source_count": strong_source_count,
        "business_fit": business_fit["status"],
        "business_fit_reason": business_fit["reason"],
        "matched_evidence": matches[:6],
        "conflict_hits": dedupe(conflict_hits, 8),
        "evidence_errors": [
            {"source": product, "error": evidence_error(payload)}
            for product, payload in evidence.items()
            if evidence_error(payload)
        ],
        "reason": reason,
        "next_action": action,
        "recall_routes": list(company.get("recall_routes") or []),
        "project_seeds": list(company.get("project_seeds") or []),
        "recall_score": int(company.get("recall_score") or 0),
    }


def emit_outputs(payload: Dict[str, Any], args: argparse.Namespace) -> bool:
    report_result = None
    if args.report_output:
        payload["report_artifacts"] = {"node_linking_report": str(Path(args.report_output).expanduser())}
        report_result = write_report(payload, args.report_output, fmt=args.report_format, title=args.report_title)
    if args.output:
        output = Path(args.output).expanduser()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json_dumps(payload, pretty=True), encoding="utf-8")
        print_json({"ok": True, "output": str(output), "report": report_result, "link_summary": payload.get("link_summary")})
        return True
    if report_result:
        print_json({"ok": True, "report": report_result, "link_summary": payload.get("link_summary")})
        return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate precise high-screen ES and review enterprises for one L5 node.")
    parser.add_argument("--config", help="Config JSON path.")
    parser.add_argument("--chain", required=True)
    parser.add_argument("--node", required=True)
    parser.add_argument("--path", help="Full node path separated by > or /.")
    parser.add_argument("--condition-file", help="Use existing condition JSON instead of building one.")
    parser.add_argument("--keyword", action="append", default=[])
    parser.add_argument("--industry", action="append", default=[])
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--page-size", type=int, default=10)
    parser.add_argument("--precision", choices=["strict", "balanced"], default="strict")
    parser.add_argument("--project-root", help="industry-chain-map project root")
    parser.add_argument("--project-chain", help="Canonical project chain override")
    parser.add_argument("--project-node", help="Canonical project L5 node override")
    parser.add_argument("--with-evidence", action="store_true", help="Call configured evidence products for sample companies.")
    parser.add_argument("--evidence-product", action="append", default=[], help="Evidence product name. Repeatable.")
    parser.add_argument("--require-es", action="store_true", help="Fail instead of using MCP keyword fallback when local high-screen ES is unavailable.")
    parser.add_argument("--include-raw-evidence", action="store_true", help="Include full evidence payloads in output.")
    parser.add_argument("--seed-limit", type=int, default=8, help="Maximum project representative-company seeds to resolve.")
    parser.add_argument("--max-candidates", type=int, default=20, help="Maximum merged candidates sent to evidence review.")
    parser.add_argument("--skip-project-seeds", action="store_true", help="Do not use representative-company seeds as a recall route.")
    parser.add_argument("--output", help="Write complete linking result JSON to file.")
    parser.add_argument("--report-output", help="Write a business-ready HTML or Markdown node-linking report")
    parser.add_argument("--report-format", choices=["html", "markdown", "md"], help="Report format; defaults from report file extension")
    parser.add_argument("--report-title", help="Report title")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--local", action="store_true", help="Force local high-screen and local evidence config.")
    args = parser.parse_args()

    path = parse_path(args.path, args.chain, args.node)
    project = build_project_context(
        args.chain,
        args.project_node or args.node,
        project_root=args.project_root,
        preferred_chain=args.project_chain,
        limit=4,
    )
    plan = build_search_plan(
        args.chain,
        args.node,
        path,
        args.keyword,
        args.industry,
        args.exclude,
        precision=args.precision,
        project_context=project if project.get("available") else None,
    )
    if args.condition_file:
        with open(args.condition_file, "r", encoding="utf-8") as handle:
            plan["condition"], _ = normalize_legacy_negative_groups(json.load(handle))
        plan["condition_origin"] = "external_condition_file"
        plan["recall_strategy"] = "single_route"
        plan["recall_routes"] = [{
            "id": "external_condition",
            "purpose": "使用调用方提供的高筛条件",
            "condition": plan["condition"],
        }]
    condition = plan["condition"]

    config: Dict[str, Any] | None = None
    high_screen: Dict[str, Any] | None = None
    try:
        config, _ = load_config(args.config)
        high_screen = get_high_screen_section(config)
    except ConfigError:
        config = None
        high_screen = None

    remote_enabled = not args.local and has_remote_mcp_config(args.config)
    page_size = min(max(args.page_size, 1), 50)
    products = args.evidence_product or DEFAULT_EVIDENCE_PRODUCTS
    if high_screen:
        search_capability = "handaas_high_screen_es"
        search_mode = "local_es"
    elif remote_enabled:
        search_capability = "handaas_mcp_keyword_fallback"
        search_mode = "mcp_keyword_fallback"
    else:
        if not args.dry_run:
            raise SystemExit("未配置可执行的高筛 ES 或 Remote MCP。请配置 high_screen，或配置 MCP 后使用关键词降级模式。")
        example_config, _ = load_config(args.config, allow_example=True)
        high_screen = get_high_screen_section(example_config)
        search_capability = "handaas_high_screen_es_dry_run"
        search_mode = "local_es"
    if args.require_es and search_mode != "local_es":
        raise SystemExit("当前仅有 Remote MCP 关键词召回，无法执行完整高筛 ES；--require-es 已拒绝降级。")

    if args.dry_run:
        enterprise_search: Dict[str, Any]
        if search_mode == "local_es":
            enterprise_search = {
                "request": redact(build_enterprise_search_request(high_screen or {}, condition, 1, page_size, pagination=True)),
                "capability": search_capability,
            }
        else:
            enterprise_search = {
                "tool": REMOTE_SEARCH_TOOL,
                "keywords": extract_keywords_from_condition(condition, [plan["node_context"]["node"], plan["node_context"]["chain"]], limit=8),
                "pageSize": page_size,
                "capability": search_capability,
                "precision_limited": True,
            }
        payload = {
            "report_type": "enterprise_node_linking",
            "title": args.report_title or f"{plan['node_context']['chain']} - {plan['node_context']['node']} 节点企业挂链方案报告",
            "dry_run": True,
            "chain": plan["node_context"]["chain"],
            "node": plan["node_context"]["node"],
            "path": plan["node_context"]["canonical_path"],
            "search_plan": plan,
            "enterprise_search": enterprise_search,
            "evidence_products": products,
            "link_summary": {
                "candidate_count": 0,
                "confirmed": 0,
                "manual_review": 0,
                "rejected": 0,
                "evidence_reviewed": False,
            },
            "project_seeds": [] if args.skip_project_seeds else project_seed_names(
                project,
                plan["node_context"]["node"],
                plan["node_context"]["canonical_path"],
                max(args.seed_limit, 0),
            ),
            "summary": f"围绕“{plan['node_context']['node']}”节点形成企业高筛条件、召回路线与证据复核方案。",
        }
        if not emit_outputs(payload, args):
            print_json(payload)
        return

    merged_candidates: Dict[str, Dict[str, Any]] = {}
    route_results: List[Dict[str, Any]] = []
    for route in plan.get("recall_routes") or [{"id": "primary", "condition": condition}]:
        route_id = str(route.get("id") or "primary")
        route_condition = route.get("condition") or condition
        if search_mode == "local_es":
            route_preview = call_enterprise_search_preview(high_screen or {}, route_condition, 1, page_size, timeout=120)
        else:
            route_preview = call_remote_enterprise_search_preview(
                route_condition,
                chain=plan["node_context"]["chain"],
                node=plan["node_context"]["node"],
                page_index=1,
                page_size=page_size,
                config_path=args.config,
                timeout=120,
            )
        route_rows = [item for item in route_preview.get("samples", []) if isinstance(item, dict)]
        for company in route_rows:
            merge_candidate(merged_candidates, company, route_id)
        route_results.append({
            "route_id": route_id,
            "purpose": route.get("purpose"),
            "priority": route.get("priority"),
            "business_fields": route.get("business_fields") or [],
            "total": route_preview.get("total"),
            "sample_count": len(route_rows),
            "errors": route_preview.get("errors") or [],
        })

    seeds = [] if args.skip_project_seeds else project_seed_names(
        project,
        plan["node_context"]["node"],
        plan["node_context"]["canonical_path"],
        max(args.seed_limit, 0),
    )
    seed_results: List[Dict[str, Any]] = []
    for seed_name in seeds:
        seed_condition = seed_lookup_condition(seed_name)
        if search_mode == "local_es":
            seed_preview = call_enterprise_search_preview(high_screen or {}, seed_condition, 1, 10, timeout=120)
        else:
            seed_preview = call_remote_enterprise_search_preview(
                seed_condition,
                chain=plan["node_context"]["chain"],
                node=seed_name,
                page_index=1,
                page_size=10,
                config_path=args.config,
                timeout=120,
            )
        seed_rows = [item for item in seed_preview.get("samples", []) if isinstance(item, dict)]
        selected = select_seed_matches(seed_name, seed_rows)
        if not selected:
            selected = [{"id": None, "name": seed_aliases(seed_name)[0], "seed_only": True}]
        for company in selected:
            merge_candidate(merged_candidates, company, "project_seed", seed_name=seed_name)
        seed_results.append({
            "seed": seed_name,
            "resolved": bool(selected and not selected[0].get("seed_only")),
            "enterprise": selected[0].get("name") if selected else None,
        })

    all_candidates = sorted(
        merged_candidates.values(),
        key=lambda item: (
            int(item.get("recall_score") or 0),
            len(item.get("recall_routes") or []),
            bool(item.get("project_seeds")),
        ),
        reverse=True,
    )
    candidate_limit = max(args.max_candidates, 1)
    candidates = all_candidates[:candidate_limit]
    preview = {
        "mode": search_mode,
        "route_results": route_results,
        "seed_results": seed_results,
        "unique_candidate_count_before_limit": len(all_candidates),
        "selected_candidate_count": len(candidates),
        "samples": candidates,
    }

    evidence_remote = remote_enabled and not args.local
    handaas: Dict[str, Any] | None = None
    if args.with_evidence and not evidence_remote and config:
        try:
            handaas = get_handaas_section(config)
        except ConfigError:
            handaas = None
    decisions: List[Dict[str, Any]] = []
    evidence_results: Dict[str, Dict[str, Any]] = {}
    for company in candidates:
        per_company: Dict[str, Any] = {}
        if args.with_evidence:
            per_company = collect_candidate_evidence(
                company,
                products,
                remote=evidence_remote,
                config_path=args.config,
                handaas=handaas,
                timeout=120,
            )
            if args.include_raw_evidence:
                evidence_results[str(company.get("name"))] = per_company
        decisions.append(classify_candidate(
            company,
            per_company,
            plan["node_context"]["node"],
            args.keyword,
            keyword_profile=plan["keyword_profile"],
        ))
    decisions.sort(key=lambda item: int(item.get("review_score") or 0), reverse=True)
    reviewed = [item for item in decisions if item.get("decision") in {"confirmed", "uncertain"}]
    rejected = [item for item in decisions if item.get("decision") == "rejected"]
    payload = {
        "report_type": "enterprise_node_linking",
        "title": args.report_title or f"{plan['node_context']['chain']} - {plan['node_context']['node']} 节点企业挂链报告",
        "mode": search_mode,
        "search_capability": search_capability,
        "precision_limited": search_mode != "local_es",
        "chain": plan["node_context"]["chain"],
        "node": plan["node_context"]["node"],
        "path": plan["node_context"]["canonical_path"],
        "search_plan": plan,
        "condition": condition,
        "preview": preview,
        "link_summary": {
            "candidate_count": len(candidates),
            "confirmed": sum(1 for item in decisions if item.get("decision") == "confirmed"),
            "manual_review": sum(1 for item in decisions if item.get("decision") == "uncertain"),
            "rejected": len(rejected),
            "evidence_reviewed": bool(args.with_evidence),
        },
        "summary": (
            f"围绕“{plan['node_context']['node']}”节点复核 {len(candidates)} 家候选企业，"
            f"确认挂链 {sum(1 for item in decisions if item.get('decision') == 'confirmed')} 家，"
            f"待复核 {sum(1 for item in decisions if item.get('decision') == 'uncertain')} 家，"
            f"排除 {len(rejected)} 家。"
        ),
        "reviewed_enterprises": reviewed,
        "rejected_enterprises": rejected,
        "decisions": decisions,
        "evidence": evidence_results,
        "next_actions": [
            "确认 strong 且多来源一致的企业挂链",
            "人工复核 uncertain 企业的官网产品、专利或项目材料",
            "把 rejected 企业的噪声特征补充到节点排除词后重新运行",
        ],
    }
    if search_mode != "local_es":
        payload["next_actions"].insert(0, "配置 high_screen 后执行完整 ES，当前 Remote MCP 结果仅作召回预览")
    if not emit_outputs(payload, args):
        print_json(payload)


if __name__ == "__main__":
    main()
