---
name: industry-chain-processing
description: Use when generating Chinese industry-chain ontology, turning L5 product/technology/service nodes into Handaas or high-screen enterprise filters, querying local Handaas/high-screen APIs with user-owned credentials, validating candidate evidence, or producing enterprise-linking recommendations. Trigger for requests about 产业链生成、企业挂链、企业归位、高筛条件、Handaas/DAAS 企业查询、产业链企业研判, especially when the user wants a local GitHub-installed skill rather than a hosted platform.
---

# Industry Chain Processing

## Core contract

Use this skill as a local, installable workflow for industry-chain processing. Do not assume any hosted platform exists. Use the user's local configuration and bundled scripts.

1. Build ontology first; link enterprises later.
2. Keep enterprises out of the L1-L5 ontology tree.
3. Treat L5 as the smallest enterprise-linking target.
4. Build Handaas/high-screen filters from business intent, not only the node name.
5. Query candidate enterprises only through local user-owned credentials.
6. Never print `secret_id`, `secret_key`, signatures, tokens, or raw signed requests.
7. Classify candidate links as `confirmed`, `uncertain`, or `rejected` based on evidence strength.

## Workflow

1. **Understand the task**
   - For ontology generation, read `references/ontology-contract.md`.
   - For Handaas/high-screen config or credentials, read `references/handaas-config.md`.
   - For filter construction, read `references/high-screen-condition-rules.md`.
   - For candidate scoring, read `references/evidence-scoring.md`.

2. **Generate or normalize the ontology**
   - Output L1 → L2 → L3 → L5.
   - L5 nodes must be product, technology, service, material, equipment, platform, solution, or capability nodes.
   - Do not include company names as child nodes.

3. **Build an enterprise-linking condition for each L5 node**
   - Prefer `scripts/build_condition.py` for deterministic baseline filters.
   - Add user-provided keywords, industry boundaries, or exclude terms when supplied.
   - Keep the condition group as a raw JSON object; do not wrap it in `condition`, `filter`, `data`, or `query`.

4. **Call local APIs only when configured**
   - Validate config first with `scripts/validate_config.py`.
   - Use `scripts/high_screen_preview.py` for high-screen candidate lists.
   - Use `scripts/handaas_call.py` for Handaas/DAAS product calls.
   - Use `--dry-run` when checking request shape or when credentials are placeholders.

5. **Link enterprises**
   - Use `scripts/link_enterprises.py` to combine condition building, high-screen preview, and optional evidence calls.
   - Report total candidates, sample companies, evidence status, and recommended next action.

## Script quick reference

Run from the skill directory or pass absolute paths.

```bash
python scripts/validate_config.py --allow-placeholders
python scripts/build_condition.py --chain "低空经济" --node "eVTOL整机制造" --path "低空经济产业链>航空器制造>eVTOL整机制造"
python scripts/high_screen_preview.py --filter-file condition.json --dry-run
python scripts/handaas_call.py --product 工商照面 --keyword "企业ID或企业名称" --key-type nameId --dry-run
python scripts/link_enterprises.py --chain "低空经济" --node "eVTOL整机制造" --dry-run
```

## Output guidance

Return concise operator-facing results:

- `ontology`: L1-L5 tree or changed nodes.
- `condition`: high-screen condition JSON or saved path.
- `candidates`: total, sample names, IDs when available.
- `evidence`: strong / medium / weak signals.
- `decision`: `confirmed`, `uncertain`, or `rejected`.
- `next_actions`: one to three concrete follow-ups.

If API calls cannot run, state the missing config or network error and provide a dry-run command that the user can execute after configuration.
