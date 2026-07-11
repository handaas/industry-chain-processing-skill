# Internal Enterprise Search Rules

## Base condition

Always start with active legal entities:

```json
{
  "must": [
    {"operStatus_v2": [{"eq": [["营业"]]}]},
    {"enterpriseType": [{"neq": [["个体户"]]}]}
  ]
}
```

The current strict generator also uses `regCapitalRmb >= 10` as a minimal entity-quality boundary. Do not add phone, mobile, contact, or regional constraints unless the user explicitly requests them.

## Node semantics before keywords

Use the complete canonical path:

- L1 identifies the industry chain but must not directly force a national-industry classification.
- L2 determines the enterprise role: upstream uses `研发/生产/制造`, midstream uses `制造/集成/交付`, and downstream uses `运营/应用/服务`.
- L3 defines the capability or product family and supplies supporting terms.
- L5 supplies the exact product, technology, material, service, or solution terms.

Infer `industriesV2` only from clear L3/L5 semantics. A broad chain name such as `工业母机` must not classify every software or service node as manufacturing.

## Evidence groups

Internally build at least one business evidence `should` group across:

- `businessKeywords`
- `business`
- `desc`
- `domainTitle`
- `domainKeywords`
- `domainDesc`

Build a separate stronger evidence group across:

- `recruitingName`
- `recruitingDesc`
- `patentNameList`
- `biddingAnncTitleList`

Only use fields registered in `build_condition.py::FIELD_RULES`. Respect HandaaS keyword limits: business/patent/bidding fields use at most 10 values; domain/recruiting fields use at most 30 values.

In strict mode, require both the business evidence group and the strong evidence group. In balanced mode, merge them into one recall group and mark the lower precision in the result.

## Multi-route recall

One hard-filter condition is insufficient because national-industry tags and enterprise text coverage are incomplete. Use these routes:

1. `industry_business_consensus`: reliable `industriesV2` + `businessKeywords` + `business/desc` + strong evidence.
2. `industry_registration_scope`: reliable `industriesV2` + `business/desc` + strong evidence.
3. `industry_business_keyword`: reliable `industriesV2` + `businessKeywords` + strong evidence.
4. `business_consensus_precision`: `businessKeywords` + `business/desc` + strong evidence without inferred industry.
5. `registration_scope_precision`: `business/desc` + strong evidence without inferred industry.
6. `business_keyword_precision`: `businessKeywords` + strong evidence without inferred industry.
7. `web_presence_recall`: balanced-mode website fallback + strong evidence.
8. `operator_confirmed`: an active condition explicitly marked as operator-confirmed in the project archive.
9. `project_seed`: resolve representative-company display names to legal entities, then send them through the same evidence review.

Merge candidates by enterprise ID or normalized legal name and retain all recall-route IDs. Project seeds and high-screen hits remain weak recall provenance, not enterprise-node confirmation.

Read `es-relevance-tuning.md` before changing route combinations or accepting a new condition version. Use `tune_search_conditions.py`; do not tune from candidate totals alone.

## Keyword expansion

Use the full node path. Expand:

- product names and technical synonyms
- business scenarios
- delivery/action verbs: `建设`, `搭建`, `运维`, `实施`, `集成`, `托管`, `交付`
- equipment verbs: `生产`, `制造`, `研发`, `集成`
- software/platform verbs: `开发`, `实施`, `运维`, `SaaS`, `平台化`
- job titles, patent terms, bidding terms

Avoid standalone generic terms: `平台`, `系统`, `服务`, `软件`, `解决方案`, `上游`, `中游`, `下游`, `产业链`.

Put exclusions on the field where the noise occurs. For example, `维修` can be excluded from enterprise names, but generic `维修` must not be excluded from the full business scope because manufacturers commonly register installation and repair services. Use specific text exclusions such as `汽车维修`, `电机维修`, or `纯贸易`.

Put every field-level `nin` / `neq` clause directly in top-level `must`. HandaaS high-screen ignores top-level `must_not`; the validator rejects it and can migrate legacy groups only when every nested operator is already `nin` or `neq`.

## Review failures internally

- Zero recall: check representative enterprises and exact synonyms before broadening; preserve the strong-evidence requirement.
- Representative manufacturer missing: inspect industry misclassification and source-field coverage; recover it through the no-industry field routes or `project_seed`, not a global broad query.
- Over-broad recall: add a reliable industry route, tighten exact terms, and add field-scoped `nin/neq` clauses inside `must`.
- Noisy samples: add exclusions for unrelated industries, pure trade, training, consulting, repair, retail.
- Parameter error: simplify to base `must` + one evidence `should` + minimal field-level `nin/neq` clauses in `must`.
- Remote MCP keyword fallback: mark `precision_limited=true`; do not accept it as a precise ES acceptance result.
