#!/usr/bin/env python3
"""Preview candidate companies from MCP or the legacy local enterprise search interface."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, Iterable, List, Sequence

from common import (
    ApiError,
    get_high_screen_section,
    high_screen_signature,
    http_json_post,
    json_dumps,
    load_config,
    print_json,
    redact,
)
from mcp_client import call_tool, has_remote_mcp_config

REMOTE_SEARCH_TOOL = "advanced_filter_get_enterprise_list"
REMOTE_KEYWORD_SEARCH_TOOL = "enterprise_get_keyword_search"
KEYWORD_SKIP = {
    "营业",
    "个体户",
    "制造业",
    "服务业",
    "平台",
    "系统",
    "服务",
    "企业",
    "公司",
    "产业链",
    "培训",
    "咨询",
    "贸易",
    "商贸",
    "代理",
    "零售",
    "批发",
    "维修",
}


def load_filter(filter_file: str | None, filter_json: str | None) -> Any:
    if filter_file:
        with open(filter_file, "r", encoding="utf-8") as handle:
            return json.load(handle)
    if filter_json:
        return json.loads(filter_json)
    raw = sys.stdin.read().strip()
    if not raw:
        raise ValueError("请提供 --filter-file、--filter-json 或 stdin JSON")
    return json.loads(raw)


def normalize_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for row in rows:
        out.append({
            "id": row.get("nameId") or row.get("_id") or row.get("id") or row.get("eid"),
            "name": row.get("name") or row.get("enterpriseName") or row.get("entName") or row.get("companyName") or "未命名企业",
            "socialCreditCode": row.get("socialCreditCode"),
            "regCapital": row.get("regCapitalRmb") if row.get("regCapitalRmb") is not None else row.get("regCapital"),
        })
    return out


def _iter_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _iter_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_strings(item)


def extract_keywords_from_condition(condition: Any, fallback: Sequence[str] = (), limit: int = 8) -> List[str]:
    """Extract business keywords from the skill's local condition JSON for MCP primitive search tools."""
    groups = condition.get("must") if isinstance(condition, dict) else None
    source = groups if isinstance(groups, list) else condition
    values: List[str] = []
    for text in [*_iter_strings(source), *fallback]:
        text = str(text).strip()
        if not (2 <= len(text) <= 32):
            continue
        if text in KEYWORD_SKIP or text.startswith("!"):
            continue
        if text not in values:
            values.append(text)
        if len(values) >= limit:
            break
    return values or [text for text in fallback if text][:1]


