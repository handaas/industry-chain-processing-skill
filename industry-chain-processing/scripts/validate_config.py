#!/usr/bin/env python3
"""Validate local enterprise data config without printing secrets."""
from __future__ import annotations

import argparse
from typing import Any, Dict, List

from common import (
    ConfigError,
    get_handaas_section,
    get_high_screen_section,
    get_mcp_section,
    is_placeholder,
    load_config,
    mcp_config_from_env,
    print_json,
    redact,
)


def check_required(section_name: str, section: Dict[str, Any], fields: List[str], allow_placeholders: bool, errors: List[str], warnings: List[str]) -> None:
    for field in fields:
        value = section.get(field)
        if value in (None, ""):
            errors.append(f"{section_name}.{field} 缺失")
        elif is_placeholder(value):
            target = warnings if allow_placeholders else errors
            target.append(f"{section_name}.{field} 仍是占位值")


def validate(config: Dict[str, Any], *, allow_placeholders: bool = False) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []
    modes: Dict[str, Any] = {
        "remote_mcp": {"ok": False, "source": None},
        "local_credentials": {"ok": False},
    }

    # Remote MCP mode: token/URL is enough. This is the preferred path after
    # the platform creates the MCP service and returns a token.
    remote_errors: List[str] = []
    remote_warnings: List[str] = []
    env_mcp = mcp_config_from_env()
    if env_mcp:
        if is_placeholder(env_mcp.get("url")):
            (remote_warnings if allow_placeholders else remote_errors).append("环境变量 Remote MCP URL/token 仍是占位值")
        modes["remote_mcp"] = {"ok": not remote_errors, "source": "environment", "config": redact(env_mcp)}
    else:
        try:
            mcp_section = get_mcp_section(config)
            if is_placeholder(mcp_section.get("url")):
                (remote_warnings if allow_placeholders else remote_errors).append("mcp.url/mcp.token 仍是占位值")
            modes["remote_mcp"] = {"ok": not remote_errors, "source": "config", "config": redact(mcp_section)}
        except ConfigError as exc:
            remote_errors.append(str(exc))
    warnings.extend(remote_warnings)

    local_errors: List[str] = []
    local_warnings: List[str] = []
    try:
        handaas = get_handaas_section(config)
        check_required("handaas", handaas, ["base_url", "integrator_id", "secret_id", "secret_key"], allow_placeholders, local_errors, local_warnings)
        products = handaas.get("products")
        if not isinstance(products, dict) or not products:
            local_errors.append("handaas.products 缺失或为空")
        else:
            for name, item in products.items():
                product_id = item if isinstance(item, str) else item.get("product_id") if isinstance(item, dict) else ""
                if not product_id:
                    local_errors.append(f"handaas.products.{name} 缺少 product_id")
                elif is_placeholder(product_id):
                    (local_warnings if allow_placeholders else local_errors).append(f"handaas.products.{name} 仍是占位值")
    except ConfigError as exc:
        local_errors.append(str(exc))

    try:
        high_screen = get_high_screen_section(config)
        check_required(
            "handaas.products.高筛企业清单",
            high_screen,
            ["url", "product_id", "secret_id", "secret_key"],
            allow_placeholders,
            local_errors,
            local_warnings,
        )
        page_size = high_screen.get("default_page_size", 20)
        if not isinstance(page_size, int) or not (1 <= page_size <= 50):
            local_warnings.append("handaas.products.高筛企业清单.default_page_size 建议为 1-50 的整数")
        if high_screen.get("source") == "legacy_high_screen":
            local_warnings.append("顶层 high_screen 配置已兼容但不再推荐；请迁移到 handaas.products.高筛企业清单并复用同一组凭证")
    except ConfigError as exc:
        local_errors.append(str(exc))

    modes["local_credentials"] = {
        "ok": not local_errors,
        "errors": local_errors,
        "warnings": local_warnings,
    }
    warnings.extend(local_warnings)

    if not modes["remote_mcp"]["ok"] and not modes["local_credentials"]["ok"]:
        errors.extend(remote_errors)
        errors.extend(local_errors)
    elif modes["remote_mcp"]["ok"] and local_errors:
        warnings.append("Remote MCP 已可用；本地 handaas 凭证或产品配置未完整，但不影响 token 模式。")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "modes": modes,
        "config_redacted": redact(config),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate industry-chain-processing config.")
    parser.add_argument("--config", help="Config JSON path.")
    parser.add_argument("--allow-placeholders", action="store_true", help="Allow example placeholder values.")
    args = parser.parse_args()

    try:
        config, path = load_config(args.config, allow_example=args.allow_placeholders)
    except ConfigError as exc:
        env_mcp = mcp_config_from_env()
        if not env_mcp:
            print_json({"ok": False, "errors": [str(exc)], "warnings": []})
            raise SystemExit(1)
        config, path = {"mcp": env_mcp}, "<environment>"

    result = validate(config, allow_placeholders=args.allow_placeholders)
    result["config_path"] = str(path)
    print_json(result)
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
