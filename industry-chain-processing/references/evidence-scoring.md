# Evidence Scoring

## Evidence strength

- Strong: patent titles, recruiting roles/descriptions, bidding titles/subject matter, factory/certification/product qualification data.
- Medium: business scope, business keywords, company description, national industry, annual-report main business.
- Weak: company name, registered capital, contact fields, region, legal status.

## Decision labels

- `confirmed`: at least one strong signal matches the L5 node and medium signals do not conflict.
- `uncertain`: only medium evidence exists, or strong evidence is adjacent but not exact.
- `rejected`: only weak evidence exists, or business scope/sample names clearly point to another industry.

## Output format

```json
{
  "enterprise_name": "...",
  "decision": "confirmed|uncertain|rejected",
  "evidence_strength": "strong|medium|weak",
  "matched_node": "L5 node name",
  "reason": "short operator-facing reason",
  "next_action": "confirm link | manual review | reject and add exclusion"
}
```