def _extract_remote_rows(payload: Any) -> List[Dict[str, Any]]:
    """Best-effort row extraction across HandaaS list response shapes."""
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("resultList", "list", "records", "rows", "items", "dataList"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    data = payload.get("data")
    if data is not payload:
        rows = _extract_remote_rows(data)
        if rows:
            return rows
    result = payload.get("result")
    if result is not payload:
        rows = _extract_remote_rows(result)
        if rows:
            return rows
    return []


def _extract_remote_total(payload: Any, row_count: int) -> int:
    if isinstance(payload, dict):
        for key in ("total", "totalCount", "count"):
            value = payload.get(key)
            if value is not None:
                try:
                    return int(value)
                except (TypeError, ValueError):
                    pass
        for key in ("data", "result"):
            value = payload.get(key)
            if isinstance(value, dict):
                total = _extract_remote_total(value, row_count)
                if total != row_count:
                    return total
    return row_count


def call_remote_enterprise_search_preview(
    condition: Any,
    *,
    chain: str,
    node: str,
    page_index: int = 1,
    page_size: int = 20,
    config_path: str | None = None,
    timeout: int = 30,
    allow_keyword_fallback: bool = True,
) -> Dict[str, Any]:
    """Execute the complete condition through MCP, with legacy keyword fallback."""
    page_size = min(max(page_size, 1), 50)
    precise_error_text = ""
    try:
        payload = call_tool(
            REMOTE_SEARCH_TOOL,
            {"filter": condition},
            config_path=config_path,
            timeout=timeout,
        )
        if isinstance(payload, dict) and payload.get("error"):
            raise ApiError(str(payload.get("message") or payload.get("error")))
        rows = normalize_rows(_extract_remote_rows(payload))
        total = _extract_remote_total(payload, len(rows))
        return {
            "mode": "mcp_high_screen",
            "search_tools": [REMOTE_SEARCH_TOOL],
            "note": "完整高筛条件组由 HandaaS MCP 高筛产品执行。",
            "keywords": [],
            "total": total,
            "pageIndex": 1,
            "pageSize": page_size,
            "totalPages": 1,
            "samples": rows[:page_size],
            "calls": [{"tool": REMOTE_SEARCH_TOOL, "rows": len(rows)}],
            "errors": [],
            "precision_limited": False,
        }
    except Exception as precise_error:
        precise_error_text = str(precise_error)
        if not allow_keyword_fallback:
            raise ApiError(f"Remote MCP 完整高筛不可用：{precise_error}") from precise_error

    keywords = extract_keywords_from_condition(condition, [node, chain], limit=8)
    merged: Dict[str, Dict[str, Any]] = {}
    calls: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = [{"tool": REMOTE_SEARCH_TOOL, "error": precise_error_text}]
    total = 0

    for keyword in keywords:
        try:
            payload = call_tool(
                REMOTE_KEYWORD_SEARCH_TOOL,
                {"matchKeyword": keyword, "pageIndex": max(page_index, 1), "pageSize": page_size},
                config_path=config_path,
                timeout=timeout,
            )
            rows = _extract_remote_rows(payload)
            normalized = normalize_rows(rows)
            total += _extract_remote_total(payload, len(normalized))
            for row in normalized:
                key = str(row.get("id") or row.get("name") or "")
                if key and key not in merged:
                    merged[key] = row
            calls.append({"tool": REMOTE_KEYWORD_SEARCH_TOOL, "matchKeyword": keyword, "rows": len(normalized)})
            if len(merged) >= page_size:
                break
        except Exception as exc:
            errors.append({"matchKeyword": keyword, "error": str(exc)})

    return {
        "mode": "mcp",
        "search_tools": [REMOTE_KEYWORD_SEARCH_TOOL],
        "note": "当前 MCP 未提供完整高筛工具，已降级为企业关键词候选召回。",
        "keywords": keywords,
        "total": total or len(merged),
        "pageIndex": max(page_index, 1),
        "pageSize": page_size,
        "totalPages": max(((total or len(merged)) + page_size - 1) // page_size, 1),
        "samples": list(merged.values())[:page_size],
        "calls": calls,
        "errors": errors,
        "precision_limited": True,
    }


def build_enterprise_search_request(section: Dict[str, Any], condition: Any, page_index: int = 1, page_size: int = 20, *, pagination: bool = False) -> Dict[str, Any]:
    filter_string = json_dumps(condition)
    params: Dict[str, Any] = {"filter": filter_string}
    if pagination:
        params.update({"pageIndex": page_index, "pageSize": page_size})
    call_params: Dict[str, Any] = {
        "product_id": section["product_id"],
        "secret_id": section["secret_id"],
        "params": params,
    }
    call_params["signature"] = high_screen_signature(section["secret_key"], call_params)
    return {"url": section["url"], "params": params, "call_params": call_params}


def call_enterprise_search_preview(section: Dict[str, Any], condition: Any, page_index: int = 1, page_size: int = 20, timeout: int = 30) -> Dict[str, Any]:
    request = build_enterprise_search_request(section, condition, page_index, page_size, pagination=False)
    payload = http_json_post(request["url"], request["call_params"], timeout=timeout)
    code = str(payload.get("code", "")) if payload.get("code") is not None else ""
    message = str(payload.get("msgCN") or payload.get("msgCn") or payload.get("message") or "")
    if code and code != "10000":
        raise ApiError(message or f"企业搜索接口返回异常：{code}")
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    rows = data.get("resultList") or []
    total = int(data.get("total") or len(rows) or 0)
    return {
        "total": total,
        "pageIndex": page_index,
        "pageSize": page_size,
        "totalPages": max((total + page_size - 1) // page_size, 1),
        "samples": normalize_rows(rows),
        "code": code,
        "message": message,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview candidate companies from the local enterprise search interface.")
    parser.add_argument("--config", help="Config JSON path.")
    parser.add_argument("--chain", default="自定义产业链", help="Remote MCP mode metadata: industry chain name.")
    parser.add_argument("--node", default="自定义节点", help="Remote MCP mode metadata: refined node name.")
    parser.add_argument("--filter-file", help="Enterprise-search JSON file.")
    parser.add_argument("--filter-json", help="Enterprise-search JSON string.")
    parser.add_argument("--page-index", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=20)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--dry-run", action="store_true", help="Print redacted request without calling network.")
    parser.add_argument("--local", action="store_true", help="Force legacy local credential mode even if Remote MCP token is configured.")
    args = parser.parse_args()

    condition = load_filter(args.filter_file, args.filter_json)

    if not args.local and has_remote_mcp_config(args.config):
        if args.dry_run:
            print_json({
                "dry_run": True,
                "mode": "mcp",
                "search_tools": [REMOTE_SEARCH_TOOL],
                "filter": condition,
                "note": "去掉 --dry-run 后将调用 advanced_filter_get_enterprise_list 执行完整高筛条件组。",
            })
            return
        result = call_remote_enterprise_search_preview(
            condition,
            chain=args.chain,
            node=args.node,
            page_index=max(args.page_index, 1),
            page_size=args.page_size,
            config_path=args.config,
            timeout=args.timeout,
        )
        print_json(result)
        return

    config, path = load_config(args.config, allow_example=args.dry_run)
    section = get_high_screen_section(config)
    page_size = min(max(args.page_size or int(section.get("default_page_size", 20)), 1), 50)
    request = build_enterprise_search_request(section, condition, max(args.page_index, 1), page_size, pagination=False)
    if args.dry_run:
        print_json({"dry_run": True, "config_path": str(path), "request": redact(request)})
        return
    result = call_enterprise_search_preview(section, condition, max(args.page_index, 1), page_size, timeout=args.timeout)
    print_json(result)


if __name__ == "__main__":
    main()
