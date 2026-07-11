# HandaaS Industry Chain Processing Skill — Codex Project Memory

This file is the repository-level operating contract for future Codex sessions. Read it before modifying the Skill, scripts, reports, tests, or documentation.

## Mission

Maintain an open-source Codex-compatible Skill for professional Chinese industry-chain analysis, project graph reuse, enterprise discovery/linking, enterprise-to-chain positioning, policy analysis, ES relevance tuning, and commercial HTML/Markdown reports.

- Repository: `https://github.com/handaas/industry-chain-processing-skill`
- Companion MCP: `https://github.com/handaas/industry-chain-mcp-server`
- User-facing invocation: `旷湖产业链分析`
- Skill package: `industry-chain-processing/`
- Skill contract: `industry-chain-processing/SKILL.md`

## Architectural boundaries

1. The MCP is the HandaaS data-access layer and exposes existing HandaaS interfaces only.
2. This Skill owns industry ontology, project graph reuse, keyword profiles, ES condition plans, relevance evaluation, evidence scoring, node linking, policy synthesis, and report composition.
3. Enterprises are linked records attached to L5 nodes. They are never children in the industry graph.
4. Pure industry-chain analysis reports must not contain candidate enterprises, linking decisions, evidence debug data, or enterprise-link records.
5. Enterprise linking, enterprise positioning, and specified enterprise-node analysis are separate workflows and separate reports.
6. Do not add dependencies unless they are required for a deterministic integration; most scripts should remain standard-library compatible. MCP connectivity uses `mcp` and `httpx`.

## Ontology and project-context rules

- Reuse an available `industry-chain-map` project before inventing a new graph.
- Project-root resolution order: CLI `--project-root`, `INDUSTRY_CHAIN_PROJECT_ROOT`, `INDUSTRY_CHAIN_MAP_ROOT`, then generic sibling discovery.
- Prefer `.data/industry-chain-archive.sqlite`; fall back to `src/data/industries/*.json`.
- Preserve the project graph's L1/L2/L3/L5 structure.
- L4 is an interpretation/compatibility layer used in report definitions; do not fabricate L4 graph nodes when the project does not store them.
- L5 is the enterprise-linking target.
- Reuse saved node IDs, paths, condition groups, condition keywords, and operator-confirmed project conditions.
- Existing representative enterprises/project seeds are recall anchors, not automatic confirmation evidence.
- A report graph is valid only when L2/L3/L5 counts are all positive and every displayed L2/L3 branch has children. Empty project graphs must be reconstructed from value-chain data or the generated fallback ontology; if still invalid, abort report generation.

## MCP integration

Official MCP project: `https://github.com/handaas/industry-chain-mcp-server`.

Configuration precedence:

1. `INDUSTRY_CHAIN_MCP_TOKEN` / `INDUSTRY_CHAIN_MCP_URL`
2. Config `mcp.url` / `mcp.token`
3. Local direct HandaaS/high-screen config when MCP is unavailable or `--local` is explicit

Remote token mode must not require local `integrator_id`, `secret_id`, `secret_key`, or per-product configuration. `scripts/mcp_client.py ping` performs a real MCP connection/tool-list initialization; it is not a config-only check.

Use only HandaaS wrapper tools, including enterprise search/profile/tags/business, supply-chain downstream products/enterprises, advanced filters, patents, bidding, and policies. If custom workflow tools appear, update/restart the MCP service.

Current precision boundary:

- Remote MCP supports reports, enterprise positioning, evidence review, policy analysis, and keyword candidate recall.
- When Remote MCP does not expose the full condition-group high-screen product, mark recall as `precision_limited` / `handaas_mcp_keyword_fallback`.
- `--require-es` must reject keyword fallback.
- Strict ES acceptance uses configured `high_screen` execution.

## Stable public HandaaS product IDs

These are platform identifiers, not secrets. Keep README, `assets/config.example.json`, references, and tests synchronized.

