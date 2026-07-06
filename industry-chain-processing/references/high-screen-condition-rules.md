# High-Screen Condition Rules

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

Do not add registered capital, phone, mobile, or contact constraints by default.

## Evidence groups

Build at least one business evidence `should` group across:

- `businessKeywords`
- `business`
- `desc`
- `domainTitle`
- `domainKeywords`
- `domainDesc`

Build stronger evidence across:

- `recruitingName`
- `recruitingDesc`
- `patentNameList`
- `biddingAnncTitleList`
- optional `appNames`, `appDescList`, `srName`

## Keyword expansion

Use the full node path. Expand:

- product names and technical synonyms
- business scenarios
- delivery/action verbs: `建设`, `搭建`, `运维`, `实施`, `集成`, `托管`, `交付`
- equipment verbs: `生产`, `制造`, `研发`, `集成`
- software/platform verbs: `开发`, `实施`, `运维`, `SaaS`, `平台化`
- job titles, patent terms, bidding terms

Avoid standalone generic terms: `平台`, `系统`, `服务`, `软件`, `解决方案`, `上游`, `中游`, `下游`, `产业链`.

## Review failures

- Zero recall: expand synonyms and broader business phrases.
- Over-broad recall: add industry boundary, stronger evidence, and must-not noise.
- Noisy samples: add exclusions for unrelated industries, pure trade, training, consulting, repair, retail.
- Parameter error: simplify to base `must` + one evidence `should` + minimal `must_not`.
