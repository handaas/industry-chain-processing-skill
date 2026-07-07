#!/usr/bin/env python3
"""Preview candidate companies from the configured local enterprise search interface."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List

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
            "name": row.get("name") or "未命名企业",
            "socialCreditCode": row.get("socialCreditCode"),
            "regCapital": row.get("regCapitalRmb") if row.get("regCapitalRmb") is not None else row.get("regCapital"),
        })
    return out


def build_enterprise_search_request(section: Dict[str, Any], condition: Any, page_index: int = 1, page_size: int = 20, *, pagination: bool = True) -> Dict[str, Any]:
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
    request = build_enterprise_search_request(section, condition, page_index, page_size, pagination=True)
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
    parser.add_argument("--filter-file", help="Enterprise-search JSON file.")
    parser.add_argument("--filter-json", help="Enterprise-search JSON string.")
    parser.add_argument("--page-index", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=20)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--dry-run", action="store_true", help="Print redacted request without calling network.")
    args = parser.parse_args()

    condition = load_filter(args.filter_file, args.filter_json)
    config, path = load_config(args.config, allow_example=args.dry_run)
    section = get_high_screen_section(config)
    page_size = min(max(args.page_size or int(section.get("default_page_size", 20)), 1), 50)
    request = build_enterprise_search_request(section, condition, max(args.page_index, 1), page_size, pagination=True)
    if args.dry_run:
        print_json({"dry_run": True, "config_path": str(path), "request": redact(request)})
        return
    result = call_enterprise_search_preview(section, condition, max(args.page_index, 1), page_size, timeout=args.timeout)
    print_json(result)


if __name__ == "__main__":
    main()
