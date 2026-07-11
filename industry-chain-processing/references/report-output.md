# Report Output

Use this reference when the user asks for 展示、报告、HTML、静态页面、材料、交付、Markdown, 专业产业链分析报告, 企业产业链定位报告, 企业挂链报告, or 指定企业节点分析报告.

## Default display modes

- Chat/table: default for fast iteration.
- HTML: use for commercial/shareable visual reports. Produce a standalone local file with embedded CSS and no debug/internal sections.
- Markdown: use for wiki, knowledge base, PRD, or later manual editing.
- JSON: use for system integration or further processing.

## Report types

Keep these report types separate:

1. **产业链分析报告**: follow the professional research structure defined below, from industry definition through value flow and structural characteristics. The abstract may use authoritative policy/market/technology context. Do not include enterprise recall, 挂链总览, candidate enterprises, evidence summaries, or existing enterprise-link anchors.
2. **单节点企业挂链报告**: focus on enterprise recall, evidence verification, confirmed/uncertain/rejected decisions, and judgment reasons. Use `link_enterprises.py --report-output ...`.
3. **整链节点企业挂链总报告**: summarize L5 node coverage, per-node candidate/review counts, confirmed enterprises, manual-review enterprises, and incomplete nodes. Use `link_chain_nodes.py --report-output ...`.
4. **企业产业链定位报告**: start from one enterprise name, resolve the canonical enterprise, compare all project chains, and explain the primary plus alternative L2/L3/L5 positions with evidence. Use `enterprise_chain_positioning.py --report-output ...`.
5. **指定企业节点分析报告**: focus on one company and one already-specified L5 node fit assessment. Use `enterprise_node_report.py --report-output ...`.
6. **区域政策分析报告**: focus on national/provincial/city policy search, regional comparison, policy support dimensions, representative policy items, and source-backed web context. Use `policy_analysis.py`.

## Project-first rule

If a current `industry-chain-map` project is available, professional industry-chain analysis reports must reuse project context before rendering:

1. Resolve project root with `--project-root`, `INDUSTRY_CHAIN_PROJECT_ROOT`, `INDUSTRY_CHAIN_MAP_ROOT`, or the known sibling path.
2. Map user chain/node to canonical project chain and, when a node is specified, to project L5 nodes.
3. Include L1-L5 level definitions, graph summary, node mapping, project graph tree, value-chain rows, node records, hierarchy analysis, analysis framework, and structural insights.
4. Do not replace the project graph ontology with a generic generated structure unless project context is unavailable.

## Professional report structure

Use this order for every commercial industry-chain analysis report:

1. **报告摘要**: define the industry object, graph scale, main value segments, and the most important policy/technology context in concise research language.
2. **产业定义与层级口径**: state the industry boundary, included node types, graph coverage, focus scope, and detailed L1/L2/L3/L4/L5 definitions.
3. **产业发展环境**: present authoritative policy, market, standard, technology, and commercialization evidence. Omit this chapter when no reliable evidence exists.
4. **产业链全景图谱**: display the L2/L3/L5 topology and node scale without mixing enterprises into the hierarchy.
5. **价值环节深度解析**: analyze each L2 segment's functional positioning, L3 composition, representative L5 nodes, scale, and upstream/downstream linkage.
6. **关键节点与产品技术体系**: use each L3 module to define capability boundaries and representative L5 products, technologies, services, or solution nodes.
7. **价值传导与协同关系**: explain how components, equipment, software, data, integration, and application value move between adjacent L2 segments.
8. **产业结构特征**: interpret topology, node concentration, equipment/software integration, and application closure using explicit graph evidence.

Do not add a conclusion, recommendation, next-action, priority-ranking, high/medium label, or generic “insight” card chapter.

## Web-assisted abstract rule

For a professional/commercial industry-chain analysis report, the “报告摘要” should not be a generic script summary. When network tools are available:

