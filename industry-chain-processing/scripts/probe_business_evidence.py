#!/usr/bin/env python3
"""Probe which HandaaS evidence products best identify enterprise-node business fit."""
from __future__ import annotations

import argparse
import itertools
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from build_condition import build_keyword_profile, dedupe
from common import json_dumps, print_json
from enterprise_chain_positioning import (
    collect_remote_evidence_set,
    evidence_error,
    evidence_signals,
    resolve_remote_enterprise,
)
from link_enterprises import DEFAULT_EVIDENCE_PRODUCTS, classify_candidate, signal_hits


DEFAULT_CASES = Path(__file__).resolve().parents[1] / "assets" / "business-evidence-cases.example.json"


def load_cases(path: str | Path) -> List[Dict[str, Any]]:
    payload = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    rows = payload.get("cases") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("cases 文件必须是数组或包含 cases 数组")
    cases: List[Dict[str, Any]] = []
    for index, item in enumerate(rows):
        if not isinstance(item, dict):
            raise ValueError(f"cases[{index}] 必须是 object")
        expected = str(item.get("expected") or "")
        if expected not in {"positive", "negative"}:
            raise ValueError(f"cases[{index}].expected 必须是 positive 或 negative")
        enterprise = str(item.get("enterprise") or "").strip()
        node = str(item.get("node") or "").strip()
        path_values = [str(value) for value in item.get("path") or []]
        if not enterprise or not node or len(path_values) < 2:
            raise ValueError(f"cases[{index}] 缺少 enterprise/node/path")
        cases.append({**item, "enterprise": enterprise, "node": node, "path": path_values, "expected": expected})
    return cases


def combinations(products: Sequence[str], max_size: int = 0) -> List[List[str]]:
    limit = len(products) if max_size <= 0 else min(max_size, len(products))
    return [
        list(group)
        for size in range(1, limit + 1)
        for group in itertools.combinations(products, size)
    ]


def safe_ratio(numerator: int | float, denominator: int | float) -> float:
    return round(float(numerator) / float(denominator), 4) if denominator else 0.0


def confusion_metrics(rows: Sequence[Mapping[str, Any]], accepted_key: str) -> Dict[str, Any]:
    tp = sum(1 for item in rows if item["expected"] == "positive" and item[accepted_key])
    fn = sum(1 for item in rows if item["expected"] == "positive" and not item[accepted_key])
    fp = sum(1 for item in rows if item["expected"] == "negative" and item[accepted_key])
    tn = sum(1 for item in rows if item["expected"] == "negative" and not item[accepted_key])
    precision = safe_ratio(tp, tp + fp)
    recall = safe_ratio(tp, tp + fn)
    specificity = safe_ratio(tn, tn + fp)
    return {
        "tp": tp,
        "fn": fn,
        "fp": fp,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "balanced_accuracy": round((recall + specificity) / 2, 4),
    }


def profile_for_case(case: Mapping[str, Any]) -> Dict[str, List[str]]:
    path = [str(value) for value in case.get("path") or []]
    return build_keyword_profile(str(case.get("chain") or path[0]), str(case["node"]), path)


def source_case_summary(product: str, payload: Any, case: Mapping[str, Any]) -> Dict[str, Any]:
    profile = profile_for_case(case)
    exact_terms = dedupe([case["node"], *(profile.get("exact") or [])], 12)
    supporting_terms = dedupe(profile.get("supporting") or [], 16)
    signals = evidence_signals({product: payload})
    exact_hits: List[str] = []
    supporting_hits: List[str] = []
    for signal in signals:
        exact_hits.extend(signal_hits(signal.get("text"), exact_terms))
        supporting_hits.extend(signal_hits(signal.get("text"), supporting_terms))
    error = evidence_error(payload)
    return {
        "available": not bool(error),
        "error": error or None,
        "signal_count": len(signals),
        "exact_hits": dedupe(exact_hits, 12),
        "supporting_hits": dedupe(supporting_hits, 12),
        "has_exact": bool(exact_hits),
        "has_supporting": bool(supporting_hits),
    }


