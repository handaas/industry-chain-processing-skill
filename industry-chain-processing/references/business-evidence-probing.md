# HandaaS Business Evidence Probing

## Purpose

Use this reference when deciding which HandaaS products and response dimensions should determine whether an enterprise actually operates in a target L5 node. Keep business-fit judgment separate from final enterprise-node link confirmation.

## Reproducible Probe

The bundled case set contains 15 enterprise-node judgments across servo drives, machining centers, and excavators:

- 9 known positive enterprise-node cases.
- 6 adjacent but negative cases, including component suppliers and downstream users that must not be linked to the product node.
- 10 unique legal enterprises; evidence is queried once per enterprise and reused across node judgments.

Run every non-empty combination of the six configured evidence products:

```bash
INDUSTRY_CHAIN_MCP_URL=http://127.0.0.1:8022/mcp \
python scripts/probe_business_evidence.py \
  --cases assets/business-evidence-cases.example.json \
  --max-combination-size 0 \
  --output /tmp/business-evidence-probe.json
```

Replace or extend the case file with operator-reviewed examples before using the metrics for another industry.

## Observed Baseline

Local HandaaS MCP probe on 2026-07-11:

| Product / dimension | Availability | Positive exact-hit rate | Negative exact-hit rate | Role |
| --- | ---: | ---: | ---: | --- |
| 企业标签 / `businessTags` | 100% | 88.89% | 0% | Highest-coverage direct business dimension |
| 企业招投标信息 / project titles | 100% | 66.67% | 0% | Strong commercialization and delivery evidence |
| 专利搜索 / applicant patent titles | 100% | 55.56% | 0% | Strong product and technology evidence |
| 企业简介 / `desc` | 100% | 33.33% | 0% | Medium business boundary and diversified-group context |
| 企业业务 | 40% | 22.22% | 0% | Strong when available, but optional only |
| 工商照面 / `business` + `industry` | 100% | 0% exact, 33.33% supporting | 0% | Legal identity, registered-scope, and fallback context |

The lean combination `企业标签 + 专利搜索 + 企业招投标信息` produced 100% precision and 88.89% recall. It missed one diversified enterprise whose available records exposed only one exact strong source.

The stable business-fit combination `工商照面 + 企业简介 + 企业标签 + 专利搜索 + 企业招投标信息` produced 100% precision and 100% recall on the 15-case baseline. Adding `企业业务` can improve strict link confirmation when that product returns data, but its low availability means it must never be a required interface.

## Decision Layers

### Business fit

Return `business_fit=matched` when:

- review score is at least 50;
- at least two independent products support the target node;
- no field-scoped conflict is present.

This layer may use two medium sources. It answers whether the enterprise appears to operate in the target business.

### Final link confirmation

Return `decision=confirmed` only when:

- review score is at least 65;
- at least two independent products support the node;
- at least one source is strong (`企业业务`, applicant patent, or bidding/project evidence);
- no conflict is present.

This layer answers whether evidence is sufficient for automatic enterprise-node linking.

## Product Rules

1. Resolve the legal enterprise and `nameId` before querying evidence.
2. Use `工商照面` for legal identity, operating status, registered scope, and industry context; do not treat a broad registered scope as direct product proof.
3. Use `企业简介` to recover the enterprise's stated product layers and group-level business boundary.
4. Use `企业标签.businessTags` as the primary direct business dimension.
5. Query patents by legal enterprise name with `keywordType=申请人`; never pass `nameId` as a patent applicant.
6. Use bidding titles and subject matter as evidence of commercial delivery, procurement, or project participation.
7. Treat `企业业务` as optional strong evidence. Record its exact product name and error when unavailable, then continue with the core five products.
8. Never confirm from one product. Repeated patents or bidding rows are one source, not multiple independent sources.

## Iteration

- Expand the judgment set before changing thresholds.
- Keep positives and hard adjacent negatives for every node family.
- Re-run the probe after product configuration, field extraction, scoring, or keyword-profile changes.
- Compare business-fit precision/recall separately from strict-link precision/recall.
- Do not generalize the 15-case percentages to every industry; treat them as a reproducible regression baseline.
