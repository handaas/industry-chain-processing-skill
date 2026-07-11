#!/usr/bin/env python3
"""Position one enterprise across project industry chains from HandaaS evidence."""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from common import get_handaas_section, json_dumps, load_config, print_json
from evidence_call import call_handaas, call_remote_evidence
from mcp_client import call_tool, has_remote_mcp_config
from project_context import normalize_text, read_archive_chains, read_static_chains, resolve_project_root
from render_report import write_report


DEFAULT_POSITIONING_PRODUCTS = ["工商照面", "企业简介", "企业业务", "企业标签", "专利搜索", "企业招投标信息"]
SOURCE_WEIGHTS = {
    "工商照面": 2.5,
    "企业简介": 3.0,
    "企业业务": 5.0,
    "企业标签": 3.5,
    "专利搜索": 5.0,
    "企业招投标信息": 3.2,
}
GENERIC_NODE_NAMES = {
    "工业", "工业自动化", "工业互联网", "工业机器人", "机器人", "新能源", "智能制造",
    "系统集成", "数据采集", "技术服务", "软件开发", "检测设备", "自动化集成", "行业应用软件",
}
GENERIC_MODULE_NAMES = {"工业", "行业应用", "应用领域", "系统集成", "控制系统", "工业互联网"}
GENERIC_FORM_NAMES = {"设备", "系统", "服务", "技术", "产品", "材料", "软件", "平台", "装置", "领域"}
GENERIC_SUFFIXES = ("总体解决方案", "解决方案", "系统集成", "管理系统", "控制系统", "服务平台", "软件平台", "平台", "系统", "设备", "软件", "服务", "技术", "产品")
LEGAL_SUFFIXES = (
    "股份有限公司", "有限责任公司", "集团有限公司", "控股有限公司", "股份公司", "分公司",
    "有限公司", "研究院", "研究所", "集团", "公司", "工厂", "厂",
)


def as_list(value: Any) -> List[Any]:
    if value in (None, ""):
        return []
    return value if isinstance(value, list) else [value]


def compact(value: Any, limit: int = 220) -> str:
    text = " ".join(str(value or "").replace("\n", " ").split()).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip("，,；;。 ") + "…"


def normalized(value: Any) -> str:
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", normalize_text(value))


def plain_normalized(value: Any) -> str:
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", str(value or "").lower())


def unique(values: Iterable[Any], limit: int = 20) -> List[str]:
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


def extract_rows(value: Any) -> List[Mapping[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, Mapping)]
    if isinstance(value, Mapping):
        for key in ("resultList", "list", "items", "records", "data"):
            nested = value.get(key)
            rows = extract_rows(nested)
            if rows:
                return rows
    return []


def unwrap_evidence(payload: Any) -> Any:
    if isinstance(payload, Mapping) and "data" in payload:
        return payload.get("data")
    return payload


def evidence_error(payload: Any) -> str:
    current = payload
    for _ in range(3):
        if not isinstance(current, Mapping):
            return ""
        error = current.get("error")
        if error:
            message = current.get("message") or current.get("msgCN") or current.get("msgCn")
            return compact(f"{error}：{message}" if message and str(message) != str(error) else error, 180)
        if "data" not in current:
            return ""
        current = current.get("data")
    return ""


def enterprise_identity(item: Mapping[str, Any], fallback: str) -> Dict[str, str]:
    return {
        "name": str(item.get("name") or item.get("enterpriseName") or item.get("entName") or fallback),
        "name_id": str(item.get("nameId") or item.get("nameID") or item.get("_id") or item.get("id") or ""),
        "social_credit_code": str(item.get("socialCreditCode") or item.get("creditCode") or ""),
        "registration_number": str(item.get("regNumber") or item.get("registrationNumber") or ""),
    }


def choose_enterprise(rows: Sequence[Mapping[str, Any]], query: str) -> Dict[str, str]:
    if not rows:
        return enterprise_identity({}, query)
    query_norm = normalized(query)
    ranked = sorted(
        rows,
        key=lambda item: (
            normalized(item.get("name") or item.get("enterpriseName")) == query_norm,
            query_norm in normalized(item.get("name") or item.get("enterpriseName")),
        ),
        reverse=True,
    )
    return enterprise_identity(ranked[0], query)