| Alias | Product ID |
| --- | --- |
| 工商照面 | `66dbccbec7a7e3460f5e613f` |
| 企业简介 | `6682b0b370f56cb7d77701e0` |
| 企业业务 | `66e55613ae988a28c6db9259` |
| 企业标签 | `669e531ce1fd7bff82321d8d` |
| 招聘明细 | `66b338e274bf098447db7f09` |
| 知识产权统计 | `66a0e1e7983134b5bb828503` |
| 企业招投标信息 | `66bf124bf134a4c21b4fc2fa` |
| 完整高筛企业名单 | `690dcb1b9c9dc8d0ff3c40eb` |

Account URLs, integrator IDs, secret IDs, secret keys, tokens, and signatures remain private local configuration.

## ES condition generation rules

- Source of truth: `scripts/build_condition.py` and `references/enterprise-search-rules.md`.
- Build field-specific keyword profiles from chain role, L2/L3/L5 path, exact product terms, supporting terms, project keywords, and noise terms.
- Respect HandaaS field keyword limits.
- Top-level HandaaS condition groups execute `must` and `should`; top-level Elasticsearch-style `must_not` is ignored.
- Place exclusions directly in top-level `must` as field-level `nin` / `neq`.
- Emulate `minimum_should_match` by using separate required `must` groups with internal `should` alternatives.
- Keep named recall routes stable so metrics and regressions remain comparable.
- Prefer consensus routes combining industry, business keywords, registration scope/description, and strong evidence.
- Do not broaden exact product terms merely to increase candidate totals.

Current strict route families include industry/business consensus, industry/registration scope, industry/business keyword, business consensus, registration-scope precision, and business-keyword precision. Business-keyword-only routes are noisier and must not dominate final ranking.

## Relevance tuning

Source of truth: `scripts/tune_search_conditions.py` and `references/es-relevance-tuning.md`.

- Maintain positive, negative, and graded enterprise judgments.
- Compare Precision@K, judged precision, MRR, DCG, anchor recall, route overlap, unique contribution, evidence confirmation, business match, and noise.
- Store stable route IDs and compare every keyword/industry/exclusion change with a baseline.
- Candidate totals alone are not a quality metric.
- Project seeds improve recall but do not count as independent enterprise evidence.

## Enterprise evidence and linking

Source of truth: `scripts/link_enterprises.py`, `references/evidence-scoring.md`, and `references/business-evidence-probing.md`.

Core evidence products:

- 工商照面
- 企业简介
- 企业标签
- 专利搜索
- 企业招投标信息

`企业业务` is optional strong evidence because real availability can vary by enterprise/account. Do not make it a hard gate.

Empirical known-case baseline:

- Stable business-fit combination: 工商照面 + 企业简介 + 企业标签 + 专利搜索 + 企业招投标信息.
- Lean combination: 企业标签 + 专利搜索 + 企业招投标信息.
- Business fit and strict link confirmation are different decisions.

Decision contract:

- `business_fit=matched`: score >= 50, at least two independent sources, no conflict.
- `decision=confirmed`: score >= 65, at least two independent sources, at least one strong source, no conflict.
- Strong sources: 企业业务、专利搜索、企业招投标信息.
- Medium sources: 企业标签、企业简介、工商照面.
- Unavailable products are evidence gaps; continue remaining calls and preserve exact `evidence_errors`.
- Patent search by company must use enterprise name with `keywordType=申请人`, not enterprise `nameId`.

## Report contracts

### Professional industry-chain report

Fixed reader-facing structure:

1. 报告摘要
2. 产业定义与 L1/L2/L3/L4/L5 口径
3. 产业发展环境 when authoritative evidence exists
4. 产业链全景图谱
5. 价值环节深度解析
6. 关键节点与产品技术体系
7. 价值传导与协同关系
8. 产业结构特征

Do not include conclusions/recommendations, enterprise linking, raw JSON, internal scores, tool status, input parameters, or execution summaries.

