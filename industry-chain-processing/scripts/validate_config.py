#!/usr/bin/env python3
"""Validate local enterprise data config without printing secrets."""
from __future__ import annotations

import argparse
from typing import Any, Dict, List

from common import ConfigError, get_handaas_section, get_high_screen_section, is_placeholder, load_config, print_json, redact


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

    try:
        handaas = get_handaas_section(config)
        check_required("handaas", handaas, ["base_url", "integrator_id", "secret_id", "secret_key"], allow_placeholders, errors, warnings)
        products = handaas.get("products")
        if not isinstance(products, dict) or not products:
            errors.append("handaas.products 缺失或为空")
        else:
            for name, item in products.items():
                product_id = item if isinstance(item, str) else item.get("product_id") if isinstance(item, dict) else ""
                if not product_id:
                    errors.append(f"handaas.products.{name} 缺少 product_id")
                elif is_placeholder(product_id):
                    (warnings if allow_placeholders else errors).append(f"handaas.products.{name} 仍是占位值")
    except ConfigError as exc:
        errors.append(str(exc))

    try:
        high_screen = get_high_screen_section(config)
        check_required("high_screen", high_screen, ["url", "product_id", "secret_id", "secret_key"], allow_placeholders, errors, warnings)
        page_size = high_screen.get("default_page_size", 20)
        if not isinstance(page_size, int) or not (1 <= page_size <= 50):
            warnings.append("high_screen.default_page_size 建议为 1-50 的整数")
    except ConfigError as exc:
        errors.append(str(exc))

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
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
        print_json({"ok": False, "errors": [str(exc)], "warnings": []})
        raise SystemExit(1)

    result = validate(config, allow_placeholders=args.allow_placeholders)
    result["config_path"] = str(path)
    print_json(result)
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
