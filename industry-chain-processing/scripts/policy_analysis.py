#!/usr/bin/env python3
"""Compose a regional industry policy analysis payload.

This workflow combines HandaaS policy-bigdata MCP results with optional
web-collected policy context. It does not perform enterprise linking.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from common import json_dumps, print_json
from mcp_client import call_tool, has_remote_mcp_config


POLICY_DIMENSION_KEYWORDS = {
    "资金补贴/项目申报": ["补贴", "奖励", "资金", "资助", "扶持资金", "专项资金", "申报", "项目"],
    "场景示范/试点应用": ["试点", "示范", "应用场景", "先行区", "示范区", "车路云", "场景"],
    "技术研发/创新平台": ["研发", "创新", "技术", "实验室", "平台", "攻关", "标准", "测试"],
    "产业集群/招商落地": ["产业园", "集群", "基地", "招商", "落地", "园区", "链主"],
    "基础设施/公共服务": ["基础设施", "充电", "换电", "算力", "通信", "道路", "公共服务"],
    "监管规范/安全合规": ["监管", "管理办法", "安全", "标准", "规范", "准入", "许可"],
    "人才/金融/税费支持": ["人才", "金融", "贷款", "基金", "税", "贴息", "保险"],
}


def as_list(value: Any) -> List[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    return [value]


def compact_text(value: Any, limit: int = 180) -> str:
    text = " ".join(str(value or "").replace("\n", " ").split()).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip("，,；;。 ") + "…"


def unique(values: List[Any], limit: int = 12) -> List[str]:
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


def parse_regions(regions: List[str] | None, regions_csv: str | None) -> List[str]:
    values: List[str] = []
    for item in regions or []:
        values.extend([part.strip() for part in item.replace("，", ",").split(",") if part.strip()])
    if regions_csv:
        values.extend([part.strip() for part in regions_csv.replace("，", ",").split(",") if part.strip()])
    return unique(values) or ["国家部委"]


def load_web_context(path: Optional[str], notes: List[str] | None = None) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if path:
        raw = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            raw_items = raw.get("policy_context") or raw.get("web_policy_context") or raw.get("market_context") or raw.get("items") or raw.get("sources") or []
        elif isinstance(raw, list):
            raw_items = raw
        else:
            raw_items = []
        for item in raw_items:
            if isinstance(item, dict):
                items.append({
                    "region": str(item.get("region") or item.get("area") or "未指定"),
                    "topic": str(item.get("topic") or item.get("title") or "政策背景"),
                    "title": str(item.get("title") or item.get("topic") or ""),
                    "finding": str(item.get("finding") or item.get("summary") or item.get("content") or item.get("text") or ""),
                    "source": str(item.get("source") or item.get("publisher") or ""),
                    "url": str(item.get("url") or item.get("link") or item.get("source_url") or ""),
                    "date": str(item.get("date") or item.get("published_at") or item.get("policyPubDate") or ""),
                })
            else:
                items.append({"region": "未指定", "topic": "政策背景", "title": "", "finding": str(item), "source": "", "url": "", "date": ""})
    for note in notes or []:
        parts = [part.strip() for part in str(note).split("|")]
        items.append({
            "region": parts[0] if len(parts) > 0 and parts[0] else "未指定",
            "topic": parts[1] if len(parts) > 1 and parts[1] else "政策背景",
            "finding": parts[2] if len(parts) > 2 else str(note),
            "source": parts[3] if len(parts) > 3 else "",
            "url": parts[4] if len(parts) > 4 else "",
            "date": parts[5] if len(parts) > 5 else "",
            "title": parts[1] if len(parts) > 1 else "",
        })
    return [item for item in items if item.get("finding") or item.get("title")][:50]


def region_from_policy_region(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("province", "city", "district", "name", "regionName", "fullName"):
            if value.get(key):
                return str(value.get(key))
        return " ".join(str(item) for item in value.values() if item) or "未标注"
    if isinstance(value, list):
        flattened: List[str] = []
        for item in value:
            if isinstance(item, dict):
                flattened.append(region_from_policy_region(item))
            elif isinstance(item, list):
                flattened.extend(str(part) for part in item if part)
            elif item:
                flattened.append(str(item))
        return " / ".join(unique(flattened, limit=3)) or "未标注"
    return str(value or "未标注")


def extract_total(result: Any) -> int:
    if isinstance(result, dict):
        for key in ("total", "totalCount", "count"):
            if isinstance(result.get(key), int):
                return int(result[key])
            try:
                return int(result.get(key))
            except Exception:
                pass
    return 0


def extract_result_list(result: Any) -> List[Any]:
    if isinstance(result, dict):
        for key in ("resultList", "list", "items", "records", "data"):
            value = result.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                nested = extract_result_list(value)
                if nested:
                    return nested
    if isinstance(result, list):
        return result
    return []


def normalize_handaas_policy_items(result: Any, region_query: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item in extract_result_list(result):
        if not isinstance(item, dict):
            continue
        text = str(item.get("pnText") or item.get("content") or item.get("summary") or "")
        title = str(item.get("pnTitle") or item.get("title") or "")
        rows.append({
            "source_type": "handaas_policy",
            "region_query": region_query,
            "region": region_from_policy_region(item.get("pnRegion")) if item.get("pnRegion") else region_query,
            "policy_id": str(item.get("pnId") or item.get("id") or ""),
            "title": title,
            "agency": str(item.get("pnAgency") or item.get("agency") or ""),
            "policy_type": str(item.get("pnType") or item.get("type") or ""),
            "publish_date": str(item.get("pnPublishDate") or item.get("publishDate") or item.get("date") or ""),
            "url": str(item.get("pnOriginUrl") or item.get("url") or ""),
            "summary": compact_text(text or title, 220),
        })
    return rows


def normalize_web_policy_items(web_context: List[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item in web_context:
        finding = compact_text(item.get("finding"), 220)
        rows.append({
            "source_type": "web_policy",
            "region_query": str(item.get("region") or "未指定"),
            "region": str(item.get("region") or "未指定"),
            "policy_id": "",
            "title": str(item.get("title") or item.get("topic") or "政策背景"),
            "agency": str(item.get("source") or ""),
            "policy_type": str(item.get("topic") or "联网政策背景"),
            "publish_date": str(item.get("date") or ""),
            "url": str(item.get("url") or ""),
            "summary": finding,
        })
    return rows


def classify_dimensions(*texts: Any) -> List[str]:
    haystack = " ".join(str(text or "") for text in texts)
    hits: List[str] = []
    for dimension, keywords in POLICY_DIMENSION_KEYWORDS.items():
        if any(keyword in haystack for keyword in keywords):
            hits.append(dimension)
    return hits or ["综合政策支持"]


def summarize_region(region: str, items: List[Mapping[str, Any]]) -> Dict[str, Any]:
    handaas_items = [item for item in items if item.get("source_type") == "handaas_policy"]
    web_items = [item for item in items if item.get("source_type") == "web_policy"]
    type_counter = Counter(str(item.get("policy_type") or "未标注") for item in items)
    agency_counter = Counter(str(item.get("agency") or "未标注") for item in items)
    dim_counter: Counter[str] = Counter()
    for item in items:
        dim_counter.update(classify_dimensions(item.get("title"), item.get("summary"), item.get("policy_type")))
    samples = [
        {
            "title": item.get("title"),
            "agency": item.get("agency"),
            "policy_type": item.get("policy_type"),
            "publish_date": item.get("publish_date"),
            "summary": item.get("summary"),
            "url": item.get("url"),
            "source_type": item.get("source_type"),
        }
        for item in items[:6]
    ]
    top_dims = [name for name, _ in dim_counter.most_common(4)]
    if items:
        analysis = (
            f"{region}共纳入 {len(items)} 条政策线索，其中 HandaaS 政策库 {len(handaas_items)} 条、联网补充 {len(web_items)} 条；"
            f"政策重点集中在{'、'.join(top_dims) or '综合政策支持'}，主要发布/信息来源包括{'、'.join(name for name, _ in agency_counter.most_common(3))}。"
        )
    else:
        analysis = f"{region}暂未获得可分析的政策线索，建议扩大关键词、放宽发布时间或补充联网搜索。"
    return {
        "region": region,
        "policy_count": len(items),
        "handaas_policy_count": len(handaas_items),
        "web_policy_count": len(web_items),
        "policy_types": "、".join(name for name, _ in type_counter.most_common(5)),
        "key_agencies": "、".join(name for name, _ in agency_counter.most_common(5)),
        "policy_focus": "、".join(top_dims),
        "analysis": analysis,
        "sample_policies": samples,
    }


def region_matches(item_region: str, target_region: str) -> bool:
    if not item_region:
        return False
    if item_region == target_region:
        return True
    return target_region in item_region or item_region in target_region


def build_payload(
    *,
    chain: str,
    keyword: str,
    regions: List[str],
    pn_type: str,
    policy_start: Optional[str],
    policy_end: Optional[str],
    page_size: int,
    config_path: Optional[str],
    skip_mcp: bool,
    dry_run: bool,
    web_context: List[Dict[str, Any]],
) -> Dict[str, Any]:
    mcp_queries: List[Dict[str, Any]] = []
    handaas_items: List[Dict[str, Any]] = []
    mcp_errors: List[Dict[str, Any]] = []
    mcp_available = has_remote_mcp_config(config_path) if not skip_mcp else False

    for region in regions:
        arguments = {
            "matchKeyword": keyword,
            "pnType": pn_type,
            "address": region,
            "policyPubStartTime": policy_start,
            "policyPubEndTime": policy_end,
            "pageSize": page_size,
            "pageIndex": 1,
        }
        arguments = {key: value for key, value in arguments.items() if value not in (None, "")}
        mcp_queries.append({"tool": "policy_bigdata_policy_search", "arguments": arguments})
        if dry_run or not mcp_available:
            continue
        try:
            result = call_tool("policy_bigdata_policy_search", arguments, config_path=config_path, timeout=120)
            if isinstance(result, dict) and result.get("error"):
                mcp_errors.append({"region": region, "error": result.get("error"), "detail": result})
            handaas_items.extend(normalize_handaas_policy_items(result, region))
        except Exception as exc:  # pragma: no cover - environment dependent
            mcp_errors.append({"region": region, "error": str(exc)})

    web_items = normalize_web_policy_items(web_context)
    all_items = handaas_items + web_items
    grouped: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for region in regions:
        for item in all_items:
            item_region = str(item.get("region") or item.get("region_query") or "")
            if region_matches(item_region, region) or str(item.get("region_query") or "") == region:
                grouped[region].append(item)
    unmatched_web = [item for item in web_items if not any(region_matches(str(item.get("region") or ""), region) for region in regions)]
    if unmatched_web and "未指定" not in regions:
        grouped["未指定/联网补充"].extend(unmatched_web)

    regional_analysis = [summarize_region(region, list(grouped.get(region, []))) for region in list(regions) + (["未指定/联网补充"] if grouped.get("未指定/联网补充") else [])]
    dim_counter: Counter[str] = Counter()
    for item in all_items:
        dim_counter.update(classify_dimensions(item.get("title"), item.get("summary"), item.get("policy_type")))
    dimension_rows = [{"dimension": key, "count": count} for key, count in dim_counter.most_common()]
    summary = (
        f"本次围绕“{keyword}”对 {len(regions)} 个地区/层级开展政策分析，"
        f"共纳入 {len(all_items)} 条政策线索，其中 HandaaS 政策库 {len(handaas_items)} 条、联网补充 {len(web_items)} 条。"
        f"政策关注点主要集中在{'、'.join(row['dimension'] for row in dimension_rows[:5]) or '综合政策支持'}。"
    )
    if dry_run:
        summary = "本次为 dry-run，仅生成 MCP 政策查询计划，未真实调用 HandaaS 政策接口。" + summary
    elif not mcp_available and not skip_mcp:
        summary += " 当前未检测到可用 MCP 配置，结果仅包含联网补充或空查询计划。"
    return {
        "report_type": "policy_analysis",
        "title": f"{chain or keyword} 区域政策分析报告",
        "chain": chain or keyword,
        "keyword": keyword,
        "regions": regions,
        "summary": summary,
        "policy_query": {
            "keyword": keyword,
            "pn_type": pn_type,
            "policy_start": policy_start or "",
            "policy_end": policy_end or "",
            "page_size": page_size,
            "mcp_available": mcp_available,
            "dry_run": dry_run,
        },
        "regional_policy_analysis": regional_analysis,
        "policy_dimensions": dimension_rows,
        "policy_items": all_items,
        "web_policy_context": web_context,
        "mcp_queries": mcp_queries,
        "mcp_errors": mcp_errors,
        "data_quality": {
            "handaas_policy_count": len(handaas_items),
            "web_policy_count": len(web_items),
            "note": "政策分析可结合 HandaaS 政策大数据 MCP 与联网搜索；联网信息需保留来源链接和日期。",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze regional industry policies using HandaaS policy MCP plus web-collected context.")
    parser.add_argument("--chain", default="", help="Industry chain or sector name, e.g. 智能汽车")
    parser.add_argument("--keyword", help="Policy keyword. Defaults to --chain.")
    parser.add_argument("--region", action="append", default=[], help="Region to query. Repeatable. Examples: 国家部委, 广东省, 上海")
    parser.add_argument("--regions", help="Comma-separated regions.")
    parser.add_argument("--pn-type", default="全部", help="Policy type: 全部/申报指南/公示公开/其他政策")
    parser.add_argument("--policy-start", help="Policy publish start date yyyy-mm-dd")
    parser.add_argument("--policy-end", help="Policy publish end date yyyy-mm-dd")
    parser.add_argument("--page-size", type=int, default=10)
    parser.add_argument("--config", help="Optional MCP config path.")
    parser.add_argument("--skip-mcp", action="store_true", help="Do not call MCP; use web context only.")
    parser.add_argument("--dry-run", action="store_true", help="Only output MCP query plan.")
    parser.add_argument("--web-context", help="Optional JSON file with web-collected policy context.")
    parser.add_argument("--web-note", action="append", default=[], help="region|topic|finding|source|url|date. Repeatable.")
    parser.add_argument("--output", help="Output JSON path. Prints to stdout when omitted.")
    args = parser.parse_args()

    keyword = args.keyword or args.chain
    if not keyword:
        raise SystemExit("请提供 --keyword 或 --chain")
    payload = build_payload(
        chain=args.chain or keyword,
        keyword=keyword,
        regions=parse_regions(args.region, args.regions),
        pn_type=args.pn_type,
        policy_start=args.policy_start,
        policy_end=args.policy_end,
        page_size=min(args.page_size, 50),
        config_path=args.config,
        skip_mcp=args.skip_mcp,
        dry_run=args.dry_run,
        web_context=load_web_context(args.web_context, args.web_note),
    )
    if args.output:
        output = Path(args.output).expanduser()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json_dumps(payload, pretty=True), encoding="utf-8")
        print_json({"ok": True, "output": str(output)})
    else:
        print_json(payload)


if __name__ == "__main__":
    main()