1. Collect 3-5 authoritative background items before composing the report.
2. Prefer government departments, regulators, industry associations, research institutes, listed-company/official disclosures, or reputable financial/technology media.
3. Capture each item as `topic`, `finding`, `source`, `url`, and `date`.
4. Use the findings to explain policy traction, market/technology evolution, commercialization stage, or boundary conditions in the abstract.
5. Keep sources in the optional “产业背景与分析依据” section.

If network is unavailable or the user requests offline output, continue from project graph records and do not fabricate current facts.

## Workflow

1. Build or collect a structured result object with these fields when available:
   - `title`
   - `summary`
   - `executive_summary`
   - `industry_overview`
   - `industry_definition`
   - `industry_map`
   - `project_graph_summary`
   - `node_mapping`
   - `level_definitions`
   - `market_context`
   - `project_graph_tree`
   - `project_value_chain`
   - `project_node_records`
   - `value_chain`
   - `hierarchy_analysis`
   - `segment_analysis`
   - `key_node_system`
   - `value_flow`
   - `structural_characteristics`
   - `regional_policy_analysis`
   - `policy_dimensions`
   - `policy_items`
2. For professional industry-chain analysis reports, compose directly from chain/node + project context:

```bash
python scripts/compose_industry_report.py \
  --chain "智能汽车" \
  --node "自动驾驶" \
  --project-root "$INDUSTRY_CHAIN_PROJECT_ROOT" \
  --project-chain "智能网联汽车" \
  --project-node "自动驾驶" \
  --output /tmp/industry-chain-analysis.json
```

When web context has been collected, pass it in either form:

```bash
python scripts/compose_industry_report.py \
  --chain "智能汽车" \
  --node "自动驾驶" \
  --project-root "$INDUSTRY_CHAIN_PROJECT_ROOT" \
  --project-chain "智能网联汽车" \
  --project-node "自动驾驶" \
  --market-context /tmp/industry-market-context.json \
  --output /tmp/industry-chain-analysis.json

python scripts/compose_industry_report.py \
  --chain "智能汽车" \
  --node "自动驾驶" \
  --market-note "政策背景|智能网联汽车相关政策正在推动自动驾驶商业化试点与车路云协同落地|权威来源|https://example.com|2026-01-01" \
  --output /tmp/industry-chain-analysis.json
```

`/tmp/industry-market-context.json` can be:

```json
{
  "market_context": [
    {
      "topic": "政策背景",
      "finding": "用一句话概括权威产业背景与关键影响。",
      "source": "来源名称",
      "url": "https://example.com/source",
      "date": "2026-01-01"
    }
  ]
}
```

3. For enterprise linking reports, run a separate enterprise workflow:

```bash
python scripts/link_enterprises.py \
  --chain "工业母机" \
  --node "伺服驱动器" \
  --path "工业母机>上游：核心零部件与基础材料>伺服系统>伺服驱动器" \
  --page-size 5 \
  --with-evidence \
  --require-es \
  --output /tmp/enterprise-linking.json \
  --report-output /tmp/enterprise-linking.html
```

For multiple L5 nodes, use `link_chain_nodes.py`. Its aggregate report must retain each node path, candidate/review counts, reviewed enterprises, and the per-node result path.

```bash
python scripts/link_chain_nodes.py \
  --chain "工业母机" \
  --project-root "$INDUSTRY_CHAIN_PROJECT_ROOT" \
  --max-nodes 20 \
  --with-evidence \
  --require-es \
  --resume \
  --output /tmp/industry-chain-linking.json \
  --report-output /tmp/industry-chain-linking.html
```

4. When the user provides only an enterprise name, resolve and position it across the complete project graph:

```bash
python scripts/enterprise_chain_positioning.py \
  --enterprise "深圳市汇川技术股份有限公司" \
  --project-root "$INDUSTRY_CHAIN_PROJECT_ROOT" \
  --output /tmp/enterprise-chain-positioning.json \
  --report-output /tmp/enterprise-chain-positioning.html
```

The report must include the canonical enterprise, enterprise profile, primary L2/L3/L5 path, cross-chain ranking, candidate-node ranking, evidence coverage, close alternatives, and positioning boundary. Do not silently convert a close multi-chain match into an exclusive classification.

