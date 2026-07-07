#!/usr/bin/env python3
"""Render an industry-chain analysis result as standalone HTML or Markdown."""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import pathlib
import sys
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from common import json_dumps


def load_payload(input_path: str | None) -> Dict[str, Any]:
    if input_path:
        path = pathlib.Path(input_path).expanduser()
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        raw = sys.stdin.read().strip()
        if not raw:
            raise SystemExit("请提供 --input <result.json> 或通过 stdin 传入 JSON")
        data = json.loads(raw)
    if not isinstance(data, dict):
        raise SystemExit("报告输入必须是 JSON object")
    return data


def as_list(value: Any) -> List[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    return [value]


def first_present(data: Mapping[str, Any], keys: Sequence[str], default: Any = None) -> Any:
    for key in keys:
        if key in data and data[key] not in (None, "", []):
            return data[key]
    return default


def infer_title(data: Mapping[str, Any], explicit: str | None = None) -> str:
    if explicit:
        return explicit
    title = first_present(data, ["title", "report_title"])
    if title:
        return str(title)
    chain = first_present(data, ["chain", "industry", "industry_chain"])
    node = first_present(data, ["node", "segment", "matched_segment"])
    if chain and node:
        return f"{chain} - {node} 企业分析报告"
    if chain:
        return f"{chain} 企业分析报告"
    return "旷湖产业链分析报告"


def normalize_decisions(data: Mapping[str, Any]) -> List[Dict[str, Any]]:
    decisions = first_present(data, ["decisions", "decision_results", "links"], [])
    out: List[Dict[str, Any]] = []
    for item in as_list(decisions):
        if isinstance(item, dict):
            out.append(item)
        else:
            out.append({"decision": str(item)})
    return out


def normalize_candidates(data: Mapping[str, Any]) -> List[Dict[str, Any]]:
    candidates = first_present(data, ["candidates", "companies", "samples"], [])
    if not candidates and isinstance(data.get("preview"), dict):
        candidates = data["preview"].get("samples", [])
    out: List[Dict[str, Any]] = []
    for item in as_list(candidates):
        if isinstance(item, dict):
            out.append(item)
        else:
            out.append({"name": str(item)})
    return out


def decision_counts(decisions: Sequence[Mapping[str, Any]]) -> Dict[str, int]:
    counts = {"confirmed": 0, "uncertain": 0, "rejected": 0}
    for item in decisions:
        label = str(item.get("decision") or "uncertain")
        counts[label] = counts.get(label, 0) + 1
    return counts


def text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json_dumps(value, pretty=True)
    return str(value)


def esc(value: Any) -> str:
    return html.escape(text(value), quote=True)


def render_html_list(items: Iterable[Any]) -> str:
    rows = []
    for item in items:
        if isinstance(item, dict):
            label = item.get("name") or item.get("title") or item.get("segment") or item.get("matched_segment") or item
            rows.append(f"<li><pre>{esc(label)}</pre></li>" if isinstance(label, dict) else f"<li>{esc(label)}</li>")
        else:
            rows.append(f"<li>{esc(item)}</li>")
    return "<ul>" + "".join(rows) + "</ul>" if rows else "<p class=\"muted\">暂无</p>"


def render_table(rows: Sequence[Mapping[str, Any]], columns: Sequence[tuple[str, str]]) -> str:
    if not rows:
        return "<p class=\"muted\">暂无</p>"
    head = "".join(f"<th>{html.escape(label)}</th>" for _, label in columns)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{esc(row.get(key, ''))}</td>" for key, _ in columns)
        body_rows.append(f"<tr>{cells}</tr>")
    return f"<div class=\"table-wrap\"><table><thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table></div>"


def render_html(data: Dict[str, Any], title: str) -> str:
    generated_at = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    industry_map = as_list(first_present(data, ["industry_map", "map", "ontology", "industry_structure"], []))
    priority_segments = as_list(first_present(data, ["priority_segments", "segments", "focus_segments"], []))
    search_strategy = as_list(first_present(data, ["search_strategy", "strategy", "search_plan"], []))
    next_actions = as_list(first_present(data, ["next_actions", "actions", "recommendations"], []))
    candidates = normalize_candidates(data)
    decisions = normalize_decisions(data)
    counts = decision_counts(decisions)
    summary = first_present(data, ["summary", "conclusion", "overview"], "")
    preview = data.get("preview") if isinstance(data.get("preview"), dict) else {}
    total = preview.get("total") or data.get("total") or len(candidates)

    decision_columns = [
        ("enterprise_name", "企业"),
        ("matched_segment", "匹配环节"),
        ("decision", "判断"),
        ("evidence_strength", "证据强度"),
        ("reason", "原因"),
        ("next_action", "下一步"),
    ]
    candidate_columns = [
        ("name", "企业"),
        ("id", "ID"),
        ("socialCreditCode", "统一社会信用代码"),
        ("regCapital", "注册资本"),
    ]

    raw_json = esc(json_dumps(data, pretty=True))
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{esc(title)}</title>
  <style>
    :root {{ --bg:#f6f7fb; --card:#ffffff; --text:#172033; --muted:#667085; --line:#e6e8ef; --blue:#2454ff; --green:#0f8a5f; --amber:#b7791f; --red:#c53030; }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; background:var(--bg); color:var(--text); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",Arial,sans-serif; line-height:1.55; }}
    header {{ padding:36px 28px 28px; background:linear-gradient(135deg,#101828,#2447ff); color:white; }}
    main {{ max-width:1120px; margin:0 auto; padding:24px; }}
    h1 {{ margin:0 0 8px; font-size:30px; }}
    h2 {{ margin:0 0 14px; font-size:20px; }}
    .subtitle {{ opacity:.82; }}
    .grid {{ display:grid; grid-template-columns: repeat(auto-fit,minmax(180px,1fr)); gap:14px; margin-top:-36px; }}
    .card {{ background:var(--card); border:1px solid var(--line); border-radius:16px; padding:18px; box-shadow:0 8px 24px rgba(16,24,40,.06); margin-bottom:18px; }}
    .metric {{ font-size:28px; font-weight:750; }}
    .label {{ color:var(--muted); font-size:13px; }}
    .confirmed {{ color:var(--green); }} .uncertain {{ color:var(--amber); }} .rejected {{ color:var(--red); }}
    .muted {{ color:var(--muted); }}
    ul {{ margin:8px 0 0 20px; padding:0; }} li {{ margin:6px 0; }}
    .table-wrap {{ overflow:auto; border:1px solid var(--line); border-radius:12px; }}
    table {{ width:100%; border-collapse:collapse; background:white; }}
    th,td {{ padding:11px 12px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; font-size:14px; }}
    th {{ background:#f8f9fc; color:#344054; font-weight:650; white-space:nowrap; }}
    tr:last-child td {{ border-bottom:0; }}
    details {{ margin-top:8px; }}
    pre {{ white-space:pre-wrap; word-break:break-word; margin:0; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:12px; }}
    .section-title {{ display:flex; justify-content:space-between; gap:12px; align-items:center; }}
    .tag {{ display:inline-flex; align-items:center; border-radius:999px; padding:3px 9px; background:#eef2ff; color:var(--blue); font-size:12px; }}
  </style>
</head>
<body>
  <header>
    <h1>{esc(title)}</h1>
    <div class="subtitle">由旷湖产业链分析 Skill 生成 · {esc(generated_at)}</div>
  </header>
  <main>
    <section class="grid">
      <div class="card"><div class="metric">{esc(total)}</div><div class="label">候选企业 / 线索</div></div>
      <div class="card"><div class="metric confirmed">{counts.get('confirmed',0)}</div><div class="label">确认匹配</div></div>
      <div class="card"><div class="metric uncertain">{counts.get('uncertain',0)}</div><div class="label">待复核</div></div>
      <div class="card"><div class="metric rejected">{counts.get('rejected',0)}</div><div class="label">建议剔除</div></div>
    </section>

    <section class="card">
      <div class="section-title"><h2>结论摘要</h2><span class="tag">Summary</span></div>
      <p>{esc(summary) if summary else '本报告根据输入结果展示产业链结构、企业搜索策略、候选企业和证据化判断。'}</p>
    </section>

    <section class="card">
      <h2>产业链结构与重点环节</h2>
      {render_html_list(industry_map or priority_segments)}
    </section>

    <section class="card">
      <h2>企业搜索策略</h2>
      {render_html_list(search_strategy)}
    </section>

    <section class="card">
      <h2>候选企业</h2>
      {render_table(candidates, candidate_columns)}
    </section>

    <section class="card">
      <h2>证据化判断</h2>
      {render_table(decisions, decision_columns)}
    </section>

    <section class="card">
      <h2>下一步建议</h2>
      {render_html_list(next_actions)}
    </section>

    <section class="card">
      <h2>原始数据</h2>
      <details><summary>展开 JSON</summary><pre>{raw_json}</pre></details>
    </section>
  </main>
</body>
</html>
"""


def md_list(items: Iterable[Any]) -> str:
    rows = []
    for item in items:
        rows.append(f"- {text(item).replace(chr(10), ' ')}")
    return "\n".join(rows) if rows else "暂无"


def md_table(rows: Sequence[Mapping[str, Any]], columns: Sequence[tuple[str, str]]) -> str:
    if not rows:
        return "暂无"
    header = "| " + " | ".join(label for _, label in columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for row in rows:
        vals = [text(row.get(key, "")).replace("\n", " ").replace("|", "\\|") for key, _ in columns]
        body.append("| " + " | ".join(vals) + " |")
    return "\n".join([header, sep, *body])


def render_markdown(data: Dict[str, Any], title: str) -> str:
    industry_map = as_list(first_present(data, ["industry_map", "map", "ontology", "industry_structure"], []))
    priority_segments = as_list(first_present(data, ["priority_segments", "segments", "focus_segments"], []))
    search_strategy = as_list(first_present(data, ["search_strategy", "strategy", "search_plan"], []))
    next_actions = as_list(first_present(data, ["next_actions", "actions", "recommendations"], []))
    candidates = normalize_candidates(data)
    decisions = normalize_decisions(data)
    summary = first_present(data, ["summary", "conclusion", "overview"], "")
    candidate_columns = [("name", "企业"), ("id", "ID"), ("socialCreditCode", "统一社会信用代码"), ("regCapital", "注册资本")]
    decision_columns = [("enterprise_name", "企业"), ("matched_segment", "匹配环节"), ("decision", "判断"), ("evidence_strength", "证据强度"), ("reason", "原因"), ("next_action", "下一步")]
    return "\n\n".join([
        f"# {title}",
        f"生成时间：{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "## 结论摘要\n" + (text(summary) or "本报告根据输入结果展示产业链结构、企业搜索策略、候选企业和证据化判断。"),
        "## 产业链结构与重点环节\n" + md_list(industry_map or priority_segments),
        "## 企业搜索策略\n" + md_list(search_strategy),
        "## 候选企业\n" + md_table(candidates, candidate_columns),
        "## 证据化判断\n" + md_table(decisions, decision_columns),
        "## 下一步建议\n" + md_list(next_actions),
    ]) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Render an industry-chain analysis result as HTML or Markdown.")
    parser.add_argument("--input", help="Analysis result JSON. Reads stdin when omitted.")
    parser.add_argument("--output", required=True, help="Output report path, e.g. /tmp/report.html or /tmp/report.md")
    parser.add_argument("--format", choices=["html", "markdown", "md"], help="Output format. Defaults from file extension.")
    parser.add_argument("--title", help="Report title.")
    args = parser.parse_args()

    data = load_payload(args.input)
    title = infer_title(data, args.title)
    output = pathlib.Path(args.output).expanduser()
    fmt = args.format or ("markdown" if output.suffix.lower() in {".md", ".markdown"} else "html")
    rendered = render_markdown(data, title) if fmt in {"markdown", "md"} else render_html(data, title)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print(json_dumps({"ok": True, "format": "markdown" if fmt in {"markdown", "md"} else "html", "output": str(output)}, pretty=True))


if __name__ == "__main__":
    main()
