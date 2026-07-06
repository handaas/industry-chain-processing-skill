#!/usr/bin/env python3
"""Call a configured Handaas/DAAS data product."""
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
        raise ApiError(message or f"Handaas 返回异常：{code}")
    return {
        "product": product,
        "product_id": request["product_id"],
        "params": request["params"],
        "code": code,
        "message": message,
        "data": payload.get("data"),
        "response": payload,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Call a Handaas data product with local config.")
    parser.add_argument("--config", help="Config JSON path.")
    parser.add_argument("--product", required=True, help="Product name configured under handaas.products, e.g. 工商照面")
    parser.add_argument("--keyword", required=True, help="Enterprise name, nameId, social credit code, etc.")
    parser.add_argument("--key-type", default="nameId", help="nameId, name, socialCreditCode, regNumber, 企业ID, 企业名称")
    parser.add_argument("--extra-json", default="{}", help="Extra request params JSON, e.g. '{\"pageIndex\":1,\"pageSize\":10}'")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--dry-run", action="store_true", help="Print redacted request without calling network.")
    args = parser.parse_args()

    config, path = load_config(args.config, allow_example=args.dry_run)
    section = get_handaas_section(config)
    extra = json.loads(args.extra_json or "{}")
    request = build_handaas_request(section, args.product, args.keyword, args.key_type, extra)
    if args.dry_run:
        print_json({"dry_run": True, "config_path": str(path), "request": redact(request)})
        return
    result = call_handaas(section, args.product, args.keyword, args.key_type, extra, timeout=args.timeout)
    print_json(result)


if __name__ == "__main__":
    main()