def resolve_remote_enterprise(query: str, config: Optional[str], timeout: int) -> Dict[str, Any]:
    payload = call_tool(
        "enterprise_get_keyword_search",
        {"matchKeyword": query, "pageIndex": 1, "pageSize": 10},
        config_path=config,
        timeout=timeout,
    )
    rows = extract_rows(payload)
    return {"identity": choose_enterprise(rows, query), "candidates": [enterprise_identity(item, query) for item in rows[:10]]}


def collect_remote_evidence_set(
    identity: Mapping[str, str],
    products: Sequence[str],
    config: Optional[str],
    timeout: int,
) -> Dict[str, Any]:
    canonical_name = str(identity.get("name") or "")
    name_id = str(identity.get("name_id") or "")
    evidence: Dict[str, Any] = {}
    for product in products:
        try:
            if product == "专利搜索":
                evidence[product] = call_remote_evidence(
                    product,
                    canonical_name,
                    "申请人",
                    {"pageIndex": 1, "pageSize": 20, "keywordType": "申请人"},
                    config_path=config,
                    timeout=timeout,
                )
            else:
                evidence[product] = call_remote_evidence(
                    product,
                    name_id or canonical_name,
                    "nameId" if name_id else "name",
                    {"pageIndex": 1, "pageSize": 20},
                    config_path=config,
                    timeout=timeout,
                )
        except Exception as exc:
            evidence[product] = {"product": product, "error": str(exc)}
    return evidence


def collect_local_evidence_set(
    query: str,
    products: Sequence[str],
    config_path: Optional[str],
    timeout: int,
) -> tuple[Dict[str, str], Dict[str, Any]]:
    config, _ = load_config(config_path)
    handaas = get_handaas_section(config)
    evidence: Dict[str, Any] = {}
    try:
        evidence["工商照面"] = call_handaas(handaas, "工商照面", query, "name", timeout=timeout)
    except Exception as exc:
        evidence["工商照面"] = {"product": "工商照面", "error": str(exc)}
    base = unwrap_evidence(evidence.get("工商照面"))
    identity = enterprise_identity(base if isinstance(base, Mapping) else {}, query)
    name_id = identity.get("name_id") or ""
    for product in products:
        if product == "工商照面":
            continue
        try:
            keyword = identity.get("name") if product == "专利搜索" else name_id or query
            key_type = "申请人" if product == "专利搜索" else "nameId" if name_id else "name"
            evidence[product] = call_handaas(handaas, product, str(keyword), key_type, {"pageIndex": 1, "pageSize": 20}, timeout=timeout)
        except Exception as exc:
            evidence[product] = {"product": product, "error": str(exc)}
    return identity, evidence


def add_signal(signals: List[Dict[str, Any]], source: str, text: Any, weight: Optional[float] = None) -> None:
    value = compact(text, 600)
    if not value or len(normalized(value)) < 2:
        return
    signals.append({"source": source, "weight": float(weight or SOURCE_WEIGHTS.get(source, 2.0)), "text": value})


def evidence_signals(evidence: Mapping[str, Any]) -> List[Dict[str, Any]]:
    signals: List[Dict[str, Any]] = []
    for product, payload in evidence.items():
        data = unwrap_evidence(payload)
        if not isinstance(data, Mapping):
            continue
        if product == "工商照面":
            add_signal(signals, product, data.get("business") or data.get("businessScope"))
            industry = data.get("industry")
            if isinstance(industry, Mapping):
                for key in ("firstIndustry", "secondIndustry", "thirdIndustry", "fourthIndustry"):
                    add_signal(signals, product, industry.get(key), 2.0)
            for key in ("mainProducts", "product", "businessTags"):
                for item in as_list(data.get(key)):
                    add_signal(signals, product, item)
        elif product == "企业简介":
            add_signal(signals, product, data.get("desc") or data.get("profile") or data.get("introduction"))
        elif product == "企业业务":
            for row in extract_rows(data):
                for key, weight in (("productName", 5.5), ("productDomain", 4.5), ("tags", 4.0), ("desc", 3.5), ("description", 3.5)):
                    value = row.get(key)
                    for item in as_list(value):
                        add_signal(signals, product, item, weight)
        elif product == "企业标签":
            for key in ("businessTags", "tags", "industryTags", "productTags"):
                for item in as_list(data.get(key)):
                    if isinstance(item, Mapping):
                        add_signal(signals, product, item.get("name") or item.get("tagName"))
                    else:
                        add_signal(signals, product, item)
        elif product == "专利搜索":
            for row in extract_rows(data):
                add_signal(signals, product, row.get("patentName") or row.get("title") or row.get("name"), 5.5)
                add_signal(signals, product, row.get("abstract") or row.get("summary"), 2.5)
        elif product == "企业招投标信息":
            for row in extract_rows(data):
                add_signal(signals, product, row.get("title") or row.get("biddingAnncTitle") or row.get("projectName"), 5.0)
                add_signal(signals, product, row.get("subject") or row.get("biddingContent") or row.get("content"), 3.0)
    deduped: Dict[tuple[str, str], Dict[str, Any]] = {}
    for signal in signals:
        key = (str(signal["source"]), normalized(signal["text"]))
        if key not in deduped or signal["weight"] > deduped[key]["weight"]:
            deduped[key] = signal
    return list(deduped.values())


