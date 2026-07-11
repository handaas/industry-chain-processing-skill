#!/usr/bin/env python3
"""Evaluate and compare HandaaS high-screen condition routes for one L5 node."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from build_condition import build_search_plan, parse_path
from common import ConfigError, get_handaas_section, get_high_screen_section, json_dumps, load_config, print_json
from enterprise_search_preview import call_enterprise_search_preview
from link_enterprises import (
    DEFAULT_EVIDENCE_PRODUCTS,
    classify_candidate,
    collect_candidate_evidence,
    merge_candidate,
    normalize_match_text,
    project_seed_names,
    seed_aliases,
)
from mcp_client import has_remote_mcp_config
from project_context import build_project_context, name_score


METHODOLOGY_REFERENCES = [
    "https://www.elastic.co/guide/en/elasticsearch/reference/8.19/query-dsl-bool-query.html",
    "https://www.elastic.co/guide/en/elasticsearch/reference/8.19/query-dsl-multi-match-query.html",
    "https://www.elastic.co/guide/en/elasticsearch/reference/8.19/search-rank-eval.html",
    "https://www.elastic.co/guide/en/elasticsearch/reference/8.19/search-with-synonyms.html",
    "https://github.com/o19s/quepid",
    "https://github.com/opensearch-project/search-relevance",
]


def load_labels(path: str | None) -> Dict[str, Any]:
    if not path:
        return {"positive_enterprises": [], "negative_enterprises": [], "ratings": {}}
    payload = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("标签文件顶层必须是 JSON object")
    ratings = payload.get("ratings") if isinstance(payload.get("ratings"), dict) else {}
    return {
        "positive_enterprises": [str(item) for item in payload.get("positive_enterprises") or [] if str(item).strip()],
        "negative_enterprises": [str(item) for item in payload.get("negative_enterprises") or [] if str(item).strip()],
        "ratings": {str(key): int(value) for key, value in ratings.items()},
    }


def best_name_match(name: str, candidates: Iterable[str]) -> tuple[str | None, int]:
    best_name: str | None = None
    best_score = 0
    for candidate in candidates:
        score = name_score(candidate, name)
        if score > best_score:
            best_name, best_score = candidate, score
    return best_name, best_score


def rating_for_enterprise(name: str, labels: Mapping[str, Any]) -> int | None:
    ratings = labels.get("ratings") if isinstance(labels.get("ratings"), Mapping) else {}
    matched, score = best_name_match(name, [str(item) for item in ratings])
    if matched and score >= 85:
        return int(ratings[matched])
    matched, score = best_name_match(name, labels.get("positive_enterprises") or [])
    if matched and score >= 85:
        return 3
    matched, score = best_name_match(name, labels.get("negative_enterprises") or [])
    if matched and score >= 85:
        return 0
    return None


def precision_at_k(names: Sequence[str], labels: Mapping[str, Any], k: int) -> Dict[str, Any]:
    selected = list(names[: max(k, 1)])
    rated = [(name, rating_for_enterprise(name, labels)) for name in selected]
    judged = [(name, rating) for name, rating in rated if rating is not None]
    relevant = sum(1 for _, rating in judged if int(rating) >= 1)
    return {
        "k": max(k, 1),
        "returned": len(selected),
        "judged": len(judged),
        "judgment_coverage": round(len(judged) / max(len(selected), 1), 4),
        "relevant": relevant,
        "precision": round(relevant / max(len(selected), 1), 4),
        "judged_precision": round(relevant / len(judged), 4) if judged else None,
    }


def mean_reciprocal_rank(names: Sequence[str], labels: Mapping[str, Any]) -> float | None:
    has_judgment = False
    for index, name in enumerate(names, start=1):
        rating = rating_for_enterprise(name, labels)
        if rating is None:
            continue
        has_judgment = True
        if rating >= 1:
            return round(1 / index, 4)
    return 0.0 if has_judgment else None


def discounted_cumulative_gain(names: Sequence[str], labels: Mapping[str, Any], k: int) -> float | None:
    ratings = [rating_for_enterprise(name, labels) for name in names[: max(k, 1)]]
    if not any(rating is not None for rating in ratings):
        return None
    value = 0.0
    for index, rating in enumerate(ratings, start=1):
        relevance = max(int(rating or 0), 0)
        value += (2**relevance - 1) / math.log2(index + 1)
    return round(value, 4)


def anchor_hits(names: Sequence[str], anchors: Sequence[str]) -> List[Dict[str, Any]]:
    hits: List[Dict[str, Any]] = []
    for anchor in anchors:
        aliases = seed_aliases(anchor) or [anchor]
        best: tuple[str | None, int] = (None, 0)
        for name in names:
            _, score = best_name_match(name, aliases)
            if score > best[1]:
                best = (name, score)
        if best[0] and best[1] >= 70:
            hits.append({"anchor": anchor, "enterprise": best[0], "score": best[1]})
    return hits


def overlap_metrics(route_names: Mapping[str, Sequence[str]]) -> List[Dict[str, Any]]:
    route_ids = list(route_names)
    rows: List[Dict[str, Any]] = []
    for index, left in enumerate(route_ids):
        left_set = {normalize_match_text(item) for item in route_names[left] if item}
        for right in route_ids[index + 1 :]:
            right_set = {normalize_match_text(item) for item in route_names[right] if item}
            union = left_set | right_set
            intersection = left_set & right_set
            rows.append({
                "left": left,
                "right": right,
                "intersection": len(intersection),
                "jaccard": round(len(intersection) / len(union), 4) if union else 0.0,
            })
    return rows


def unique_contribution(route_names: Mapping[str, Sequence[str]]) -> Dict[str, List[str]]:
    normalized = {
        route_id: {normalize_match_text(name): name for name in names if name}
        for route_id, names in route_names.items()
    }
    result: Dict[str, List[str]] = {}
    for route_id, names in normalized.items():
        other_names: set[str] = set()
        for other_id, other in normalized.items():
            if other_id != route_id:
                other_names.update(other)
        result[route_id] = [display for key, display in names.items() if key not in other_names]
    return result


def evidence_metrics(names: Sequence[str], decisions: Mapping[str, Dict[str, Any]]) -> Dict[str, Any]:
    reviewed = [decisions[normalize_match_text(name)] for name in names if normalize_match_text(name) in decisions]
    confirmed = sum(1 for item in reviewed if item.get("decision") == "confirmed")
    uncertain = sum(1 for item in reviewed if item.get("decision") == "uncertain")
    rejected = sum(1 for item in reviewed if item.get("decision") == "rejected")
    business_matched = sum(1 for item in reviewed if item.get("business_fit") == "matched")
    business_partial = sum(1 for item in reviewed if item.get("business_fit") == "partial")
    return {
        "reviewed": len(reviewed),
        "business_matched": business_matched,
        "business_partial": business_partial,
        "business_match_rate": round(business_matched / len(reviewed), 4) if reviewed else None,
        "business_coverage_rate": round((business_matched + business_partial) / len(reviewed), 4) if reviewed else None,
        "confirmed": confirmed,
        "uncertain": uncertain,
        "rejected": rejected,
        "precision": round(confirmed / len(reviewed), 4) if reviewed else None,
        "accepted_rate": round((confirmed + uncertain) / len(reviewed), 4) if reviewed else None,
        "noise_rate": round(rejected / len(reviewed), 4) if reviewed else None,
        "strong_source_coverage": round(
            sum(1 for item in reviewed if int(item.get("strong_source_count") or 0) > 0) / len(reviewed),
            4,
        ) if reviewed else None,
    }


def stratified_candidates(
    route_names: Mapping[str, Sequence[str]],
    merged: Mapping[str, Dict[str, Any]],
    limit: int,
) -> List[Dict[str, Any]]:
    by_name = {
        normalize_match_text(item.get("name")): item
        for item in merged.values()
        if item.get("name")
    }
    selected: List[Dict[str, Any]] = []
    selected_keys: set[str] = set()
    positions = {route_id: 0 for route_id in route_names}
    while len(selected) < max(limit, 1):
        added = False
        for route_id, names in route_names.items():
            while positions[route_id] < len(names):
                name = names[positions[route_id]]
                positions[route_id] += 1
                key = normalize_match_text(name)
                if key in selected_keys or key not in by_name:
                    continue
                selected.append(by_name[key])
                selected_keys.add(key)
                added = True
                break
            if len(selected) >= max(limit, 1):
                break
        if not added:
            break
    if len(selected) < max(limit, 1):
        remaining = sorted(
            (item for key, item in by_name.items() if key not in selected_keys),
            key=lambda item: (int(item.get("recall_score") or 0), len(item.get("recall_routes") or [])),
            reverse=True,
        )
        selected.extend(remaining[: max(limit, 1) - len(selected)])
    return selected


def recommendations(route_rows: Sequence[Dict[str, Any]], overlap: Sequence[Dict[str, Any]], anchor_count: int) -> List[str]:
    items: List[str] = []
    for row in route_rows:
        route_id = row["route_id"]
        total = int(row.get("total") or 0)
        metrics = row.get("evidence_metrics") or {}
        if total == 0:
            items.append(f"{route_id}: 零召回，检查节点规格拆分、同义词和字段数据覆盖，不要先放宽强证据组。")
        elif total > 5000:
            items.append(f"{route_id}: 候选总量 {total} 偏宽，优先收紧精确产品词、行业边界或经营范围排除词。")
        if metrics.get("precision") is not None and float(metrics["precision"]) < 0.5:
            if float(metrics.get("noise_rate") or 0) >= 0.2:
                items.append(f"{route_id}: 证据噪声率达到 20% 以上，应收紧业务关键词/经营范围并补充排除词。")
            elif float(metrics.get("strong_source_coverage") or 0) < 0.5:
                items.append(f"{route_id}: 噪声可控但强证据覆盖低于 50%，优先检查企业业务、专利和招投标商品可用性及分页覆盖。")
        label_metrics = row.get("precision_at_10") or {}
        if float(label_metrics.get("judgment_coverage") or 0) < 0.3:
            items.append(f"{route_id}: 前 10 条人工标签覆盖不足 30%，先补充判断集再接受相关性结论。")
        if int(row.get("unique_sample_count") or 0) == 0:
            items.append(f"{route_id}: 当前采样没有独有企业，检查该路由是否可合并或降低采样优先级。")
    if anchor_count and not any(int(row.get("anchor_hit_count") or 0) for row in route_rows):
        items.append("所有 ES 路由均未命中项目代表企业，检查行业误分和字段缺失，并保留 project_seed 补召回。")
    for row in overlap:
        if float(row.get("jaccard") or 0) >= 0.9:
            items.append(f"{row['left']} 与 {row['right']} 样本重叠超过 90%，可在下一轮减少冗余路由或降低其中一条采样量。")
    return list(dict.fromkeys(items))


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate HandaaS ES condition routes with labels, anchors, and evidence review.")
    parser.add_argument("--config", help="Config JSON containing high_screen and optional local HandaaS products")
    parser.add_argument("--chain", required=True)
    parser.add_argument("--node", required=True)
    parser.add_argument("--path")
    parser.add_argument("--keyword", action="append", default=[])
    parser.add_argument("--industry", action="append", default=[])
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--precision", choices=["strict", "balanced"], default="strict")
    parser.add_argument("--project-root")
    parser.add_argument("--project-chain")
    parser.add_argument("--project-node")
    parser.add_argument("--labels", help="JSON with positive_enterprises, negative_enterprises, or ratings")
    parser.add_argument("--page-size", type=int, default=20)
    parser.add_argument("--pages", type=int, default=1)
    parser.add_argument("--with-evidence", action="store_true")
    parser.add_argument("--evidence-product", action="append", default=[])
    parser.add_argument("--max-evidence-candidates", type=int, default=20)
    parser.add_argument("--baseline", help="Previous tuner JSON for route-level comparison")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    config, _ = load_config(args.config)
    high_screen = get_high_screen_section(config)
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
    labels = load_labels(args.labels)
    anchors = project_seed_names(
        project,
        plan["node_context"]["node"],
        plan["node_context"]["canonical_path"],
        30,
    )
    route_names: Dict[str, List[str]] = {}
    route_results: List[Dict[str, Any]] = []
    merged: Dict[str, Dict[str, Any]] = {}
    page_size = min(max(args.page_size, 1), 50)
    pages = min(max(args.pages, 1), 10)
    for route in plan["recall_routes"]:
        route_id = str(route["id"])
        rows: Dict[str, Dict[str, Any]] = {}
        total = 0
        for page_index in range(1, pages + 1):
            preview = call_enterprise_search_preview(
                high_screen,
                route["condition"],
                page_index,
                page_size,
                timeout=120,
            )
            total = max(total, int(preview.get("total") or 0))
            for company in preview.get("samples") or []:
                if not isinstance(company, dict):
                    continue
                key = str(company.get("id") or normalize_match_text(company.get("name")))
                if key:
                    rows.setdefault(key, company)
                    merge_candidate(merged, company, route_id)
            if page_index >= int(preview.get("totalPages") or 1):
                break
        names = [str(item.get("name") or "") for item in rows.values() if item.get("name")]
        route_names[route_id] = names
        hits = anchor_hits(names, anchors)
        route_results.append({
            "route_id": route_id,
            "purpose": route.get("purpose"),
            "priority": route.get("priority"),
            "business_fields": route.get("business_fields") or [],
            "total": total,
            "sample_count": len(names),
            "anchor_hit_count": len(hits),
            "anchor_hits": hits,
            "precision_at_10": precision_at_k(names, labels, 10),
            "mrr": mean_reciprocal_rank(names, labels),
            "dcg_at_10": discounted_cumulative_gain(names, labels, 10),
            "sample_enterprises": names,
            "condition": route["condition"],
        })

    decisions_by_name: Dict[str, Dict[str, Any]] = {}
    selected = stratified_candidates(route_names, merged, max(args.max_evidence_candidates, 1))
    evidence_remote = has_remote_mcp_config(args.config)
    handaas: Dict[str, Any] | None = None
    if args.with_evidence and not evidence_remote:
        try:
            handaas = get_handaas_section(config)
        except ConfigError:
            handaas = None
    products = args.evidence_product or DEFAULT_EVIDENCE_PRODUCTS
    if args.with_evidence:
        for company in selected:
            evidence = collect_candidate_evidence(
                company,
                products,
                remote=evidence_remote,
                config_path=args.config,
                handaas=handaas,
                timeout=120,
            )
            decision = classify_candidate(
                company,
                evidence,
                plan["node_context"]["node"],
                args.keyword,
                keyword_profile=plan["keyword_profile"],
            )
            decisions_by_name[normalize_match_text(company.get("name"))] = decision
    unique = unique_contribution(route_names)
    for row in route_results:
        unique_names = unique.get(row["route_id"]) or []
        row["unique_sample_count"] = len(unique_names)
        row["unique_sample_enterprises"] = unique_names
        row["evidence_metrics"] = evidence_metrics(route_names[row["route_id"]], decisions_by_name)

    overlaps = overlap_metrics(route_names)
    baseline_comparison: List[Dict[str, Any]] = []
    if args.baseline:
        previous = json.loads(Path(args.baseline).expanduser().read_text(encoding="utf-8"))
        previous_routes = {
            str(item.get("route_id")): item
            for item in previous.get("routes") or []
            if isinstance(item, dict) and item.get("route_id")
        }
        for row in route_results:
            before = previous_routes.get(row["route_id"])
            if not before:
                continue
            baseline_comparison.append({
                "route_id": row["route_id"],
                "total_delta": int(row.get("total") or 0) - int(before.get("total") or 0),
                "evidence_precision_before": (before.get("evidence_metrics") or {}).get("precision"),
                "evidence_precision_after": (row.get("evidence_metrics") or {}).get("precision"),
                "precision_at_10_before": (before.get("precision_at_10") or {}).get("precision"),
                "precision_at_10_after": (row.get("precision_at_10") or {}).get("precision"),
                "mrr_before": before.get("mrr"),
                "mrr_after": row.get("mrr"),
                "dcg_at_10_before": before.get("dcg_at_10"),
                "dcg_at_10_after": row.get("dcg_at_10"),
                "anchor_hit_delta": int(row.get("anchor_hit_count") or 0) - int(before.get("anchor_hit_count") or 0),
            })

    payload = {
        "methodology": {
            "model": "named route matrix + labeled judgments + evidence review",
            "minimum_should_match_emulation": "工商基础、业务字段和强证据分别作为 must 组，每组内部 should 至少命中一项",
            "references": METHODOLOGY_REFERENCES,
        },
        "chain": plan["node_context"]["chain"],
        "node": plan["node_context"]["node"],
        "path": plan["node_context"]["canonical_path"],
        "precision": args.precision,
        "keyword_profile": plan["keyword_profile"],
        "industry_paths": plan["node_context"]["industry_paths"],
        "labels": labels,
        "project_anchors": anchors,
        "routes": route_results,
        "overlap": overlaps,
        "evidence_sampling": "stratified_round_robin_by_route",
        "evidence_decisions": list(decisions_by_name.values()),
        "baseline_comparison": baseline_comparison,
        "recommendations": recommendations(route_results, overlaps, len(anchors)),
    }
    output = Path(args.output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json_dumps(payload, pretty=True), encoding="utf-8")
    print_json({
        "ok": True,
        "output": str(output),
        "route_count": len(route_results),
        "reviewed_enterprises": len(decisions_by_name),
        "recommendations": payload["recommendations"],
    })


if __name__ == "__main__":
    main()
