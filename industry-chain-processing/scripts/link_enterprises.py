#!/usr/bin/env python3
"""End-to-end local enterprise matching helper for one refined industry segment."""
from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List, Sequence

from build_condition import build_condition_group, parse_path
from common import ApiError, get_handaas_section, get_high_screen_section, load_config, print_json, redact
from evidence_call import call_handaas
from enterprise_search_preview import build_enterprise_search_request, call_enterprise_search_preview

DEFAULT_EVIDENCE_PRODUCTS = ["工商照面", "招聘明细", "知识产权统计", "企业招投标信息"]


def keyword_hits(payload: Any, keywords: Sequence[str]) -> List[str]:
    text = json.dumps(payload, ensure_ascii=False)
    return [kw for kw in keywords if kw and kw in text][:12]


def classify_candidate(company: Dict[str, Any], evidence: Dict[str, Any], node: str, keywords: Sequence[str]) -> Dict[str, Any]:
    strong_sources = ["招聘明细", "知识产权统计", "企业招投标信息"]
    strong_hits: List[str] = []
    medium_hits: List[str] = []
    for product, payload in evidence.items():
        hits = keyword_hits(payload, [node, *keywords])
        if not hits:
            continue
        if product in strong_sources:
            strong_hits.extend(hits)
        else:
            medium_hits.extend(hits)
    if strong_hits:
        decision, strength, action = "confirmed", "strong", "confirm link"
        reason = f"强证据产品命中：{'、'.join(sorted(set(strong_hits))[:6])}"
    elif medium_hits:
        decision, strength, action = "uncertain", "medium", "manual review"
        reason = f"中证据命中：{'、'.join(sorted(set(medium_hits))[:6])}"
    else:
        decision, strength, action = "uncertain", "weak", "manual review"
        reason = "候选来自企业搜索召回，但尚未采集到明确强证据"
    return {
        "enterprise_name": company.get("name"),
        "enterprise_id": company.get("id"),
        "decision": decision,
        "evidence_strength": strength,
        "matched_segment": node,
        "reason": reason,
        "next_action": action,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Match enterprises for one refined industry segment using local enterprise data config.")
    parser.add_argument("--config", help="Config JSON path.")
    parser.add_argument("--chain", required=True)
    parser.add_argument("--node", required=True)
    parser.add_argument("--path", help="Full node path separated by > or /.")
    parser.add_argument("--condition-file", help="Use existing condition JSON instead of building one.")
    parser.add_argument("--keyword", action="append", default=[])
    parser.add_argument("--industry", action="append", default=[])
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--page-size", type=int, default=10)
    parser.add_argument("--with-evidence", action="store_true", help="Call configured evidence products for sample companies.")
    parser.add_argument("--evidence-product", action="append", default=[], help="Evidence product name. Repeatable.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    path = parse_path(args.path, args.chain, args.node)
    if args.condition_file:
        with open(args.condition_file, "r", encoding="utf-8") as handle:
            condition = json.load(handle)
    else:
        condition = build_condition_group(args.chain, args.node, path, args.keyword, args.industry, args.exclude)

    config, config_path = load_config(args.config, allow_example=args.dry_run)
    high_screen = get_high_screen_section(config)
    page_size = min(max(args.page_size, 1), 50)

    if args.dry_run:
        request = build_enterprise_search_request(high_screen, condition, 1, page_size, pagination=True)
        print_json({
            "dry_run": True,
            "config_path": str(config_path),
            "chain": args.chain,
            "node": args.node,
            "path": path,
            "condition": condition,
            "enterprise_search_request": redact(request),
            "evidence_products": args.evidence_product or DEFAULT_EVIDENCE_PRODUCTS,
            "note": "dry-run 未调用网络；填入真实配置后去掉 --dry-run。",
        })
        return

    preview = call_enterprise_search_preview(high_screen, condition, 1, page_size)
    candidates = preview.get("samples", [])
    decisions = []
    evidence_results: Dict[str, Dict[str, Any]] = {}
    products = args.evidence_product or DEFAULT_EVIDENCE_PRODUCTS

    if args.with_evidence and candidates:
        handaas = get_handaas_section(config)
        keywords = [args.node, *args.keyword]
        for company in candidates:
            company_id = company.get("id") or company.get("name")
            key_type = "nameId" if company.get("id") else "name"
            per_company: Dict[str, Any] = {}
            for product in products:
                try:
                    per_company[product] = call_handaas(handaas, product, str(company_id), key_type, {"pageIndex": 1, "pageSize": 5})
                except Exception as exc:  # keep processing other products/candidates
                    per_company[product] = {"error": str(exc)}
            evidence_results[str(company.get("name"))] = per_company
            decisions.append(classify_candidate(company, per_company, args.node, keywords))
    else:
        decisions = [classify_candidate(company, {}, args.node, args.keyword) for company in candidates]

    print_json({
        "chain": args.chain,
        "node": args.node,
        "path": path,
        "condition": condition,
        "preview": preview,
        "decisions": decisions,
        "evidence": evidence_results,
        "next_actions": [
            "抽查 confirmed/uncertain 企业证据",
            "对跑偏样本补充排除词",
            "对高价值细分环节启用 --with-evidence 做二次证据核验",
        ],
    })


if __name__ == "__main__":
    main()