Commercial prose must not expose process language such as “联网收集”, “用于增强摘要”, “Skill 生成”, “未传入资料”, or tool-call decisions. State sourced industry facts and analysis directly.

Web research is allowed for current policy, market, technology, commercialization, and regulatory context. Prefer authoritative sources and retain source, URL, and date. Never invent current facts.

### Enterprise outputs

- Single-node linking, whole-chain linking, enterprise positioning, and specified enterprise-node analysis must produce standalone HTML or Markdown plus structured JSON unless the user explicitly requests JSON only.
- Keep `confirmed`, `uncertain`, and `rejected` records visibly separated.
- Enterprise reports may contain evidence and linking decisions; pure industry reports may not.

## Script ownership map

- `compose_industry_report.py`: pure professional industry-chain report payload.
- `render_report.py`: commercial HTML/Markdown rendering.
- `build_condition.py`: keyword profiles, condition groups, recall routes.
- `tune_search_conditions.py`: labeled ES relevance evaluation.
- `link_enterprises.py`: one-node candidate recall and evidence review.
- `link_chain_nodes.py`: bounded/resumable whole-chain L5 orchestration.
- `enterprise_chain_positioning.py`: enterprise name to ranked chain/L2/L3/L5 positions.
- `enterprise_node_report.py`: specified enterprise-node fit analysis.
- `policy_analysis.py`: HandaaS policy + external context synthesis.
- `probe_business_evidence.py`: known-case interface ablation and combination evaluation.
- `mcp_client.py`: Remote/local Streamable HTTP MCP connection and calls.
- `project_context.py`: graph/archive discovery and reuse.
- `validate_config.py`: redacted configuration validation.

## Security and generated artifacts

- Never print or commit tokens, credentials, signatures, signed requests, customer lists, or raw private evidence.
- Redact URL query tokens and secret-like mapping keys.
- Real configuration belongs in environment variables or the current user's `.industry-chain-processing/handaas.config.json`; use `references/os-operations.md` to create it on macOS/Linux or Windows.
- `output/`, `.omx/`, `.playwright-cli/`, caches, and local config files are ignored.
- Product IDs may be committed because they are stable public identifiers.

## Required verification

Run before claiming completion:

```bash
python -m unittest discover -s tests -v
ruff check industry-chain-processing/scripts tests
python -m compileall -q industry-chain-processing/scripts tests
# Also run the quick_validate.py supplied by the installed skill-creator.
git diff --check
```

Current expected baseline is at least 63 unit tests. For MCP changes, also run `mcp_client.py ping` and `list-tools`. For real-query changes, inspect actual results rather than treating a successful HTTP response as acceptance.

## Documentation and release rules

- README is user-facing: installation, MCP connection, workflows, outputs, examples, and troubleshooting.
- Installation/configuration guidance must detect macOS/Linux versus Windows PowerShell and use `references/os-operations.md`. Prefer repository-relative script paths and executable-discovery commands over fixed Unix home paths or drive-specific paths.
- Keep detailed contributor workflow in `CONTRIBUTING.md` and security policy in `SECURITY.md`; link them from README without duplicating full sections.
- `tests/` stays committed for CI but is outside the installed `industry-chain-processing/` Skill directory.
- Keep `SKILL.md` concise and under 500 lines; move detail into direct references.
- The official MCP project link must remain visible in `SKILL.md`, README, and `references/local-enterprise-config.md`.
- Commit messages use the active Codex environment's Lore decision-record format when required.
- Push target: `handaas/main` for `handaas/industry-chain-processing-skill`.

## Known limitations

- Remote keyword recall is not equivalent to full high-screen ES execution.
- Product availability differs by account; preserve exact product/tool error identity.
- Relevance metrics depend on judgment coverage; low-coverage Precision@K must be reported with judged precision/coverage.
- Project graph quality bounds report quality; do not silently replace project ontology with generic output.
- Never render `暂无 L5 节点` cards or an empty graph page in a professional industry-chain report.