def profile_from_evidence(identity: Mapping[str, str], evidence: Mapping[str, Any]) -> Dict[str, Any]:
    base = unwrap_evidence(evidence.get("工商照面"))
    profile = unwrap_evidence(evidence.get("企业简介"))
    business = unwrap_evidence(evidence.get("企业业务"))
    tags = unwrap_evidence(evidence.get("企业标签"))
    base = base if isinstance(base, Mapping) else {}
    profile = profile if isinstance(profile, Mapping) else {}
    industry = base.get("industry") if isinstance(base.get("industry"), Mapping) else {}
    products = unique(
        row.get("productName") or row.get("productDomain")
        for row in extract_rows(business)
    )
    tag_values: List[Any] = []
    if isinstance(tags, Mapping):
        for key in ("businessTags", "tags", "industryTags", "productTags"):
            for item in as_list(tags.get(key)):
                tag_values.append(item.get("name") or item.get("tagName") if isinstance(item, Mapping) else item)
    return {
        "name": identity.get("name") or base.get("name") or "",
        "name_id": identity.get("name_id") or base.get("nameId") or "",
        "social_credit_code": identity.get("social_credit_code") or base.get("socialCreditCode") or "",
        "oper_status": base.get("operStatus") or "",
        "address": base.get("address") or "",
        "registered_industry": " / ".join(str(industry.get(key) or "") for key in ("firstIndustry", "secondIndustry", "thirdIndustry", "fourthIndustry") if industry.get(key)),
        "business_scope": compact(base.get("business") or base.get("businessScope"), 500),
        "profile": compact(profile.get("desc") or profile.get("profile") or profile.get("introduction"), 500),
        "business_products": "、".join(products[:12]),
        "business_tags": "、".join(unique(tag_values, limit=20)),
    }


def load_project_chains(project_root: Optional[str]) -> tuple[Optional[Path], List[Dict[str, Any]]]:
    root = resolve_project_root(project_root)
    if not root:
        return None, []
    chains = read_archive_chains(root) + read_static_chains(root)
    selected: Dict[str, Dict[str, Any]] = {}
    for chain in chains:
        name = str(chain.get("chain_name") or "").strip()
        key = normalize_text(name)
        if not key or not chain.get("l5_nodes"):
            continue
        if key not in selected or chain.get("source") == "sqlite_archive":
            selected[key] = chain
    return root, list(selected.values())


def company_forms(value: Any) -> List[str]:
    text = re.sub(r"[（(].*?[）)]", "", str(value or ""))
    forms = [plain_normalized(text)]
    stripped = text.strip()
    changed = True
    while changed:
        changed = False
        for suffix in LEGAL_SUFFIXES:
            if stripped.endswith(suffix):
                stripped = stripped[: -len(suffix)].strip()
                forms.append(plain_normalized(stripped))
                changed = True
                break
    without_location = re.sub(r"^(?:中国)?(?:[\u4e00-\u9fff]{2,8}?(?:省|自治区|特别行政区|市|区|县)){1,2}", "", stripped)
    if without_location != stripped:
        forms.append(plain_normalized(without_location))
    return sorted((item for item in unique(forms, limit=8) if len(item) >= 4), key=len, reverse=True)


