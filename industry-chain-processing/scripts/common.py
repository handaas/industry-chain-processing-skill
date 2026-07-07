#!/usr/bin/env python3
"""Shared helpers for the industry-chain-processing skill."""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Iterable, Optional, Tuple

SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
EXAMPLE_CONFIG = SKILL_DIR / "assets" / "config.example.json"
DEFAULT_CONFIG = pathlib.Path.home() / ".industry-chain-processing" / "handaas.config.json"
SECRET_KEYWORDS = ("secret", "signature", "token", "api_key", "apikey", "password")


class ConfigError(RuntimeError):
    pass


class ApiError(RuntimeError):
    pass


def json_dumps(value: Any, *, pretty: bool = False) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2 if pretty else None, separators=None if pretty else (",", ":"))


def load_json_file(path: pathlib.Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"配置文件不存在：{path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"配置文件不是合法 JSON：{path}: {exc}") from exc


def resolve_config_path(config_path: Optional[str] = None, *, allow_example: bool = False) -> pathlib.Path:
    candidates = [
        config_path,
        os.environ.get("INDUSTRY_CHAIN_CONFIG"),
        os.environ.get("HANDAAS_CONFIG"),
        str(DEFAULT_CONFIG),
    ]
    for candidate in candidates:
        if candidate and pathlib.Path(candidate).expanduser().exists():
            return pathlib.Path(candidate).expanduser().resolve()
    if allow_example and EXAMPLE_CONFIG.exists():
        return EXAMPLE_CONFIG.resolve()
    raise ConfigError(
        "未找到配置文件。请传 --config，或设置 INDUSTRY_CHAIN_CONFIG/HANDAAS_CONFIG，"
        f"或创建 {DEFAULT_CONFIG}。"
    )


def load_config(config_path: Optional[str] = None, *, allow_example: bool = False) -> Tuple[Dict[str, Any], pathlib.Path]:
    path = resolve_config_path(config_path, allow_example=allow_example)
    data = load_json_file(path)
    if not isinstance(data, dict):
        raise ConfigError("配置文件顶层必须是 JSON object")
    return data, path


def is_placeholder(value: Any) -> bool:
    text = str(value or "").strip().lower()
    if not text:
        return True
    return (
        text.startswith("your_")
        or "_for_" in text
        or "example.com" in text
        or text in {"todo", "replace_me", "changeme", "xxx"}
    )


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(token in lowered for token in SECRET_KEYWORDS):
                out[key] = "***REDACTED***"
            else:
                out[key] = redact(item)
        return out
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def md5_hex(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def python_string(value: Any, nested: bool = False) -> str:
    """Mimic the local enterprise-search signing string used by exported examples."""
    if isinstance(value, dict):
        return "{" + ", ".join(f"'{key}': {python_string(item, True)}" for key, item in value.items()) + "}"
    if isinstance(value, list):
        return "[" + ", ".join(python_string(item, True) for item in value) + "]"
    if isinstance(value, str):
        if not nested:
            return value
        return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"
    return str(value)


def high_screen_signature(secret_key: str, call_params: Dict[str, Any]) -> str:
    material = "".join(python_string(call_params[key]) for key in sorted(call_params)) + secret_key
    return md5_hex(material)


def daas_signature(secret_key: str, call_params: Dict[str, Any]) -> str:
    material = "".join(str(call_params[key]) for key in sorted(call_params)) + secret_key
    return md5_hex(material)


def get_handaas_section(config: Dict[str, Any]) -> Dict[str, Any]:
    section = config.get("handaas") or config.get("daas")
    if not isinstance(section, dict):
        raise ConfigError("缺少 handaas 配置段")
    return section


def get_high_screen_section(config: Dict[str, Any]) -> Dict[str, Any]:
    section = config.get("high_screen") or config.get("highScreen")
    if not isinstance(section, dict):
        raise ConfigError("缺少 high_screen 配置段")
    return section


def product_id_of(products: Dict[str, Any], product_name: str) -> str:
    if product_name not in products:
        available = "、".join(products.keys()) or "无"
        raise ConfigError(f"未找到证据产品：{product_name}。可用产品：{available}")
    item = products[product_name]
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return str(item.get("product_id") or item.get("id") or item.get("_id") or "")
    return ""


def http_json_post(url: str, payload: Dict[str, Any], *, timeout: int = 30) -> Dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json_dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            text = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ApiError(f"HTTP {exc.code}: {body[:500]}") from exc
    except urllib.error.URLError as exc:
        raise ApiError(f"请求失败：{exc}") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ApiError(f"响应不是合法 JSON：{text[:500]}") from exc


def http_form_post(url: str, payload: Dict[str, Any], *, timeout: int = 30) -> Dict[str, Any]:
    encoded = urllib.parse.urlencode({key: str(value) for key, value in payload.items()}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=encoded,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            text = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ApiError(f"HTTP {exc.code}: {body[:500]}") from exc
    except urllib.error.URLError as exc:
        raise ApiError(f"请求失败：{exc}") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ApiError(f"响应不是合法 JSON：{text[:500]}") from exc


def print_json(value: Any) -> None:
    print(json_dumps(value, pretty=True))


def die(message: str, code: int = 1) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)
