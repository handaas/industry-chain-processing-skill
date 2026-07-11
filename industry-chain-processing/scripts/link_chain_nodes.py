#!/usr/bin/env python3
"""Plan or execute enterprise linking for multiple L5 nodes in one chain."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence

from build_condition import build_search_plan, infer_role
from common import json_dumps, print_json, redact
from project_context import build_project_context
from render_report import write_report


SCRIPT_DIR = Path(__file__).resolve().parent
LINK_SCRIPT = SCRIPT_DIR / "link_enterprises.py"


def select_nodes(
    nodes: Sequence[Dict[str, Any]],
    *,
    roles: Sequence[str] = (),
    node_pattern: str | None = None,
    offset: int = 0,
    max_nodes: int = 20,
) -> List[Dict[str, Any]]:
    pattern = re.compile(node_pattern, re.I) if node_pattern else None
    selected: List[Dict[str, Any]] = []
    for item in nodes:
        if not isinstance(item, dict):
            continue
        node = str(item.get("name") or "").strip()
        path = [str(value) for value in item.get("path") or []]
        role = infer_role(path)
        if not node or (roles and role not in roles):
            continue
        if pattern and not (pattern.search(node) or pattern.search(" > ".join(path))):
            continue
        selected.append({**item, "name": node, "path": path, "role": role})
    start = max(offset, 0)
    end = None if max_nodes <= 0 else start + max_nodes
    return selected[start:end]


def node_file_name(index: int, node: str) -> str:
    digest = hashlib.sha1(node.encode("utf-8")).hexdigest()[:10]
    return f"node-{index + 1:04d}-{digest}.json"


def summarize_result(payload: Dict[str, Any], output: Path) -> Dict[str, Any]:
    summary = payload.get("link_summary") if isinstance(payload.get("link_summary"), dict) else {}
    return {
        "node": payload.get("node"),
        "path": payload.get("path") or [],
        "mode": payload.get("mode"),
        "precision_limited": bool(payload.get("precision_limited")),
        "condition_origin": (payload.get("search_plan") or {}).get("condition_origin"),
        "recall_routes": [
            item.get("route_id")
            for item in (payload.get("preview") or {}).get("route_results") or []
            if isinstance(item, dict)
        ],
        "candidate_count": int(summary.get("candidate_count") or 0),
        "confirmed": int(summary.get("confirmed") or 0),
        "manual_review": int(summary.get("manual_review") or 0),
        "rejected": int(summary.get("rejected") or 0),
        "reviewed_enterprises": payload.get("reviewed_enterprises") or [],
        "output": str(output),
    }


def build_command(args: argparse.Namespace, node: Dict[str, Any], output: Path) -> List[str]:
    command = [
        sys.executable,
        str(LINK_SCRIPT),
        "--chain",
        args.chain,
        "--node",
        node["name"],
        "--path",
        " > ".join(node["path"]),
        "--precision",
        args.precision,
        "--page-size",
        str(args.page_size),
        "--seed-limit",
        str(args.seed_limit),
        "--max-candidates",
        str(args.max_candidates),
        "--output",
        str(output),
    ]
    if args.config:
        command.extend(["--config", args.config])
    if args.project_root:
        command.extend(["--project-root", args.project_root])
    if args.project_chain:
        command.extend(["--project-chain", args.project_chain])
    if args.with_evidence:
        command.append("--with-evidence")
    if args.require_es:
        command.append("--require-es")
    if args.local:
        command.append("--local")
    if args.skip_project_seeds:
        command.append("--skip-project-seeds")
    for product in args.evidence_product:
        command.extend(["--evidence-product", product])
    return command


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan or execute enterprise linking for all selected L5 nodes in one industry chain.")
    parser.add_argument("--chain", required=True)
    parser.add_argument("--config", help="Skill config JSON path")
    parser.add_argument("--project-root", help="industry-chain-map project root")
    parser.add_argument("--project-chain", help="Canonical project chain override")
    parser.add_argument("--role", action="append", choices=["upstream", "midstream", "downstream", "cross_chain"], default=[])
    parser.add_argument("--node-pattern", help="Regex applied to node name and full path")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--max-nodes", type=int, default=20, help="Maximum nodes in this run; 0 means all matching nodes")
    parser.add_argument("--precision", choices=["strict", "balanced"], default="strict")
    parser.add_argument("--page-size", type=int, default=10)
    parser.add_argument("--seed-limit", type=int, default=8)
    parser.add_argument("--max-candidates", type=int, default=20)
    parser.add_argument("--skip-project-seeds", action="store_true")
    parser.add_argument("--with-evidence", action="store_true")
    parser.add_argument("--evidence-product", action="append", default=[])
    parser.add_argument("--require-es", action="store_true")
    parser.add_argument("--local", action="store_true")
    parser.add_argument("--resume", action="store_true", help="Reuse valid per-node output files")
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--timeout", type=int, default=900, help="Per-node process timeout in seconds")
    parser.add_argument("--dry-run", action="store_true", help="Only generate each node's ES recall plan")
    parser.add_argument("--output", default="output/enterprise-linking/chain-linking.json")
    parser.add_argument("--node-output-dir", help="Directory for complete per-node results")
    parser.add_argument("--report-output", help="Write a business-ready HTML or Markdown chain-linking report")
    parser.add_argument("--report-format", choices=["html", "markdown", "md"], help="Report format; defaults from report file extension")
    parser.add_argument("--report-title", help="Report title")
    args = parser.parse_args()

    context = build_project_context(
        args.chain,
        "",
        project_root=args.project_root,
        preferred_chain=args.project_chain,
        limit=1,
    )
    if not context.get("available"):
        raise SystemExit(str(context.get("reason") or f"未找到产业链：{args.chain}"))
    chain_record = context.get("chain")
    chain_name = str(chain_record.get("name") or args.chain) if isinstance(chain_record, dict) else str(chain_record or args.chain)
    nodes = select_nodes(
        context.get("l5_nodes") or [],
        roles=args.role,
        node_pattern=args.node_pattern,
        offset=args.offset,
        max_nodes=args.max_nodes,
    )
    if not nodes:
        raise SystemExit("没有符合筛选条件的 L5 节点")

    output = Path(args.output).expanduser().resolve()
    node_dir = Path(args.node_output_dir).expanduser().resolve() if args.node_output_dir else output.parent / f"{output.stem}-nodes"
    output.parent.mkdir(parents=True, exist_ok=True)
    node_dir.mkdir(parents=True, exist_ok=True)

    results: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    for index, node in enumerate(nodes):
        node_output = node_dir / node_file_name(index + args.offset, node["name"])
        if args.dry_run:
            node_context = build_project_context(
                args.chain,
                node["name"],
                project_root=args.project_root,
                preferred_chain=args.project_chain,
                limit=4,
            )
            plan = build_search_plan(
                args.chain,
                node["name"],
                node["path"],
                precision=args.precision,
                project_context=node_context if node_context.get("available") else None,
            )
            results.append({
                "node": node["name"],
                "path": plan["node_context"]["canonical_path"],
                "role": plan["node_context"]["role"],
                "condition_origin": plan["condition_origin"],
                "recall_strategy": plan["recall_strategy"],
                "recall_routes": plan["recall_routes"],
                "project_seed_count": len((node_context.get("matched_nodes") or [{}])[0].get("link_samples") or []) if node_context.get("matched_nodes") else 0,
            })
            continue
        if args.resume and node_output.exists():
            try:
                payload = json.loads(node_output.read_text(encoding="utf-8"))
                results.append({**summarize_result(payload, node_output), "resumed": True})
                continue
            except (OSError, json.JSONDecodeError):
                pass
        command = build_command(args, node, node_output)
        try:
            completed = subprocess.run(
                command,
                cwd=str(SCRIPT_DIR.parent.parent),
                capture_output=True,
                text=True,
                timeout=max(args.timeout, 30),
                check=False,
            )
            if completed.returncode != 0 or not node_output.exists():
                message = (completed.stderr or completed.stdout or "节点挂链执行失败").strip().splitlines()[-1]
                failure = {"node": node["name"], "path": node["path"], "error": redact(message)}
                failures.append(failure)
                if args.fail_fast:
                    break
                continue
            payload = json.loads(node_output.read_text(encoding="utf-8"))
            results.append(summarize_result(payload, node_output))
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
            failure = {"node": node["name"], "path": node["path"], "error": redact(str(exc))}
            failures.append(failure)
            if args.fail_fast:
                break

    payload = {
        "report_type": "industry_chain_linking",
        "title": args.report_title or f"{chain_name}产业链节点企业挂链总报告",
        "dry_run": bool(args.dry_run),
        "chain": chain_name,
        "project_chain": chain_record if isinstance(chain_record, dict) else {},
        "selection": {
            "roles": args.role,
            "node_pattern": args.node_pattern,
            "offset": max(args.offset, 0),
            "max_nodes": args.max_nodes,
            "selected_node_count": len(nodes),
        },
        "summary": {
            "completed_nodes": len(results),
            "failed_nodes": len(failures),
            "candidate_count": sum(int(item.get("candidate_count") or 0) for item in results),
            "confirmed": sum(int(item.get("confirmed") or 0) for item in results),
            "manual_review": sum(int(item.get("manual_review") or 0) for item in results),
            "rejected": sum(int(item.get("rejected") or 0) for item in results),
        },
        "nodes": results,
        "failures": failures,
    }
    payload["report_summary"] = (
        f"本报告覆盖“{chain_name}”产业链 {len(results)} 个 L5 节点，"
        f"累计形成 {payload['summary']['confirmed']} 家确认挂链企业和 "
        f"{payload['summary']['manual_review']} 家待复核企业。"
        if not args.dry_run else
        f"本报告覆盖“{chain_name}”产业链 {len(results)} 个 L5 节点的企业筛选条件与召回路线。"
    )
    report_result = None
    if args.report_output:
        payload["report_artifacts"] = {"chain_linking_report": str(Path(args.report_output).expanduser())}
        report_result = write_report(payload, args.report_output, fmt=args.report_format, title=args.report_title)
    output.write_text(json_dumps(payload, pretty=True), encoding="utf-8")
    print_json({"ok": not failures, "output": str(output), "report": report_result, "summary": payload["summary"], "failures": failures})


if __name__ == "__main__":
    main()
