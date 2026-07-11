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
from typing import Any, Dict, Optional, Tuple

SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
EXAMPLE_CONFIG = SKILL_DIR / "assets" / "config.example.json"
DEFAULT_CONFIG = pathlib.Path.home() / ".industry-chain-processing" / "handaas.config.json"
DEFAULT_MCP_URL_TEMPLATE = "https://mcp.handaas.com/industry-chain/industry_chain?token={token}"
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
        or "your_" in text
        or "_for_" in text
        or "example.com" in text
        or "{token}" in text
        or "your token" in text
        or text in {"todo", "replace_me", "changeme", "xxx"}
    )


def redact_url(value: str) -> str:
    if not any(marker in value.lower() for marker in ("token=", "signature=", "secret_id=", "secret_key=")):
        return value
    try:
        parsed = urllib.parse.urlparse(value)
        query = []
        for key, item in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True):
            if key.lower() in {"token", "signature", "secret", "secret_id", "secret_key"}:
                query.append((key, "REDACTED"))
            else:
                query.append((key, item))
        return urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(query)))
    except Exception:
        return value


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
    if isinstance(value, str):
        return redact_url(value)
    return value


def build_mcp_url(url: Optional[str] = None, token: Optional[str] = None) -> str:
    """Build a Remote MCP URL from either a full URL or a platform token."""
    raw_url = (url or "").strip()
    raw_token = (token or "").strip()
    if raw_url:
        if raw_token and "{token}" in raw_url:
            return raw_url.replace("{token}", urllib.parse.quote(raw_token, safe=""))
        if raw_token and "token=" not in raw_url:
            parsed = urllib.parse.urlparse(raw_url)
            query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
            query.append(("token", raw_token))
            return urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(query)))
        return raw_url
    if raw_token:
        return DEFAULT_MCP_URL_TEMPLATE.replace("{token}", urllib.parse.quote(raw_token, safe=""))
    return ""


def mcp_config_from_env() -> Dict[str, Any]:
    """Resolve Remote MCP config from environment variables only."""
    token = os.environ.get("INDUSTRY_CHAIN_MCP_TOKEN") or os.environ.get("HANDAAS_MCP_TOKEN")
    url = os.environ.get("INDUSTRY_CHAIN_MCP_URL") or os.environ.get("HANDAAS_MCP_URL")
    resolved = build_mcp_url(url, token)
    if not resolved:
        return {}
    return {"url": resolved, "token": token or "", "source": "environment"}


def get_mcp_section(config: Dict[str, Any]) -> Dict[str, Any]:
    section = config.get("mcp") or config.get("remote_mcp") or config.get("remoteMcp")
    if not isinstance(section, dict):
        raise ConfigError("缺少 mcp 配置段")
    token = section.get("token")
    url = build_mcp_url(str(section.get("url") or ""), str(token or ""))
    if not url:
        raise ConfigError("mcp.url 或 mcp.token 至少需要配置一个")
    return {**section, "url": url, "token": token or "", "source": "config"}


def resolve_mcp_config(config_path: Optional[str] = None, *, allow_example: bool = False) -> Dict[str, Any]:
    """Resolve Remote MCP config, preferring env token/URL over config file."""
    env_config = mcp_config_from_env()
    if env_config:
        return env_config
    try:
        config, _ = load_config(config_path, allow_example=allow_example)
        return get_mcp_section(config)
    except ConfigError:
        return {}


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
