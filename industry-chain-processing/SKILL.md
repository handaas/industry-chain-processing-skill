---
name: industry-chain-processing
description: Use for Chinese industry-chain analysis and enterprise discovery when users say “使用旷湖产业链分析...”, “旷湖产业链分析”, or ask to analyze an industry/sector, find relevant companies, classify companies into an industry chain, evaluate招商线索, verify enterprise evidence, produce enterprise-linking recommendations, or generate static HTML/Markdown reports for industry-chain results. The user should not need to provide internal layer names, interface details, search parameters, or credential details; infer the analysis structure and search strategy internally, then use local configured enterprise data tools when needed.
---

# 旷湖产业链分析

## User-facing contract

Treat “旷湖产业链分析” as the user-facing invocation phrase for this skill. `industry-chain-processing` is only the internal package name.

When this skill is active:

1. Do not ask the user to provide internal layer labels, search parameters, API fields, credential details, or evidence source names.
2. Accept natural business goals such as “分析低空经济”, “找 eVTOL 相关企业”, “判断这些企业属于哪些环节”, or “做招商线索挖掘”.
3. Infer the industry boundary, refined segments, search targets, keywords, exclusions, and evidence checks yourself.
4. Hide implementation details by default. Explain results in business language; show raw JSON or command details only when the user asks, when debugging, or when a dry-run artifact is useful.
5. Use local configuration and bundled scripts only; do not assume any hosted platform exists.
6. Never print `secret_id`, `secret_key`, signatures, tokens, or raw signed requests.
7. Prefer dry-run before real paid or credentialed API calls unless the user explicitly asks for a real query and config is valid.

## Required references

Load only what the task needs:

- Broad industry analysis or enterprise discovery: read `references/analysis-playbook.md`.
- Internal chain normalization: read `references/ontology-contract.md`.
- Local config or credential issues: read `references/local-enterprise-config.md`.
- Search strategy construction: read `references/enterprise-search-rules.md`.
- Candidate scoring and recommendations: read `references/evidence-scoring.md`.
- HTML/Markdown report generation: read `references/report-output.md`.

## Internal workflow

1. **Understand the business goal**
   - Determine whether the user wants industry mapping, enterprise discovery, company classification, evidence verification, or strategy advice.
   - If the request is broad, make reasonable assumptions and state them briefly. Do not block on missing internal terminology.

2. **Build the analysis map**
   - Create an internal hierarchy: industry theme -> value segment -> business module -> refined product/technology/service/capability target.
   - Keep companies out of the hierarchy; companies are linked records.
   - Select the most commercially useful refined targets for enterprise search.

3. **Create the search strategy internally**
   - Expand product names, synonyms, application scenarios, delivery verbs, equipment verbs, software/platform verbs, recruiting terms, patent terms, bidding terms, and exclusion terms.
   - Prefer `scripts/build_condition.py` for deterministic baseline search JSON when a refined target is known.
   - Add user-provided clues when present, but do not require them.

4. **Use local enterprise data only when appropriate**
   - Validate config first with `scripts/validate_config.py`.
   - Use `scripts/link_enterprises.py` for end-to-end candidate discovery and optional evidence checks.
   - Use `scripts/enterprise_search_preview.py` or `scripts/evidence_call.py` only for debugging or specialized calls.
   - If config is missing or placeholders remain, provide a dry-run result and a concise setup instruction.

5. **Score and explain**
   - Classify candidates as `confirmed`, `uncertain`, or `rejected`.
   - Base decisions on evidence strength, not just name similarity.
   - Explain in operator-facing terms: why the company matches, what evidence was found, what still needs review.

6. **Generate reports when useful**
   - Default to concise tables in the chat.
   - If the user asks for 展示、报告、HTML、页面、材料、交付, create structured result JSON and run `scripts/render_report.py`.
   - Prefer standalone HTML for sharing and Markdown for knowledge-base/wiki editing.

## Script quick reference

Use these internally or for advanced debugging:

```bash
python scripts/validate_config.py --allow-placeholders
python scripts/build_condition.py --chain "低空经济" --node "eVTOL整机制造" --path "低空经济产业链>航空器制造>eVTOL整机制造"
python scripts/enterprise_search_preview.py --filter-file condition.json --dry-run
python scripts/evidence_call.py --product 工商照面 --keyword "企业ID或企业名称" --key-type nameId --dry-run
python scripts/link_enterprises.py --chain "低空经济" --node "eVTOL整机制造" --dry-run
python scripts/render_report.py --input assets/report.example.json --output /tmp/industry-report.html
```

## Output guidance

Default output should be business-readable:

- `industry_map`: concise industry structure and priority segments.
- `search_strategy`: natural-language description of how companies were searched or would be searched.
- `candidates`: total, sample names, IDs when available.
- `evidence`: strong / medium / weak signals summarized in plain language.
- `decision`: `confirmed`, `uncertain`, or `rejected`.
- `next_actions`: one to three concrete follow-ups.
- `report_path`: generated HTML or Markdown path when a report is requested.

If API calls cannot run, state the missing config or network error and provide a dry-run command or installation/configuration step.
