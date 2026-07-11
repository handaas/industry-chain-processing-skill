# Policy Analysis

Use this reference when the user asks for 各地政策、区域政策、产业政策、政策对比、政策扶持、申报指南、公示公告, or policy analysis for an industry chain.

## Core rule

Policy analysis combines two sources:

1. **HandaaS policy MCP** for structured policy search and policy details.
2. **Web search/browsing** for current official context, local government releases, public policy pages, and authoritative media/research context.

Do not put policy analysis into enterprise linking reports. Keep it as a separate `policy_analysis` report unless the user explicitly asks to merge it into another deliverable.

## Preferred sources

When web tools are available, search before composing the final policy analysis. Prefer:

- State Council, ministries, provincial/city/district government websites.
- Industry regulators, development/reform, industry/information, science/technology, transportation, finance departments.
- Official park/zone announcements and public申报指南/公示公告.
- Reputable research institutes or media only as supplements.

For each web item keep `region`, `topic`, `finding`, `source`, `url`, and `date`.

## MCP tools

Use these MCP tools when configured:

- `policy_bigdata_policy_search`: search policy法规、申报指南、公示公告 by keyword, type, agency, region, and publish date.
- `policy_bigdata_policy_info`: fetch policy details by `pnId` when a search result needs details.
- `policy_bigdata_approved_project_stats`: analyze one enterprise's approved policy projects and subsidy trends.

Address examples for `policy_bigdata_policy_search`:

- `国家部委`
- `广东省`
- `广东省,深圳市`
- `[["福建省"],["贵州省","安顺市","平坝县"]]`
- `北京` / `上海` / `天津` / `重庆`

## Workflow

1. Infer policy keyword from the user request. For “智能汽车政策”, use `智能网联汽车 自动驾驶` or the canonical chain/node keyword.
2. Infer regions. If absent, use `国家部委` plus 3-5 relevant regions from the user's geography or the industry context.
3. Web-search official/current policy context. Save findings to JSON or pass `--web-note`.
4. Run `policy_analysis.py`.
5. Render with `render_report.py` to HTML/Markdown.

Example:

```bash
python scripts/policy_analysis.py \
  --chain "智能汽车" \
  --keyword "智能网联汽车 自动驾驶" \
  --region "国家部委" \
  --region "广东省" \
  --region "上海" \
  --region "江苏省" \
  --policy-start "2025-01-01" \
  --web-context /tmp/policy-web-context.json \
  --output /tmp/policy-analysis.json

python scripts/render_report.py \
  --input /tmp/policy-analysis.json \
  --output /tmp/policy-analysis.html
```

`/tmp/policy-web-context.json` can be:

```json
{
  "policy_context": [
    {
      "region": "广东省",
      "topic": "智能网联汽车政策",
      "finding": "用一句话概括联网收集到的政策要点。",
      "source": "来源名称",
      "url": "https://example.com/source",
      "date": "2026-01-01"
    }
  ]
}
```

## Output fields

- `policy_query`: keyword, regions, type, date range, MCP availability.
- `regional_policy_analysis`: per-region policy count, HandaaS/web counts, policy focus, key agencies, representative items, and analysis.
- `policy_dimensions`: support dimensions such as funds/subsidy, pilots/scenarios, technology/R&D, infrastructure, regulation, talent/finance/tax.
- `policy_items`: normalized policy records from HandaaS and web.
- `web_policy_context`: raw web-collected policy context.
- `mcp_queries` / `mcp_errors`: query plan and recoverable MCP errors.

## Quality gate

Before claiming complete:

- The report compares at least two regions unless the user requested one region.
- Web findings include source and URL when network search was used.
- The report distinguishes HandaaS policy data from web-collected context.
- It does not expose tokens, signatures, secret IDs, or raw signed requests.
- It does not include enterprise candidates or enterprise挂链 decisions unless a separate enterprise workflow is requested.
