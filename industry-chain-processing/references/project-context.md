# Project Context Reuse

Use this reference whenever the user asks for 专业产业链分析报告、图谱展示、产业链层级分析、企业所属产业链定位、挂链、节点分析, or when a current `industry-chain-map` project is available.

## Core rule

Do not generate a generic industry-chain report if project graph data exists. Reuse the current project's graph ontology and node records first. For industry-chain analysis reports, stop at hierarchy and analysis; do not include enterprise-link records or 挂链结果. Use enterprise links only in enterprise linking reports or specified enterprise-node reports.

For professional report abstracts, project graph reuse may be combined with web-collected industry context. Use external sources only for policy, market, technology, commercialization, or regulatory background; keep graph hierarchy and node records sourced from the project.

## Root discovery

Resolve the visualization project root in this order:

1. CLI `--project-root <path>`.
2. `INDUSTRY_CHAIN_PROJECT_ROOT`.
3. `INDUSTRY_CHAIN_MAP_ROOT`.
4. Generic sibling discovery: `./industry-chain-map`, `../industry-chain-map`, or `../industrychainvisualization/industry-chain-map` when present.

## Data sources

Prefer the SQLite archive:

- `.data/industry-chain-archive.sqlite`
- `chain_definitions`: canonical chain names, current graph JSON, node count, enterprise count cache.
- `canonical_nodes` + `chain_node_edges`: canonical L1/L2/L3/L5 nodes and paths.
- `high_screen_condition_groups`: saved high-screen condition groups and keywords.
- `enterprise_node_links`: existing candidate/confirmed enterprise links; use only in enterprise linking reports, not in pure industry-chain analysis reports.

Fallback to static graph JSON:

- `src/data/industries/*.json`

## Ontology constraints

- Use L1/L2/L3/L4/L5 as the report口径; current project graph display usually renders L1/L2/L3/L5, with L4 as an optional compatibility/interpretation layer.
- Use L5 as the enterprise-linking target in separate linking workflows.
- Do not add enterprises under graph nodes. Enterprises remain link records.
- In industry-chain analysis reports, show node IDs, node paths, condition keywords, hierarchy relationships, and analysis. Do not show enterprise link samples.

## Mapping behavior

Map natural user wording to canonical project data before report composition.

Example project mapping:

- Input chain: `智能汽车` or `智能汽车产业链`
- Canonical chain: `智能网联汽车`
- Example chain ID: `chain_754545cda6a26fe8`
- Example graph stats: L2=3, L3=13, L5=49, cached candidate enterprises=262
- Input node: `自动驾驶`
- Mapped L5 nodes can include:
  - `自动驾驶解决方案`
  - `自动驾驶仿真平台`

If multiple L5 nodes match, prefer the closest business target for the requested report and include alternatives in `node_mapping` or `project_node_records`.

## Required output fields for industry-chain analysis reports

Project-aware industry-chain analysis reports should include these fields when available:

- `project_graph_summary`: canonical chain, chain ID, source, node counts, cached enterprise counts.
- `node_mapping`: input chain/node, canonical chain, mapped project nodes, primary project path.
- `level_definitions`: detailed L1/L2/L3/L4/L5 interpretation口径, including L4 optional-layer semantics.
- `market_context`: optional web-collected background items used to strengthen the report abstract and “产业背景与分析依据”.
- `project_graph_tree`: L1/L2/L3/L5 tree for static HTML graph display using the current project card style.
- `project_value_chain`: project L2/L3/L5 rows from the graph.
- `project_node_records`: L5 node name, path, node ID, condition source, condition keywords.
- `hierarchy_analysis`: interpretation of L2/L3/L5 hierarchy.
- `analysis_framework`: dimensions for hierarchy completeness, node boundary, value transfer, and reuse.

Do not include `project_seed_links`, `link_summary`, `candidates`, `decisions`, or `evidence_summary` in pure industry-chain analysis reports.

## Enterprise-name positioning

When the user provides an enterprise name without a chain or node:

1. Resolve the canonical enterprise with `enterprise_get_keyword_search`; prefer an exact normalized name over branches or similarly named companies.
2. Collect business profile, enterprise introduction, business tags, patents, and bidding evidence through existing HandaaS MCP wrappers. An unavailable product is an evidence gap, not a reason to stop the remaining calls.
3. Scan every project L5 node instead of guessing a chain from the registered industry.
4. Score direct products and technologies above generic business scope or registered industry. Treat project representative-company records as supporting anchors, not exclusive truth.
5. Reduce the weight of generic nodes and downstream application scenarios when the enterprise evidence describes an upstream product, component, equipment, software, or solution supplier.
6. Aggregate node scores by chain before selecting the primary path. Preserve close alternatives for diversified enterprises.

Required fields:

- `enterprise_resolution`: input name, canonical name, enterprise ID, and candidate count.
- `enterprise_profile`: registered industry, business scope, introduction, business products, and tags.
- `primary_position`: status, confidence, chain, L2, L3, L5, full path, chain score, node score, evidence sources, and optional project anchor.
- `chain_ranking`: cross-chain comparison and each chain's best L5 node.
- `node_ranking`: candidate L2/L3/L5 paths with role adjustment and evidence matches.
- `evidence_summary`: product availability, nested interface errors, signal counts, and representative evidence.
- `positioning_boundary`: multi-business and non-exclusive classification explanation.

## Commands

Professional industry-chain analysis report:

```bash
python scripts/compose_industry_report.py \
  --chain "智能汽车" \
  --node "自动驾驶" \
  --project-root /path/to/industry-chain-map \
  --project-chain "智能网联汽车" \
  --project-node "自动驾驶" \
  --market-context /tmp/smart-car-market-context.json \
  --output /tmp/smart-car-chain-analysis-report.json
```

Specified enterprise-node report, separate from industry-chain analysis:

```bash
python scripts/enterprise_node_report.py \
  --chain "智能汽车" \
  --node "自动驾驶" \
  --path "智能汽车产业链>智能化系统>自动驾驶" \
  --enterprise "安徽中科星驰自动驾驶技术有限公司" \
  --key-type name \
  --project-root /path/to/industry-chain-map \
  --project-chain "智能网联汽车" \
  --project-node "自动驾驶" \
  --output /tmp/smart-car-enterprise-node-report.json
```

Enterprise-name positioning across all project chains:

```bash
python scripts/enterprise_chain_positioning.py \
  --enterprise "深圳市汇川技术股份有限公司" \
  --project-root /path/to/industry-chain-map \
  --output /tmp/enterprise-chain-positioning.json
```

Render either JSON:

```bash
python scripts/render_report.py --input /tmp/smart-car-chain-analysis-report.json --output /tmp/smart-car-chain-analysis-report.html
python scripts/render_report.py --input /tmp/smart-car-enterprise-node-report.json --output /tmp/smart-car-enterprise-node-report.md
```

## Quality gate

Before claiming an industry-chain analysis report is complete, confirm the rendered report contains:

- `L1-L5 层级口径说明`
- `项目图谱口径`
- `项目节点映射`
- `智能网联汽车产业链图谱` or equivalent project-style graph heading
- `产业链结构`
- `层级结构分析`
- `分析框架`
- A mapped L5 node name rather than only a generic node such as `自动驾驶`, when a node is specified.

And confirm it does not contain:

- `挂链总览`
- `项目已有候选挂链/锚点`
- `候选企业`
- `证据化判断`
