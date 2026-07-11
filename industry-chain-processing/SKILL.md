---
name: industry-chain-processing
description: Use for Chinese industry-chain analysis with project-graph-aware L1/L2/L3/L5 ontology reuse, HandaaS ES high-screen condition generation and relevance tuning, business-keyword/registration-scope enterprise matching, evidence verification, regional policy analysis, enterprise-name-to-chain positioning, and professional HTML/Markdown reports. Trigger when users ask for “旷湖产业链分析”, 专业产业链分析报告, ES/高筛条件生成或准确性调优, 企业筛选结果过宽/过窄, 招商线索, 企业挂链, 某企业所属产业链/节点, 各地产业政策, MCP联调, or 指定企业节点分析. Infer project nodes, route combinations, MCP tools, evidence products, labels, metrics, policy regions, and report parameters automatically.
---

# 旷湖产业链分析

## User-facing contract

Treat “旷湖产业链分析” as the user-facing invocation phrase. `industry-chain-processing` is only the internal package name.

When this skill is active:

1. Do not ask the user for internal layer labels, MCP tool names, API fields, product IDs, credential details, evidence source names, or search parameters.
2. Accept natural goals such as “分析低空经济”, “找 eVTOL 企业”, “判断这些企业挂到哪里”, “分析某企业属于哪个产业链环节”, “生成智能汽车专业产业链分析报告”, or “分析某企业是否适合挂到自动驾驶节点”.
3. Prefer project context before inventing structure whenever a current `industry-chain-map` project is available. Reuse its L1/L2/L3/L5 graph and node records for industry-chain analysis reports.
4. Keep enterprises out of the graph hierarchy. Enterprises are linked records attached to L5 nodes, never graph children.
5. Prefer MCP for HandaaS enterprise evidence when `INDUSTRY_CHAIN_MCP_URL`, `INDUSTRY_CHAIN_MCP_TOKEN`, or config `mcp.url/mcp.token` exists. Precise enterprise linking requires the full `high_screen` ES interface; when Remote MCP exposes only keyword search, label it as a recall preview and use local `high_screen` for the final candidate pool.
6. Treat MCP as a HandaaS interface-wrapper layer only. Do not expect MCP-side tools for building conditions, scoring, linking, or report composition; those are local skill workflows.
7. For professional industry-chain analysis reports, allow web collection for the report abstract and “产业背景与分析依据” when network tools are available. Prefer official/authoritative sources; never invent current market or policy facts.
8. For regional policy analysis, combine HandaaS policy MCP tools (`policy_bigdata_policy_search`, `policy_bigdata_policy_info`, `policy_bigdata_approved_project_stats`) with web search/browsing when available. Keep source, URL, region, and date for every web policy item.
9. Never print `secret_id`, `secret_key`, signatures, tokens, or raw signed requests.
10. Prefer dry-run before real paid/credentialed API calls unless the user clearly asks for real querying and config is valid.
11. Commercial report prose must only state industry facts, research evidence, hierarchy definitions, and analytical findings. Never expose collection/generation process language such as “联网收集”, “用于增强摘要”, “未传入资料”, “Skill 生成”, input parameters, tool calls, or internal workflow decisions.
12. Professional industry-chain reports must follow the fixed research structure: 报告摘要 -> 产业定义与层级口径 -> 产业发展环境 -> 产业链全景图谱 -> 价值环节深度解析 -> 关键节点与产品技术体系 -> 价值传导与协同关系 -> 产业结构特征. Omit only the development-environment chapter when no authoritative evidence is available; do not replace these chapters with generic priority cards or execution summaries.
13. Enterprise-chain positioning, specified enterprise-node analysis, single-node enterprise linking, and whole-chain node linking must produce a standalone HTML or Markdown report in addition to structured JSON unless the user explicitly requests JSON only. Use each script's `--report-output`; do not require a second manual rendering step.

## MCP service entry