def evaluate_combination(
    products: Sequence[str],
    cases: Sequence[Mapping[str, Any]],
    identities: Mapping[str, Mapping[str, Any]],
    evidence_cache: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for case in cases:
        enterprise = str(case["enterprise"])
        identity = identities[enterprise]
        subset = {product: evidence_cache[enterprise].get(product) for product in products}
        profile = profile_for_case(case)
        company = {"id": identity.get("name_id"), "name": identity.get("name") or enterprise}
        decision = classify_candidate(company, subset, str(case["node"]), [], keyword_profile=profile)
        strict_accept = decision["decision"] == "confirmed"
        business_accept = decision.get("business_fit") == "matched"
        rows.append({
            "enterprise": enterprise,
            "node": case["node"],
            "expected": case["expected"],
            "decision": decision["decision"],
            "review_score": decision["review_score"],
            "evidence_source_count": decision["evidence_source_count"],
            "strong_source_count": decision["strong_source_count"],
            "business_fit": decision["business_fit"],
            "strict_accept": strict_accept,
            "business_accept": business_accept,
        })
    strict = confusion_metrics(rows, "strict_accept")
    business = confusion_metrics(rows, "business_accept")
    available_calls = sum(
        1
        for enterprise in identities
        for product in products
        if not evidence_error(evidence_cache[enterprise].get(product))
    )
    total_calls = len(identities) * len(products)
    availability = safe_ratio(available_calls, total_calls)
    manual_review_rate = safe_ratio(sum(1 for item in rows if item["decision"] == "uncertain"), len(rows))
    quality_score = round(
        business["balanced_accuracy"] * 0.45
        + business["precision"] * 0.2
        + business["recall"] * 0.2
        + strict["balanced_accuracy"] * 0.1
        + availability * 0.05
        - max(len(products) - 3, 0) * 0.01,
        4,
    )
    return {
        "products": list(products),
        "interface_count": len(products),
        "availability": availability,
        "business_judgment": business,
        "strict_link_confirmation": strict,
        "manual_review_rate": manual_review_rate,
        "quality_score": quality_score,
        "cases": rows,
    }


def dimension_metrics(
    products: Sequence[str],
    cases: Sequence[Mapping[str, Any]],
    evidence_cache: Mapping[str, Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    unique_enterprises = sorted({str(item["enterprise"]) for item in cases})
    rows: List[Dict[str, Any]] = []
    for product in products:
        summaries = [
            {
                "expected": case["expected"],
                **source_case_summary(product, evidence_cache[str(case["enterprise"])].get(product), case),
            }
            for case in cases
        ]
        positive = [item for item in summaries if item["expected"] == "positive"]
        negative = [item for item in summaries if item["expected"] == "negative"]
        positive_exact = sum(1 for item in positive if item["has_exact"])
        negative_exact = sum(1 for item in negative if item["has_exact"])
        available_enterprises = sum(
            1 for enterprise in unique_enterprises if not evidence_error(evidence_cache[enterprise].get(product))
        )
        rows.append({
            "product": product,
            "enterprise_availability": safe_ratio(available_enterprises, len(unique_enterprises)),
            "positive_exact_hit_rate": safe_ratio(positive_exact, len(positive)),
            "negative_exact_hit_rate": safe_ratio(negative_exact, len(negative)),
            "exact_hit_precision": safe_ratio(positive_exact, positive_exact + negative_exact),
            "positive_supporting_hit_rate": safe_ratio(sum(1 for item in positive if item["has_supporting"]), len(positive)),
            "errors": sorted({str(item["error"]) for item in summaries if item.get("error")}),
        })
    rows.sort(
        key=lambda item: (
            item["exact_hit_precision"],
            item["positive_exact_hit_rate"],
            item["enterprise_availability"],
        ),
        reverse=True,
    )
    return rows


def recommendations(dimensions: Sequence[Mapping[str, Any]], combinations_ranked: Sequence[Mapping[str, Any]]) -> List[str]:
    notes: List[str] = []
    if combinations_ranked:
        best = combinations_ranked[0]
        notes.append(
            f"业务判断优先组合：{' + '.join(best['products'])}；"
            f"平衡准确率 {best['business_judgment']['balanced_accuracy']:.2f}，"
            f"精确率 {best['business_judgment']['precision']:.2f}，召回率 {best['business_judgment']['recall']:.2f}。"
        )
        strict = sorted(
            combinations_ranked,
            key=lambda item: (
                item["strict_link_confirmation"]["balanced_accuracy"],
                item["strict_link_confirmation"]["precision"],
                -item["interface_count"],
            ),
            reverse=True,
        )[0]
        notes.append(
            f"最终挂链确认优先组合：{' + '.join(strict['products'])}；"
            "业务判断与最终挂链分层，后者继续要求强证据和独立来源。"
        )
    unavailable = [str(item["product"]) for item in dimensions if float(item["enterprise_availability"]) < 0.5]
    if unavailable:
        notes.append(f"低可用接口不得作为硬门槛：{'、'.join(unavailable)}。")
    noisy = [str(item["product"]) for item in dimensions if float(item["negative_exact_hit_rate"]) >= 0.5]
    if noisy:
        notes.append(f"高误命中维度只作辅助证据，不单独确认：{'、'.join(noisy)}。")
    return notes


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe HandaaS evidence dimensions against known enterprise-node cases.")
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    parser.add_argument("--config", help="Config containing Remote MCP URL/token")
    parser.add_argument("--product", action="append", default=[])
    parser.add_argument("--max-combination-size", type=int, default=4, help="0 evaluates every non-empty product subset")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    cases = load_cases(args.cases)
    products = args.product or list(DEFAULT_EVIDENCE_PRODUCTS)
    enterprises = sorted({str(item["enterprise"]) for item in cases})
    identities: Dict[str, Dict[str, Any]] = {}
    evidence_cache: Dict[str, Dict[str, Any]] = {}
    resolution_candidates: Dict[str, Any] = {}
    for enterprise in enterprises:
        resolved = resolve_remote_enterprise(enterprise, args.config, args.timeout)
        identity = resolved["identity"]
        identities[enterprise] = identity
        resolution_candidates[enterprise] = resolved.get("candidates") or []
        evidence_cache[enterprise] = collect_remote_evidence_set(identity, products, args.config, args.timeout)

    dimensions = dimension_metrics(products, cases, evidence_cache)
    evaluated = [
        evaluate_combination(group, cases, identities, evidence_cache)
        for group in combinations(products, args.max_combination_size)
    ]
    evaluated.sort(
        key=lambda item: (
            item["quality_score"],
            item["business_judgment"]["balanced_accuracy"],
            item["business_judgment"]["precision"],
            -item["interface_count"],
        ),
        reverse=True,
    )
    errors_by_product: Dict[str, Counter[str]] = defaultdict(Counter)
    for enterprise in enterprises:
        for product in products:
            error = evidence_error(evidence_cache[enterprise].get(product))
            if error:
                errors_by_product[product][error] += 1
    payload = {
        "cases_file": str(Path(args.cases).expanduser().resolve()),
        "case_count": len(cases),
        "enterprise_count": len(enterprises),
        "positive_cases": sum(1 for item in cases if item["expected"] == "positive"),
        "negative_cases": sum(1 for item in cases if item["expected"] == "negative"),
        "products": products,
        "dimension_metrics": dimensions,
        "combination_count": len(evaluated),
        "combination_ranking": evaluated,
        "top_combinations": evaluated[:10],
        "recommendations": recommendations(dimensions, evaluated),
        "resolution": {enterprise: identities[enterprise] for enterprise in enterprises},
        "resolution_candidates": resolution_candidates,
        "errors_by_product": {
            product: [{"error": error, "enterprise_count": count} for error, count in counts.items()]
            for product, counts in errors_by_product.items()
        },
    }
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json_dumps(payload, pretty=True), encoding="utf-8")
    print_json({
        "ok": True,
        "output": str(output),
        "case_count": len(cases),
        "enterprise_count": len(enterprises),
        "top_combinations": [
            {
                "products": item["products"],
                "quality_score": item["quality_score"],
                "business_judgment": item["business_judgment"],
                "strict_link_confirmation": item["strict_link_confirmation"],
            }
            for item in evaluated[:5]
        ],
        "recommendations": payload["recommendations"],
    })


if __name__ == "__main__":
    main()
