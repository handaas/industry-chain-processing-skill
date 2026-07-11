# ES Condition Generation And Relevance Tuning

## Source-backed method

The condition generator adapts established Elasticsearch and open-source search relevance practices to the HandaaS high-screen condition-group contract:

- Elasticsearch bool query: separate mandatory filters, optional evidence, and exclusions. https://www.elastic.co/guide/en/elasticsearch/reference/8.19/query-dsl-bool-query.html
- Elasticsearch multi-match query: search the same intent across multiple fields and compare field strategies. https://www.elastic.co/guide/en/elasticsearch/reference/8.19/query-dsl-multi-match-query.html
- Elasticsearch rank evaluation: maintain rated documents and compare Precision@K, MRR, and DCG between query versions. https://www.elastic.co/guide/en/elasticsearch/reference/8.19/search-rank-eval.html
- Elasticsearch search-time synonyms: manage domain synonyms without expanding every query blindly. https://www.elastic.co/guide/en/elasticsearch/reference/8.19/search-with-synonyms.html
- Quepid: make search relevance changes repeatable through query sets, judgments, and regression comparison. https://github.com/o19s/quepid
- OpenSearch Search Relevance Workbench: manage search configurations, query sets, judgments, and parameter optimization as reusable resources. https://github.com/opensearch-project/search-relevance

## Mapping To HandaaS High-Screen

HandaaS condition groups do not expose native Elasticsearch boosts, `_name`, `minimum_should_match`, `_rank_eval`, or analyzer configuration. Use these equivalents:

| Elasticsearch practice | HandaaS/Skill equivalent |
| --- | --- |
| `bool.filter` | `operStatus_v2`, `enterpriseType`, capital, explicit region, and reliable `industriesV2` in top-level `must` |
| negative clauses | field-level `nin/neq` directly inside `must`; top-level `must_not` is ignored by HandaaS high-screen |
| `minimum_should_match` | Put identity, business evidence, and strong evidence in separate top-level `must` groups; each internal `should` group must hit at least one field |
| named queries | Stable route IDs such as `industry_business_keyword` and `registration_scope_precision` |
| field boosts | Route priority plus multi-route consensus score before evidence review |
| `multi_match` field strategies | Separate business-keyword, registration-scope, and optional website routes instead of one oversized OR group |
| search-time synonyms | Node-specific exact/supporting profiles and project condition keywords |
| `_rank_eval` | `tune_search_conditions.py` with labels, project anchors, Precision@K, MRR, DCG, evidence precision, and baseline comparison |

## Default Route Matrix

Strict mode requires two evidence groups for every generated route:

1. A business group: either `businessKeywords`, or `business/desc`.
2. A strong group: at least one of recruiting, patent, or bidding fields.

Routes:

1. `industry_business_consensus`: reliable industry + business keywords + business scope/profile + strong evidence.
2. `industry_registration_scope`: active legal entity + reliable industry + business scope/profile + strong evidence.
3. `industry_business_keyword`: active legal entity + reliable industry + business keywords + strong evidence.
4. `business_consensus_precision`: business keywords + business scope/profile + strong evidence without industry hard filtering.
5. `registration_scope_precision`: business scope/profile + strong evidence without industry hard filtering.
6. `business_keyword_precision`: business keywords + strong evidence without industry hard filtering.
7. `web_presence_recall`: balanced-mode fallback using website fields + strong evidence.
8. `project_seed`: representative-company name resolution, always followed by enterprise evidence review.

Do not merge all business, website, recruiting, patent, and bidding fields into one large OR group. That removes the minimum evidence boundary and makes unrelated companies pass on a single weak field.

## Judgment Dataset

Use `assets/search-tuning-labels.example.json` as the schema:

- `positive_enterprises`: confirmed target-node enterprises.
- `negative_enterprises`: known false positives or adjacent-node enterprises.
- `ratings`: optional graded relevance from `0` to `3`.
  - `0`: unrelated or conflicting.
  - `1`: adjacent capability, not suitable for direct linking.
  - `2`: relevant supplier/product participant.
  - `3`: direct representative enterprise for the L5 node.

Project representative companies are recall anchors, not ground-truth confirmation labels. Keep operator-reviewed labels in a separate file under the project data boundary.

## Evaluation Metrics

- Route total: detects zero recall and runaway candidate pools.
- Anchor recall: whether project representative enterprises appear in sampled ES results.
- Precision@10: relevant judged enterprises divided by returned enterprises in the first 10, treating unlabeled results as not yet relevant.
- Judged precision: relevant enterprises divided only by judged enterprises; always report judgment coverage beside it.
- MRR: position of the first relevant judged enterprise.
- DCG@10: rewards highly relevant enterprises near the top.
- Evidence precision: confirmed enterprises divided by evidence-reviewed enterprises.
- Noise rate: rejected enterprises divided by evidence-reviewed enterprises.
- Strong-source coverage: proportion with patent, bidding, or enterprise-business evidence.
- Route Jaccard overlap: identifies redundant route combinations.
- Unique contribution: enterprises supplied only by one field strategy.

Do not accept a condition change when only the total count improves. Require either better labeled relevance, better evidence precision, recovery of a missing representative enterprise, or a documented recall/precision tradeoff.

## Iteration Order

1. Lock a judgment set for the node before changing keywords.
2. Generate strict routes and record the baseline JSON.
3. Inspect zero-recall routes for malformed node variants or missing synonyms.
4. Inspect low-precision routes for generic terms, adjacent products, trade/repair/training noise, or incorrect industry paths.
5. Add exclusions to the field where the noise occurs; do not globally exclude generic registered-scope verbs.
6. Compare the new output with `--baseline`.
7. Run enterprise evidence review on the top consensus candidates.
8. Promote a condition to operator-confirmed only after representative recall and precision remain stable across reruns.

## Commands

Generate the route matrix:

```bash
python scripts/build_condition.py \
  --chain "工业母机" \
  --node "伺服驱动器" \
  --path "工业母机>上游：核心零部件与基础材料>伺服系统>伺服驱动器" \
  --precision strict \
  --explain
```

Evaluate with judgments and MCP evidence:

```bash
python scripts/tune_search_conditions.py \
  --config /path/to/handaas.config.json \
  --chain "工业母机" \
  --node "伺服驱动器" \
  --path "工业母机>上游：核心零部件与基础材料>伺服系统>伺服驱动器" \
  --project-root "$INDUSTRY_CHAIN_PROJECT_ROOT" \
  --labels /path/to/servo-labels.json \
  --page-size 20 \
  --pages 2 \
  --with-evidence \
  --output /tmp/servo-search-evaluation.json
```

Compare a new condition version:

```bash
python scripts/tune_search_conditions.py \
  --config /path/to/handaas.config.json \
  --chain "工业母机" \
  --node "伺服驱动器" \
  --labels /path/to/servo-labels.json \
  --baseline /tmp/servo-search-evaluation.json \
  --output /tmp/servo-search-evaluation-v2.json
```
