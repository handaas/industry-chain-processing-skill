#!/usr/bin/env python3
"""Call evidence data through MCP HandaaS wrappers or legacy local products."""
from __future__ import annotations

import argparse
import json
from typing import Any, Dict, Optional

from common import (
    ApiError,
    ConfigError,
    daas_signature,
    get_handaas_section,
    http_form_post,
    json_dumps,
    load_config,
    print_json,
    product_id_of,
    redact,
)
from mcp_client import call_tool, has_remote_mcp_config

KEY_TYPE_MAP = {
    "企业名称": "name",
    "企业ID": "nameId",
    "统一社会信用代码": "socialCreditCode",
    "注册号": "regNumber",
    "name": "name",
    "nameId": "nameId",
    "socialCreditCode": "socialCreditCode",
    "regNumber": "regNumber",
}

REMOTE_EVIDENCE_TOOL_MAP = {
    "工商照面": "enterprise_get_enterprise_base_info",
    "企业基础信息": "enterprise_get_enterprise_base_info",
    "企业简介": "enterprise_get_enterprise_profile",
    "企业业务": "enterprise_get_enterprise_business_info",
    "经营业务": "enterprise_get_enterprise_business_info",
    "企业标签": "enterprise_get_enterprise_tags",
    "股东信息": "enterprise_get_enterprise_holder_info",
    "对外投资": "enterprise_get_enterprise_invest_info",
    "分支机构": "enterprise_get_enterprise_branch_info",
    "主要人员": "enterprise_get_enterprise_main_person_info",
    "知识产权统计": "patent_bigdata_patent_stats",
    "专利统计": "patent_bigdata_patent_stats",
    "专利搜索": "patent_bigdata_patent_search",
    "企业招投标信息": "bid_bigdata_bidding_info",
    "招投标信息": "bid_bigdata_bidding_info",
    "中标统计": "bid_bigdata_bid_win_stats",
    "招标统计": "bid_bigdata_tender_stats",
    "采购统计": "bid_bigdata_procurement_stats",
    "招投标公告": "bid_bigdata_bid_search",
    "拟建项目": "bid_bigdata_planned_projects",
}

REMOTE_PAGED_TOOLS = {
    "enterprise_get_enterprise_invest_info",
    "enterprise_get_enterprise_branch_info",
    "enterprise_get_enterprise_main_person_info",
    "patent_bigdata_patent_search",
    "bid_bigdata_bidding_info",
    "bid_bigdata_bid_search",
    "bid_bigdata_planned_projects",
}

PATENT_SEARCH_KEY_TYPES = {
    "专利名称",
    "申请号/公开号",
    "申请人",
    "代理机构",
}

REMOTE_UNSUPPORTED_PRODUCTS = {
    "工商年报": "当前 industry-chain-mcp-server 未封装工商年报接口，请用 --local 走本地已开通商品，或改用 企业业务/企业标签。",
    "招聘统计": "当前 industry-chain-mcp-server 未封装招聘统计接口，请用 --local 走本地已开通商品。",
    "招聘明细": "当前 industry-chain-mcp-server 未封装招聘明细接口，请用 --local 走本地已开通商品。",
}