def representative_anchor(node: Mapping[str, Any], enterprise_name: str) -> Dict[str, Any]:
    enterprise_forms = company_forms(enterprise_name)
    best: Dict[str, Any] = {}
    for representative in as_list(node.get("representative_companies")):
        representative_forms = company_forms(representative)
        for enterprise_form in enterprise_forms:
            for representative_form in representative_forms:
                shorter = min(len(enterprise_form), len(representative_form))
                if shorter < 4:
                    continue
                if enterprise_form == representative_form:
                    strength = 1.0
                elif enterprise_form in representative_form or representative_form in enterprise_form:
                    strength = min(0.96, 0.78 + shorter * 0.025)
                else:
                    continue
                if strength > float(best.get("strength") or 0):
                    best = {"strength": round(strength, 2), "representative": str(representative)}
    return best


def node_forms(name: str) -> List[str]:
    base = normalized(re.sub(r"[（(].*?[）)]", "", name))
    forms = [normalized(name), base]
    forms.extend(
        part
        for part in (normalized(item) for item in re.split(r"[/、及与和]", name))
        if part not in GENERIC_FORM_NAMES
    )
    for suffix in GENERIC_SUFFIXES:
        suffix_norm = normalized(suffix)
        if base.endswith(suffix_norm) and len(base) - len(suffix_norm) >= 2:
            forms.append(base[: -len(suffix_norm)])
    return unique(forms, limit=6)


def bigram_coverage(term: str, text: str) -> float:
    if len(term) < 4 or len(text) < 4:
        return 0.0
    term_pairs = {term[index:index + 2] for index in range(len(term) - 1)}
    text_pairs = {text[index:index + 2] for index in range(len(text) - 1)}
    return len(term_pairs & text_pairs) / max(len(term_pairs), 1)


def score_node(
    chain: Mapping[str, Any],
    node: Mapping[str, Any],
    signals: Sequence[Mapping[str, Any]],
    enterprise_name: str = "",
) -> Dict[str, Any]:
    path = [str(part) for part in as_list(node.get("path"))]
    node_name = str(node.get("name") or (path[-1] if path else ""))
    l2 = path[1] if len(path) > 1 else ""
    l3 = path[2] if len(path) > 2 else ""
    forms = node_forms(node_name)
    module_norm = normalized(l3)
    source_best: Dict[str, Dict[str, Any]] = {}

    for signal in signals:
        source = str(signal.get("source") or "其他证据")
        weight = float(signal.get("weight") or 2.0)
        signal_text = str(signal.get("text") or "")
        signal_norm = normalized(signal_text)
        best = 0.0
        matched_term = ""
        match_type = ""
        for index, form in enumerate(forms):
            if len(form) < 2:
                continue
            if form in signal_norm:
                candidate = (18 if index == 0 else 10) + weight * (2.2 if index == 0 else 1.5) + min(len(form), 10) * (0.6 if index == 0 else 0.4)
                if candidate > best:
                    best, matched_term, match_type = candidate, form, "节点名称命中" if index == 0 else "核心词命中"
            else:
                coverage = bigram_coverage(form, signal_norm)
                similarity = SequenceMatcher(None, form, signal_norm).ratio() if len(signal_norm) <= 80 else 0.0
                if coverage >= 0.72:
                    candidate = 6 + weight * 1.25 + coverage * 6
                    if candidate > best:
                        best, matched_term, match_type = candidate, form, "产品技术相似"
                elif similarity >= 0.7:
                    candidate = 5 + weight * 1.1 + similarity * 5
                    if candidate > best:
                        best, matched_term, match_type = candidate, form, "名称相似"
        if len(module_norm) >= 4 and l3 not in GENERIC_MODULE_NAMES and module_norm in signal_norm:
            module_score = 3 + weight * 0.8 + min(len(module_norm), 8) * 0.3
            if module_score > best:
                best, matched_term, match_type = module_score, module_norm, "产业模块命中"
        if best <= 0:
            continue
        current = source_best.get(source)
        row = {
            "source": source,
            "score": round(best, 2),
            "matched_term": matched_term,
            "match_type": match_type,
            "snippet": compact(signal_text, 150),
        }
        if not current or best > float(current.get("score") or 0):
            source_best[source] = row

    matches = sorted(source_best.values(), key=lambda item: float(item["score"]), reverse=True)
    coefficients = (1.0, 0.85, 0.55, 0.35, 0.2)
    raw_score = sum(float(item["score"]) * coefficient for item, coefficient in zip(matches[:5], coefficients))
    raw_score += min(max(len(matches) - 1, 0) * 3, 9)
    full_matches = sum(1 for item in matches if item.get("match_type") == "节点名称命中")
    raw_score += min(full_matches * 4, 12)

    module_core = normalized(re.sub(r"(系统|领域|设备|制造|服务)$", "", l3))
    module_sources = {
        str(signal.get("source") or "")
        for signal in signals
        if len(module_core) >= 2 and l3 not in GENERIC_MODULE_NAMES and module_core in normalized(signal.get("text"))
    }
    module_bonus = min(14.0, 5.0 + len(module_sources) * 2.5) if module_sources else 0.0

    anchor = representative_anchor(node, enterprise_name) if enterprise_name else {}
    downstream_application = "下游" in l2 and any(marker in l2 for marker in ("应用", "场景", "行业"))
    role_factor = 0.62 if downstream_application else 1.0
    generic_factor = 0.64 if node_name in GENERIC_NODE_NAMES else 1.0
    if anchor:
        role_factor = max(role_factor, 0.85)
        generic_factor = max(generic_factor, 0.85)
    score = (raw_score + module_bonus) * role_factor * generic_factor
    score += float(anchor.get("strength") or 0) * 15
    score = min(99.0, score)
    confidence = "high" if score >= 72 else "medium" if score >= 48 else "low" if score >= 30 else "weak"
    evidence_sources = [item["source"] for item in matches]
    if anchor:
        evidence_sources.append("项目图谱代表企业")
    return {
        "chain": str(chain.get("chain_name") or (path[0] if path else "")),
        "chain_id": str(chain.get("chain_id") or ""),
        "l2_segment": l2,
        "l3_module": l3,
        "l5_node": node_name,
        "path": " > ".join(path),
        "score": round(score, 1),
        "confidence": confidence,
        "evidence_sources": "、".join(unique(evidence_sources, limit=8)),
        "matched_terms": "、".join(unique([item["matched_term"] for item in matches], limit=8)),
        "evidence_matches": matches[:6],
        "module_support_sources": "、".join(sorted(module_sources)),
        "project_anchor": anchor,
        "role_adjustment": "下游应用场景降权" if downstream_application and not anchor else "项目图谱企业锚点校准" if anchor else "直接产品/能力节点",
    }


