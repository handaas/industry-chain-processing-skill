#!/usr/bin/env python3
"""Small Remote MCP client for industry-chain-processing scripts.

The skill can use Remote MCP with only a platform token:
  export INDUSTRY_CHAIN_MCP_TOKEN=...

It prefers the official MCP Python SDK when installed. This file intentionally
prints only redacted config in errors and never prints tokens/signatures.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any, Dict, Optional

from common import ConfigError, is_placeholder, print_json, redact, resolve_mcp_config


def _plain(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=True)
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


def _extract_tool_result(value: Any) -> Any:
    plain = _plain(value)
    if isinstance(plain, dict):
        structured = plain.get("structuredContent") or plain.get("structured_content")
        if structured is not None:
            if isinstance(structured, dict) and set(structured.keys()) == {"result"}:
                return structured["result"]
            return structured
        content = plain.get("content")
        if isinstance(content, list) and content:
            texts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    texts.append(str(item.get("text") or ""))
            text = "\n".join(texts).strip()
            if text:
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return {"text": text}
    return plain


async def _call_tool_async(url: str, token: str, tool: str, arguments: Dict[str, Any], timeout: int = 60) -> Any:
    try:
        import httpx
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client
    except Exception as exc:  # pragma: no cover - depends on host environment
        raise ConfigError(
            "调用 Remote MCP 需要 Python 包 mcp 和 httpx。请运行：pip install 'mcp>=1.12.0' httpx"
        ) from exc

    headers: Dict[str, str] = {}
    if token and "token=" not in url:
        headers["Authorization"] = f"Bearer {token}"
    http_client = httpx.AsyncClient(headers=headers, timeout=httpx.Timeout(timeout, read=max(timeout, 300)), follow_redirects=True)
    async with http_client:
        transport = streamable_http_client(url=url, http_client=http_client)
        async with transport as streams:
            read_stream, write_stream = streams[0], streams[1]
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool, arguments)
                return _extract_tool_result(result)


async def _list_tools_async(url: str, token: str, timeout: int = 60) -> Any:
    try:
        import httpx
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client
    except Exception as exc:  # pragma: no cover
        raise ConfigError(
            "列出 Remote MCP tools 需要 Python 包 mcp 和 httpx。请运行：pip install 'mcp>=1.12.0' httpx"
        ) from exc

    headers: Dict[str, str] = {}
    if token and "token=" not in url:
        headers["Authorization"] = f"Bearer {token}"
    http_client = httpx.AsyncClient(headers=headers, timeout=httpx.Timeout(timeout, read=max(timeout, 300)), follow_redirects=True)
    async with http_client:
        async with streamable_http_client(url=url, http_client=http_client) as streams:
            read_stream, write_stream = streams[0], streams[1]
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.list_tools()
                return _plain(result)


def get_remote_mcp_config(config_path: Optional[str] = None, *, allow_example: bool = False) -> Dict[str, Any]:
    config = resolve_mcp_config(config_path, allow_example=allow_example)
    if not config or is_placeholder(config.get("url")):
        raise ConfigError(
            "未配置 Remote MCP。请设置 INDUSTRY_CHAIN_MCP_TOKEN，或设置 INDUSTRY_CHAIN_MCP_URL，"
            "或在 handaas.config.json 中加入 mcp.url/mcp.token。"
        )
    return config


def has_remote_mcp_config(config_path: Optional[str] = None, *, allow_example: bool = False) -> bool:
    try:
        get_remote_mcp_config(config_path, allow_example=allow_example)
        return True
    except ConfigError:
        return False


def call_tool(tool: str, arguments: Dict[str, Any], *, config_path: Optional[str] = None, timeout: int = 60) -> Any:
    config = get_remote_mcp_config(config_path)
    return asyncio.run(_call_tool_async(str(config["url"]), str(config.get("token") or ""), tool, arguments, timeout=timeout))


def list_tools(*, config_path: Optional[str] = None, timeout: int = 60) -> Any:
    config = get_remote_mcp_config(config_path)
    return asyncio.run(_list_tools_async(str(config["url"]), str(config.get("token") or ""), timeout=timeout))


def tool_count(payload: Any) -> int:
    if isinstance(payload, dict) and isinstance(payload.get("tools"), list):
        return len(payload["tools"])
    if isinstance(payload, list):
        return len(payload)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Call the industry-chain Remote MCP service with a platform token.")
    parser.add_argument("command", choices=["ping", "list-tools", "call-tool"])
    parser.add_argument("--config", help="Optional config JSON path containing mcp.url/mcp.token.")
    parser.add_argument("--tool", help="Tool name for call-tool.")
    parser.add_argument("--arguments-json", default="{}", help="Tool arguments JSON for call-tool.")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    try:
        config = get_remote_mcp_config(args.config)
        if args.command == "ping":
            tools = list_tools(config_path=args.config, timeout=args.timeout)
            print_json({"ok": True, "tool_count": tool_count(tools), "mcp": redact(config)})
            return
        if args.command == "list-tools":
            print_json(list_tools(config_path=args.config, timeout=args.timeout))
            return
        if not args.tool:
            raise ConfigError("call-tool 需要 --tool")
        arguments = json.loads(args.arguments_json or "{}")
        if not isinstance(arguments, dict):
            raise ConfigError("--arguments-json 必须是 JSON object")
        print_json(call_tool(args.tool, arguments, config_path=args.config, timeout=args.timeout))
    except Exception as exc:
        print_json({"ok": False, "error": str(exc)})
        raise SystemExit(1)


if __name__ == "__main__":
    main()