5. For a specified enterprise-node report, collect evidence directly and map the input node to the project L5 target:

```bash
python scripts/enterprise_node_report.py \
  --chain "智能汽车" \
  --node "自动驾驶" \
  --path "智能汽车产业链>智能化系统>自动驾驶" \
  --enterprise "安徽中科星驰自动驾驶技术有限公司" \
  --key-type name \
  --project-root "$INDUSTRY_CHAIN_PROJECT_ROOT" \
  --project-chain "智能网联汽车" \
  --project-node "自动驾驶" \
  --output /tmp/enterprise-node.json \
  --report-output /tmp/enterprise-node.html
```

6. For regional policy analysis, combine HandaaS policy MCP with web context:

```bash
python scripts/policy_analysis.py \
  --chain "智能汽车" \
  --keyword "智能网联汽车 自动驾驶" \
  --region "国家部委" \
  --region "广东省" \
  --region "上海" \
  --policy-start "2025-01-01" \
  --web-context /tmp/policy-web-context.json \
  --output /tmp/policy-analysis.json
```

7. Use `render_report.py` only when re-rendering an existing JSON artifact or converting it to another format:

```bash
python scripts/render_report.py --input output/industry-chain-analysis.json --output output/industry-chain-analysis.html
python scripts/render_report.py --input output/industry-chain-analysis.json --output output/industry-chain-analysis.md
python scripts/render_report.py --input output/enterprise-chain-positioning.json --output output/enterprise-chain-positioning.html
python scripts/render_report.py --input output/policy-analysis.json --output output/policy-analysis.html
```

8. Return the JSON path and direct report path, plus canonical chain/node mapping, enterprise positioning summary, linking coverage, or policy query/region summary depending on report type.

## Quality bar

- The report should be readable without Codex context.
- Keep implementation details out of the main report unless the user asks.
- Professional industry-chain analysis reports must be commercial deliverables with the fixed eight-part structure: summary, definition and hierarchy, development environment, graph, segment analysis, node system, value flow, and structural characteristics.
- Empty graphs are forbidden. The composed payload must have L2 > 0, L3 > 0, and L5 > 0; every rendered L2 must contain at least one L3 and every rendered L3 must contain at least one L5. Repair from value-chain/fallback ontology before rendering, or fail without writing the report.
- HTML reports should use a research-report visual style: A4-like white pages, grey striped top rule, blue report banner, left cover sidebar with catalogue/scope, navy section headings, dark-blue table headers, light-blue zebra rows, and print-friendly page breaks.
- The report abstract must synthesize project graph structure and, when available, web-collected industry context; it should read like a professional industry-chain analysis abstract, not a generic execution summary.
- Visible report prose must never expose collection or generation workflow language such as “联网收集”, “用于增强摘要/分析口径”, “未传入资料”, “Skill 生成”, input parameters, tool names, or internal workflow decisions. State the policy environment, market evolution, technology route, evidence source, and analytical finding directly.
- Professional industry-chain analysis reports must not include conclusion/recommendation sections, raw JSON, internal debug fields, data-quality/interface-status cards, empty tables, enterprise candidates, 挂链总览, existing挂链 anchors, evidence summaries, or confirmed/uncertain/rejected enterprise decisions.
- Enterprise positioning reports may include enterprise profile, primary and alternative paths, project representative-enterprise anchors, evidence coverage, confidence, and classification boundaries. They should not claim exclusive membership when top chain scores are close.
- Enterprise linking reports and specified enterprise-node reports may include candidates, evidence, fit assessment, risk/review flags, and clear挂链建议.
- Enterprise linking reports must separate confirmed, manual-review, and rejected enterprises. Whole-chain reports must preserve per-node attribution instead of presenting one undifferentiated company list.
- If project context is unavailable, state that the hierarchy follows a standard industry ontology and distinguish it from project-archived graph records without mentioning tools or generation workflow.
- For real enterprise data, avoid printing secrets or raw signed requests.