def rank_positions(
    chains: Sequence[Mapping[str, Any]],
    signals: Sequence[Mapping[str, Any]],
    max_nodes: int = 12,
    max_chains: int = 5,
    enterprise_name: str = "",
) -> Dict[str, Any]:
    nodes: List[Dict[str, Any]] = []
    for chain in chains:
        for node in as_list(chain.get("l5_nodes")):
            if not isinstance(node, Mapping):
                continue
            scored = score_node(chain, node, signals, enterprise_name=enterprise_name)
            if float(scored["score"]) >= 18:
                nodes.append(scored)
    nodes.sort(key=lambda item: (float(item["score"]), len(item.get("evidence_matches") or [])), reverse=True)
    deduped_nodes: Dict[tuple[str, str], Dict[str, Any]] = {}
    for node in nodes:
        key = (str(node.get("chain") or ""), normalized(node.get("l5_node")))
        if key not in deduped_nodes:
            deduped_nodes[key] = node
    nodes = list(deduped_nodes.values())

    by_chain: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for node in nodes:
        by_chain[str(node["chain"])].append(node)
    chain_rows: List[Dict[str, Any]] = []
    for chain_name, chain_nodes in by_chain.items():
        top = chain_nodes[:3]
        distinct_modules = {str(item.get("l3_module") or "") for item in top if item.get("l3_module")}
        weighted_nodes = list(zip(top, (0.82, 0.12, 0.06)))
        chain_score = sum(float(item["score"]) * weight for item, weight in weighted_nodes)
        chain_score /= sum(weight for _, weight in weighted_nodes)
        chain_score = min(99.0, chain_score + max(len(distinct_modules) - 1, 0) * 1.5)
        chain_rows.append({
            "chain": chain_name,
            "score": round(chain_score, 1),
            "confidence": "high" if chain_score >= 75 else "medium" if chain_score >= 50 else "low",
            "best_path": top[0]["path"],
            "best_node": top[0]["l5_node"],
            "candidate_nodes": "、".join(unique((item["l5_node"] for item in top), limit=3)),
            "evidence_sources": top[0]["evidence_sources"],
            "project_anchor_count": sum(1 for item in top if item.get("project_anchor")),
        })
    chain_rows.sort(key=lambda item: float(item["score"]), reverse=True)
    primary_chain = str(chain_rows[0]["chain"]) if chain_rows else ""
    primary_node = by_chain.get(primary_chain, [None])[0] if primary_chain else None
    qualified_nodes = [item for item in nodes if float(item.get("score") or 0) >= 48]
    visible_nodes = qualified_nodes if qualified_nodes else nodes
    return {"nodes": visible_nodes[:max_nodes], "chains": chain_rows[:max_chains], "primary_node": primary_node}