- Official project: [handaas/industry-chain-mcp-server](https://github.com/handaas/industry-chain-mcp-server).
- Open the MCP project README when the user needs local deployment, environment variables, client configuration, tool inventory, or troubleshooting.
- For Remote MCP, prefer the platform-issued token or complete MCP URL; do not require cloning the MCP repository.
- For local MCP, guide the user to clone the official project above, copy `.env.example` to `.env`, start `streamable-http`, and set `INDUSTRY_CHAIN_MCP_URL` to the local `/mcp` endpoint.
- Detect macOS/Linux versus Windows PowerShell and use `references/os-operations.md`; do not present a Unix home path or shell command as universal configuration guidance.
- After either setup path, run `scripts/mcp_client.py ping` and `scripts/mcp_client.py list-tools` before the first real query.

## Load references only when needed

- Broad industry analysis or enterprise discovery: `references/analysis-playbook.md`.
- Project graph / node records / current app reuse: `references/project-context.md`.
- Internal ontology normalization: `references/ontology-contract.md`.
- MCP or local credential/config issues: `references/local-enterprise-config.md`.
- Installation, environment variables, local paths, and MCP startup by operating system: `references/os-operations.md`.
- Regional policy analysis: `references/policy-analysis.md`.
- Search strategy construction: `references/enterprise-search-rules.md`.
- ES condition relevance tuning, labels, metrics, and baseline comparison: `references/es-relevance-tuning.md`.
- HandaaS business-interface dimension probing and evidence combinations: `references/business-evidence-probing.md`.
- Candidate scoring and 挂链 decisions: `references/evidence-scoring.md`.
- HTML/Markdown/professional report generation: `references/report-output.md`.

## Intent router

Choose the smallest complete workflow:

| User intent | Internal workflow |
| --- | --- |
| 只要产业链结构/策略 | Build business map from `analysis-playbook` + `ontology-contract`; no network required. |
| 各地政策、区域政策、产业政策分析 | Load `policy-analysis`; use web search for official/current context, run `policy_analysis.py`, render with `render_report.py`. |
| 单个 L5 节点找企业、招商线索、企业挂链 | Load `enterprise-search-rules` + `evidence-scoring`; run `link_enterprises.py --report-output ...`. Use full high-screen ES for candidates and MCP/local HandaaS wrappers for evidence. |
| 整条产业链各节点企业挂链 | Resolve project L5 nodes, dry-run the complete ES plan, then run bounded batches with evidence, resume support, and `link_chain_nodes.py --report-output ...` for the aggregate report. |
| ES 条件不准、结果过宽/过窄、需要调优验证 | Load `es-relevance-tuning`; lock labels, run `tune_search_conditions.py`, compare route metrics and evidence precision, then revise profiles/exclusions. |
| 哪些 HandaaS 接口/维度更能判断企业业务 | Load `business-evidence-probing`; prepare known positive and adjacent-negative cases, run `probe_business_evidence.py`, and compare business-fit versus strict-link metrics. |
| 专业产业链分析报告、图谱层级展示、HTML、Markdown | Load `project-context` + `report-output`; run `compose_industry_report.py --chain ...` -> `render_report.py`. Do not run enterprise linking for this report. |
| 只输入企业名称，判断所属产业链/环节 | Load `project-context` + `evidence-scoring`; run `enterprise_chain_positioning.py --enterprise ... --report-output ...`. Scan all project chains and return primary + alternative L2/L3/L5 positions plus the report path. |
| 指定企业是否适合某节点 | Load `project-context` + `evidence-scoring`; run `enterprise_node_report.py --report-output ...` and return the fit decision plus report path. |
| MCP/接口/产品不存在/传参错误 | Load `local-enterprise-config`; use `mcp_client.py list-tools`, `evidence_call.py --dry-run`, then report the exact missing product/tool/parameter. |

## Golden path for industry-chain analysis reports

1. **Resolve project context first**
   - Use `--project-root`, then `INDUSTRY_CHAIN_PROJECT_ROOT`, then `INDUSTRY_CHAIN_MAP_ROOT`, then the known sibling path if present.
   - Prefer `.data/industry-chain-archive.sqlite`; fall back to `src/data/industries/*.json`.
   - Fuzzy-map user wording to the canonical chain and L5 target. Example: “智能汽车 / 自动驾驶” should map to project chain “智能网联汽车” and L5 nodes such as “自动驾驶解决方案”.

2. **Normalize the analysis target**
   - Use project L1/L2/L3/L5 as the report口径 when available.
   - If the user gives a broad or non-standard node, map it to the closest L5 node and state the mapping briefly.
   - If no project context exists, fall back to the generated ontology and clearly mark it as non-project fallback.

3. **Collect external context for the report abstract when useful**
   - For a professional/commercial industry-chain analysis report, use web search/browsing if available to collect 3-5 recent or authoritative items about policy, market size, technology route, commercialization progress, or regulatory background.
   - Prefer government, industry association, research institute, exchange/filing, company official, or reputable news sources. Record `topic`, `finding`, `source`, `url`, and `date`.
   - Pass the findings with `--market-context <json>` or repeated `--market-note "topic|finding|source|url|date"`.
   - If network is unavailable or the user requests offline work, continue from project graph data and do not fabricate external facts.

4. **Compose hierarchy and analysis only**
   - Run `scripts/compose_industry_report.py --chain ... --node ...` for professional industry-chain analysis reports.
   - Do not include enterprise candidates, 挂链总览, evidence summaries, or existing enterprise-link anchors in this report.
   - Build dedicated report fields for `industry_definition`, `segment_analysis`, `key_node_system`, `value_flow`, and `structural_characteristics`; do not use `priority_segments`, high/medium labels, generic action cards, or execution-oriented summaries.

5. **Compose project-aware deliverables**
   - For professional industry-chain analysis reports, use `scripts/compose_industry_report.py` with project parameters when available.
   - For enterprise linking or 招商名单, use `scripts/link_enterprises.py` as a separate workflow.
   - For an enterprise name without a specified chain/node, use `scripts/enterprise_chain_positioning.py`; resolve the canonical enterprise, collect business/profile/tag/patent/bidding evidence, rank all project L5 nodes, and report the primary plus alternative industry-chain positions.
   - For a specified company/node, use `scripts/enterprise_node_report.py` as a separate workflow.
   - Required project-aware chain-analysis sections: professional report abstract; industry definition and detailed L1/L2/L3/L4/L5口径; policy/market/technology environment when evidence exists; project-style L2/L3/L5 graph; L2 value-segment analysis; L3/L5 product-technology system; inter-segment value flow; and evidence-backed structural characteristics.

6. **Render and report**
   - Render standalone HTML for commercial sharing and Markdown for knowledge-base/wiki reuse. Industry-chain analysis reports must use the research-report style template: A4-like pages, grey striped top rule, blue report banner, cover catalogue/scope sidebar, executive summary, L1-L5口径, graph, hierarchy analysis, and structural insights; no raw JSON, internal debug fields, interface status, empty tables, or enterprise-linking sections.
   - Write every visible heading, note, abstract, table caption, and source description as reader-facing research content. Describe policy environment, market evolution, technology routes, evidence sources, and structural findings directly; never describe how the Skill collected or generated them.
   - Return the file paths, canonical chain/node mapping, project graph source, and whether the report is project-backed or generated fallback.

## Golden path for enterprise linking

1. **Resolve the canonical target**
   - Map the request to the project L1/L2/L3/L5 path. L5 is the enterprise-link target; use L2 only to infer upstream, midstream, or downstream operating verbs.
   - Reuse active project condition keywords and operator-confirmed conditions. Do not promote project representative companies to confirmed links.

2. **Build field-valid ES routes**
   - Run `build_condition.py --precision strict --explain` and validate every field/operator against the HandaaS high-screen contract.
   - Separate exact product terms, supporting technical terms, role-specific action terms, recruiting terms, and field-scoped exclusions.
   - Generate consensus routes that require `businessKeywords` + `business/desc` + strong evidence, plus single-business-group routes for recall. Add industry variants only when L3/L5 semantics support a reliable `industriesV2` path.
   - Keep no-industry routes to recover enterprises whose industry label is missing or misclassified while preserving exact business + strong-evidence requirements.
   - Add project representative enterprises through the `project_seed` name-resolution route. Seeds are recall anchors only.

3. **Execute and deduplicate candidates**
   - For precise linking, execute all ES routes and merge by enterprise ID or normalized legal name.
   - Remote `enterprise_get_keyword_search` is a documented fallback when full ES is unavailable. Set `precision_limited=true`; never describe it as full high-screen execution.
   - Use `--require-es` for acceptance runs so keyword fallback fails explicitly.

4. **Review enterprise evidence**
   - Use the stable core combination: enterprise base + profile + tags + patent search by enterprise name/`申请人` + enterprise bidding information. Query enterprise business as optional strong evidence, never as a required product.
   - A project seed, company name, industry label, registered capital, or high-screen hit is not confirmation evidence.
   - Set `business_fit=matched` at score >= 50 with at least two independent sources and no conflict. This identifies likely business participation but does not automatically create a node link.
   - `confirmed` requires score >= 65, at least one strong source, at least two independent sources, and no conflict signal. Otherwise return `uncertain` or `rejected` with matched terms and source counts.

5. **Iterate per node**
   - Lock positive/negative/graded enterprise labels and run `tune_search_conditions.py`. Review Precision@10, MRR, DCG@10, anchor recall, evidence precision, noise rate, strong-source coverage, and route overlap.
   - Review candidate totals and rejected samples by recall route. Tighten exact terms, industry paths, or field-scoped exclusions when noisy; add synonyms only when representative companies or verified manufacturers are missing.
   - For an entire chain, use `link_chain_nodes.py` with role/node filters, bounded `--max-nodes`, per-node output files, and `--resume`. Use `--max-nodes 0` only when a complete-chain run is intended.

6. **Deliver the report**
   - Single-node linking reports must show the canonical path, route coverage, confirmed enterprises, manual-review enterprises, rejected enterprises, evidence-source counts, and decision reasons.
   - Whole-chain linking reports must summarize L5 node coverage and retain each node's confirmed/manual-review enterprises and evidence judgment.
   - Pass `--report-output <report.html|report.md>` during the analysis command. Return both JSON and report paths; never expose raw evidence payloads or internal workflow text in the report.

## Script quick reference

Use these internally or for advanced debugging:

```bash
python scripts/validate_config.py --allow-placeholders
python scripts/mcp_client.py ping
python scripts/mcp_client.py list-tools

python scripts/build_condition.py \
  --chain "低空经济" \
  --node "eVTOL整机制造" \
  --path "低空经济产业链>航空器制造>eVTOL整机制造"

python scripts/compose_industry_report.py \
  --chain "智能汽车" \
  --node "自动驾驶" \
  --project-root "$INDUSTRY_CHAIN_PROJECT_ROOT" \
  --project-chain "智能网联汽车" \
  --project-node "自动驾驶" \
  --market-note "政策背景|权威政策、市场或技术要点|来源名称|https://example.com|2026-01-01" \
  --output output/industry-chain-analysis.json

python scripts/policy_analysis.py \
  --chain "智能汽车" \
  --keyword "智能网联汽车 自动驾驶" \
  --region "国家部委" \
  --region "广东省" \
  --region "上海" \
  --policy-start "2025-01-01" \
  --web-context output/policy-web-context.json \
  --output output/policy-analysis.json

python scripts/enterprise_chain_positioning.py \
  --enterprise "深圳市汇川技术股份有限公司" \
  --project-root "$INDUSTRY_CHAIN_PROJECT_ROOT" \
  --output output/enterprise-chain-positioning.json \
  --report-output output/enterprise-chain-positioning.html

python scripts/link_enterprises.py \
  --chain "工业母机" \
  --node "伺服驱动器" \
  --path "工业母机>上游：核心零部件与基础材料>伺服系统>伺服驱动器" \
  --project-root "$INDUSTRY_CHAIN_PROJECT_ROOT" \
  --page-size 5 \
  --with-evidence \
  --require-es \
  --output output/servo-drive-enterprise-linking.json \
  --report-output output/servo-drive-enterprise-linking.html

python scripts/link_chain_nodes.py \
  --chain "工业母机" \
  --project-root "$INDUSTRY_CHAIN_PROJECT_ROOT" \
  --role upstream \
  --max-nodes 20 \
  --dry-run \
  --output output/industrial-machine-upstream-plan.json \
  --report-output output/industrial-machine-upstream-plan.html

python scripts/tune_search_conditions.py \
  --config "$INDUSTRY_CHAIN_CONFIG" \
  --chain "工业母机" \
  --node "伺服驱动器" \
  --path "工业母机>上游：核心零部件与基础材料>伺服系统>伺服驱动器" \
  --project-root "$INDUSTRY_CHAIN_PROJECT_ROOT" \
  --labels assets/search-tuning-labels.example.json \
  --with-evidence \
  --output output/servo-search-evaluation.json

python scripts/probe_business_evidence.py \
  --cases assets/business-evidence-cases.example.json \
  --max-combination-size 0 \
  --output output/business-evidence-probe.json

python scripts/enterprise_node_report.py \
  --chain "智能汽车" \
  --node "自动驾驶" \
  --path "智能汽车产业链>智能化系统>自动驾驶" \
  --enterprise "安徽中科星驰自动驾驶技术有限公司" \
  --key-type name \
  --project-root "$INDUSTRY_CHAIN_PROJECT_ROOT" \
  --project-chain "智能网联汽车" \
  --project-node "自动驾驶" \
  --output output/enterprise-node.json \
  --report-output output/enterprise-node.html

python scripts/render_report.py --input output/industry-chain-analysis.json --output output/industry-chain-analysis.html
python scripts/render_report.py --input output/enterprise-node.json --output output/enterprise-node.md
```

## Output guidance

Default output should be business-readable and concise:

- `industry_map`: project-aware or generated industry structure.
- `project_graph_summary`: canonical project chain, source, L2/L3/L5 counts when available.
- `node_mapping`: input chain/node -> canonical project chain/L5 node.
- `level_definitions`: detailed L1/L2/L3/L4/L5 interpretation口径.
- `market_context`: optional web-collected policy, market, technology, or commercialization context used to strengthen the report abstract.
- `project_graph_tree`: L1/L2/L3/L5 tree used by the static HTML graph display.
- `project_node_records`: node IDs, paths, condition keywords.
- `industry_definition`: industry object, value boundary, hierarchy system, graph coverage, and focus scope.
- `segment_analysis`: L2 functional positioning, L3 composition, representative L5 nodes, scale, and upstream/downstream linkage.
- `key_node_system`: L3 capability boundaries and representative L5 product/technology/service nodes.
- `value_flow`: value transfer relationships, content, and mechanisms between adjacent L2 segments.
- `structural_characteristics`: evidence-backed interpretation of topology, node concentration, integration pattern, and application closure.
- `primary_position`: enterprise's primary chain/L2/L3/L5 path, score, confidence, and evidence sources.
- `chain_ranking`: cross-chain comparison based on the strongest matching nodes.
- `node_ranking`: candidate L5 paths across all project chains.
- `evidence_summary`: availability, signal count, and representative evidence from existing HandaaS interfaces.
- `candidates` / `evidence` / `decision`: only for enterprise linking or specified enterprise-node reports, not for industry-chain analysis reports.
- `recall_routes`: field-specific business-keyword, registration-scope, optional website, operator-confirmed, or project-seed recall provenance.
- `routes` / `overlap` / `baseline_comparison`: ES condition tuning metrics and route comparison output.
- `review_score` / `evidence_source_count` / `strong_source_count`: enterprise-level review evidence for linking acceptance.
- `next_actions`: only for enterprise linking or specified enterprise-node reports, not for industry-chain analysis reports.
- `report_artifacts`: direct HTML/Markdown artifacts emitted by enterprise positioning, enterprise-node analysis, single-node linking, or whole-chain linking.
- `report_path`, `professional_report_path`, `enterprise_node_report_path`: generated artifacts retained for compatible integrations.
- `policy_query`, `regional_policy_analysis`, `policy_dimensions`, `policy_items`, `web_policy_context`: for regional policy analysis reports.

If API calls cannot run, state the exact missing config, missing product, MCP tool error, parameter validation error, or upstream network error. Provide a dry-run command or setup step without exposing secrets.
