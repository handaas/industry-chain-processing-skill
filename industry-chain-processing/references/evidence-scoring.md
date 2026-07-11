# Evidence Scoring

## Evidence strength

- Strong: enterprise-business product records, patent titles queried by enterprise applicant, bidding titles/subject matter, and equivalent product/project evidence.
- Medium: business scope, business keywords/tags, company description, national industry, and annual-report main business.
- Weak: project representative-company seed, high-screen recall route, company name, registered capital, contact fields, region, and legal status.

The default core product set is `工商照面 + 企业简介 + 企业标签 + 专利搜索 + 企业招投标信息`. `企业业务` is optional strong evidence because product availability can differ by enterprise/account. See `business-evidence-probing.md` for the reproducible ablation baseline.

## Business fit versus link confirmation

- `business_fit=matched`: score >= 50, at least two independent sources, and no conflict. Two medium sources can establish likely business participation.
- `business_fit=partial`: some matching evidence exists, but source coverage or score is insufficient.
- `business_fit=not_matched`: no sufficient target-business evidence.
- `decision=confirmed`: stricter automatic-link rule requiring score >= 65 and at least one strong source.

## Decision labels

- `confirmed`: `review_score >= 65`, at least one strong source, at least two independent evidence sources, and no conflict signal.
- `uncertain`: score >= 30 or one strong source exists, but the independent-source acceptance rule is incomplete.
- `rejected`: only weak evidence exists, exact/supporting node terms do not appear in evidence, or evidence points to an excluded business.

Count sources, not repeated rows. Multiple patents from `专利搜索` are one independent source. The same term repeated in profile and tags counts as two sources only when the underlying HandaaS products are distinct.

## Output format

```json
{
  "enterprise_name": "...",
  "decision": "confirmed|uncertain|rejected",
  "evidence_strength": "strong|medium|weak",
  "matched_segment": "refined segment name",
  "review_score": 0,
  "evidence_source_count": 0,
  "strong_source_count": 0,
  "business_fit": "matched|partial|not_matched|unreviewed",
  "business_fit_reason": "...",
  "recall_routes": ["industry_business_keyword", "registration_scope_precision", "project_seed"],
  "matched_evidence": [],
  "conflict_hits": [],
  "reason": "short operator-facing reason",
  "next_action": "confirm link | manual review | reject and add exclusion"
}
```