def build_handaas_request(section: Dict[str, Any], product: str, keyword: str, key_type: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    products = section.get("products") or {}
    if not isinstance(products, dict):
        raise ConfigError("handaas.products 必须是 object")
    product_id = product_id_of(products, product)
    params: Dict[str, Any] = {
        "matchKeyword": keyword,
        "keywordType": KEY_TYPE_MAP.get(key_type, key_type),
    }
    if extra:
        params.update(extra)
    call_params: Dict[str, Any] = {
        "product_id": product_id,
        "secret_id": section["secret_id"],
        "params": json_dumps(params),
    }
    call_params["signature"] = daas_signature(section["secret_key"], call_params)
    return {
        "url": f"{str(section.get('base_url', '')).rstrip('/')}/api/v1/integrator/call_api/{section['integrator_id']}",
        "params": params,
        "call_params": call_params,
        "product_id": product_id,
        "product_name": product,
    }


def call_handaas(section: Dict[str, Any], product: str, keyword: str, key_type: str = "nameId", extra: Optional[Dict[str, Any]] = None, timeout: int = 30) -> Dict[str, Any]:
    request = build_handaas_request(section, product, keyword, key_type, extra)
    payload = http_form_post(request["url"], request["call_params"], timeout=timeout)
    code = str(payload.get("code", "")) if payload.get("code") is not None else ""
    message = str(payload.get("msgCN") or payload.get("msgCn") or payload.get("message") or "")
    if code and code != "10000":
        raise ApiError(message or f"证据接口返回异常：{code}")
    return {
        "product": product,
        "product_id": request["product_id"],
        "params": request["params"],
        "code": code,
        "message": message,
        "data": payload.get("data"),
        "response": payload,
    }


def build_remote_evidence_arguments(tool: str, keyword: str, key_type: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    extra = extra or {}
    keyword_type = KEY_TYPE_MAP.get(key_type, key_type)
    args: Dict[str, Any] = {"matchKeyword": keyword}

    if tool not in {"bid_bigdata_bid_search", "patent_bigdata_patent_search"}:
        args["keywordType"] = keyword_type

    if tool in REMOTE_PAGED_TOOLS:
        args["pageIndex"] = int(extra.get("pageIndex") or 1)
        args["pageSize"] = min(max(int(extra.get("pageSize") or 10), 1), 50)

    if tool == "patent_bigdata_patent_search":
        for key in ("patentType",):
            if extra.get(key) is not None:
                args[key] = extra[key]
        if extra.get("keywordType"):
            args["keywordType"] = extra["keywordType"]
        elif key_type in PATENT_SEARCH_KEY_TYPES:
            args["keywordType"] = key_type

    if tool == "bid_bigdata_bid_search":
        for key in (
            "biddingType",
            "biddingRegion",
            "biddingAnncPubStartTime",
            "biddingAnncPubEndTime",
            "searchMode",
            "biddingProjectMaxAmount",
            "biddingPurchasingType",
            "biddingProjectMinAmount",
        ):
            if extra.get(key) is not None:
                args[key] = extra[key]

    return args


def call_remote_evidence(
    product: str,
    keyword: str,
    key_type: str = "nameId",
    extra: Optional[Dict[str, Any]] = None,
    *,
    config_path: Optional[str] = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    """Call one existing HandaaS MCP wrapper for evidence retrieval."""
    if product in REMOTE_UNSUPPORTED_PRODUCTS:
        raise ConfigError(REMOTE_UNSUPPORTED_PRODUCTS[product])
    tool = REMOTE_EVIDENCE_TOOL_MAP.get(product)
    if not tool:
        available = "、".join(sorted(REMOTE_EVIDENCE_TOOL_MAP))
        raise ConfigError(f"Remote MCP 不支持证据产品：{product}。可用产品：{available}")
    arguments = build_remote_evidence_arguments(tool, keyword, key_type, extra)
    payload = call_tool(tool, arguments, config_path=config_path, timeout=timeout)
    return {
        "mode": "mcp",
        "product": product,
        "tool": tool,
        "params": arguments,
        "data": payload,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Call a configured local enterprise evidence data product.")
    parser.add_argument("--config", help="Config JSON path.")
    parser.add_argument("--product", required=True, help="Evidence product name configured locally, e.g. 工商照面")
    parser.add_argument("--keyword", required=True, help="Enterprise name, nameId, social credit code, etc.")
    parser.add_argument("--key-type", default="nameId", help="nameId, name, socialCreditCode, regNumber, 企业ID, 企业名称")
    parser.add_argument("--extra-json", default="{}", help="Extra request params JSON, e.g. '{\"pageIndex\":1,\"pageSize\":10}'")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--dry-run", action="store_true", help="Print redacted request without calling network.")
    parser.add_argument("--local", action="store_true", help="Force legacy local credential mode even if Remote MCP token is configured.")
    args = parser.parse_args()

    extra = json.loads(args.extra_json or "{}")
    if not args.local and has_remote_mcp_config(args.config):
        if args.dry_run:
            product = args.product
            if product in REMOTE_UNSUPPORTED_PRODUCTS:
                raise ConfigError(REMOTE_UNSUPPORTED_PRODUCTS[product])
            tool = REMOTE_EVIDENCE_TOOL_MAP.get(product)
            if not tool:
                raise ConfigError(f"Remote MCP 不支持证据产品：{product}")
            print_json({
                "dry_run": True,
                "mode": "mcp",
                "product": product,
                "tool": tool,
                "arguments": build_remote_evidence_arguments(tool, args.keyword, args.key_type, extra),
                "note": "去掉 --dry-run 后将调用对应 HandaaS MCP 接口封装；不会调用自定义工作流工具。",
            })
            return
        result = call_remote_evidence(
            args.product,
            args.keyword,
            args.key_type,
            extra,
            config_path=args.config,
            timeout=args.timeout,
        )
        print_json(result)
        return

    config, path = load_config(args.config, allow_example=args.dry_run)
    section = get_handaas_section(config)
    request = build_handaas_request(section, args.product, args.keyword, args.key_type, extra)
    if args.dry_run:
        print_json({"dry_run": True, "config_path": str(path), "request": redact(request)})
        return
    result = call_handaas(section, args.product, args.keyword, args.key_type, extra, timeout=args.timeout)
    print_json(result)


if __name__ == "__main__":
    main()