def positioning_status(primary: Optional[Mapping[str, Any]], alternative: Optional[Mapping[str, Any]]) -> tuple[str, str]:
    if not primary:
        return "证据不足", "low"
    score = float(primary.get("score") or 0)
    margin = score - float(alternative.get("score") or 0) if alternative else score
    if score >= 75 and margin >= 10:
        return "明确归属", "high"
    if score >= 50:
        return "较高可能", "medium"
    return "待进一步核验", "low"


def evidence_summary_rows(evidence: Mapping[str, Any], signals: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    counts: Dict[str, int] = defaultdict(int)
    samples: Dict[str, List[str]] = defaultdict(list)
    for signal in signals:
        source = str(signal.get("source") or "其他证据")
        counts[source] += 1
        if len(samples[source]) < 3:
            samples[source].append(compact(signal.get("text"), 100))
    rows: List[Dict[str, Any]] = []
    for product in evidence:
        payload = evidence[product]
        error = evidence_error(payload)
        rows.append({
            "source": product,
            "status": "error" if error else "available" if counts.get(product) else "empty",
            "signal_count": counts.get(product, 0),
            "representative_evidence": "；".join(samples.get(product, [])) or compact(error, 180),
        })
    return rows


def build_report(args: argparse.Namespace) -> Dict[str, Any]:
    products = args.evidence_product or DEFAULT_POSITIONING_PRODUCTS
    remote_enabled = not args.local and has_remote_mcp_config(args.config)
    if args.evidence_input:
        raw = json.loads(Path(args.evidence_input).expanduser().read_text(encoding="utf-8"))
        identity = raw.get("identity") or {"name": args.enterprise, "name_id": ""}
        evidence = raw.get("evidence") or {}
        resolution_candidates = raw.get("candidates") or []
        mode = "provided_evidence"
    elif remote_enabled:
        resolution = resolve_remote_enterprise(args.enterprise, args.config, args.timeout)
        identity = resolution["identity"]
        resolution_candidates = resolution["candidates"]
        evidence = collect_remote_evidence_set(identity, products, args.config, args.timeout)
        mode = "mcp"
    else:
        identity, evidence = collect_local_evidence_set(args.enterprise, products, args.config, args.timeout)
        resolution_candidates = [identity]
        mode = "local"

    root, chains = load_project_chains(args.project_root)
    if not chains:
        raise SystemExit("未找到可用于企业归位的产业链图谱，请通过 --project-root 或 INDUSTRY_CHAIN_PROJECT_ROOT 配置 industry-chain-map。")
    signals = evidence_signals(evidence)
    profile = profile_from_evidence(identity, evidence)
    enterprise_name = str(profile.get("name") or args.enterprise)
    rankings = rank_positions(
        chains,
        signals,
        max_nodes=args.max_nodes,
        max_chains=args.max_chains,
        enterprise_name=enterprise_name,
    )
    primary = rankings.get("primary_node")
    primary_chain = rankings["chains"][0] if rankings["chains"] else None
    alternative_chain = rankings["chains"][1] if len(rankings["chains"]) > 1 else None
    status, confidence = positioning_status(primary_chain, alternative_chain)
    primary_position = {
        "status": status,
        "confidence": confidence,
        "chain": primary.get("chain") if primary else "",
        "l2_segment": primary.get("l2_segment") if primary else "",
        "l3_module": primary.get("l3_module") if primary else "",
        "l5_node": primary.get("l5_node") if primary else "",
        "path": primary.get("path") if primary else "",
        "score": primary_chain.get("score") if primary_chain else 0,
        "node_score": primary.get("score") if primary else 0,
        "evidence_sources": primary.get("evidence_sources") if primary else "",
        "matched_terms": primary.get("matched_terms") if primary else "",
        "project_anchor": primary.get("project_anchor") if primary else {},
        "role_adjustment": primary.get("role_adjustment") if primary else "",
    }
    if primary:
        summary = (
            f"{enterprise_name}的主营业务与技术证据主要指向“{primary['chain']}”产业链，"
            f"对应“{primary['l2_segment']} / {primary['l3_module']} / {primary['l5_node']}”环节；"
            f"归属判断为“{status}”，综合匹配分为 {primary_position['score']}/100。"
        )
        if alternative_chain and float(primary_chain.get("score") or 0) - float(alternative_chain.get("score") or 0) < 10:
            summary += (
                f"“{alternative_chain.get('chain')}”产业链的“{alternative_chain.get('best_node')}”节点亦形成接近匹配，"
                "反映企业存在跨产业链产品布局，主归属不等同于排他性分类。"
            )
    else:
        summary = f"现有企业业务、标签、专利及项目证据尚不足以将{enterprise_name}稳定定位到项目产业链节点。"

    return {
        "report_type": "enterprise_chain_positioning",
        "title": args.title or f"{enterprise_name}产业链环节定位分析报告",
        "enterprise": enterprise_name,
        "summary": summary,
        "enterprise_resolution": {
            "input_name": args.enterprise,
            "canonical_name": identity.get("name") or enterprise_name,
            "name_id": identity.get("name_id") or "",
            "candidate_count": len(resolution_candidates),
        },
        "enterprise_profile": profile,
        "primary_position": primary_position,
        "chain_ranking": rankings["chains"],
        "node_ranking": rankings["nodes"],
        "evidence_summary": evidence_summary_rows(evidence, signals),
        "evidence_matches": primary.get("evidence_matches") if primary else [],
        "positioning_boundary": [
            "产业链归属以企业主营产品、技术能力、专利和项目活动为主要判断依据。",
            "同一企业可能同时覆盖多个产业链节点，主归属反映当前证据最集中的业务位置。",
            "工商行业分类用于辅助识别，不单独决定产业链节点归属。",
        ],
        "data_status": {
            "mode": mode,
            "project_root": str(root or ""),
            "chain_count": len(chains),
            "signal_count": len(signals),
            "evidence_errors": sum(1 for payload in evidence.values() if evidence_error(payload)),
        },
        "evidence": evidence,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze one enterprise's most likely industry-chain segment from its name.")
    parser.add_argument("--enterprise", required=True, help="Enterprise name")
    parser.add_argument("--config", help="Config JSON path")
    parser.add_argument("--project-root", help="industry-chain-map project root")
    parser.add_argument("--evidence-product", action="append", default=[], help="Evidence product; repeatable")
    parser.add_argument("--evidence-input", help="Optional pre-collected identity/evidence JSON for offline reuse")
    parser.add_argument("--max-nodes", type=int, default=12)
    parser.add_argument("--max-chains", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--local", action="store_true", help="Force legacy local credential mode")
    parser.add_argument("--title", help="Report title")
    parser.add_argument("--output", help="Output JSON path")
    parser.add_argument("--report-output", help="Write a business-ready HTML or Markdown report")
    parser.add_argument("--report-format", choices=["html", "markdown", "md"], help="Report format; defaults from report file extension")
    args = parser.parse_args()
    payload = build_report(args)
    report_result = None
    if args.report_output:
        payload["report_artifacts"] = {"enterprise_positioning_report": str(Path(args.report_output).expanduser())}
        report_result = write_report(payload, args.report_output, fmt=args.report_format, title=args.title)
    if args.output:
        output = Path(args.output).expanduser()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json_dumps(payload, pretty=True), encoding="utf-8")
        print_json({"ok": True, "output": str(output), "report": report_result, "primary_position": payload.get("primary_position")})
    elif report_result:
        print_json({"ok": True, "report": report_result, "primary_position": payload.get("primary_position")})
    else:
        print_json(payload)


if __name__ == "__main__":
    main()
