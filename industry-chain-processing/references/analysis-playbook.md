# Analysis Playbook

Use this playbook to turn a natural business request into an internal industry-chain analysis and enterprise-discovery workflow. Do not expose internal mechanics unless the user asks.

## Intent routing

- “分析 XX 产业链”: produce an industry map, priority segments, enterprise types, search strategy, and next actions. Do not require API calls.
- “找企业 / 企业线索 / 招商名单”: build the map, choose high-value refined targets, then run dry-run or real local query depending on config and user wording.
- “判断这些企业”: map each company to the most plausible refined segment, collect or request evidence, then classify confidence.
- “优化结果 / 太宽 / 噪声多”: inspect false positives, add exclusions, strengthen business evidence, then re-run dry-run.
- “不要真实调用 / 先模拟”: never call network; output assumptions, search strategy, and redacted request shape.

## Auto-decomposition logic

For a broad industry, build the map with these lenses:

1. Demand scenario: who pays, what problem is solved, what deployment context exists.
2. Value chain: core product/service, key upstream inputs, enabling technology, downstream operation/application.
3. Evidence availability: whether companies can be identified through business scope, websites, jobs, patents, bidding, qualifications, or product names.
4. Commercial usefulness: prioritize segments useful for招商, sales, investment, supply-chain matching, or risk review.
5. Noise risk: mark segments likely to pull in trading, training, consulting, repair, retail, or generic software noise.

## Refined target criteria

A refined enterprise-search target should be:

- Specific enough to identify a company by product, technology, service, equipment, material, platform, or capability.
- Broad enough to recall more than one company.
- Evidence-friendly: likely to appear in jobs, patents, bidding, business scope, websites, certifications, or product descriptions.
- Not a company name, brand-only phrase, generic word, or pure structural label.

Good target examples:

- eVTOL整机制造
- 飞控系统
- 低空空域管理平台
- 动力电池PACK
- 碳纤维复合材料结构件
- 人形机器人关节模组
- 半导体刻蚀设备

Weak target examples:

- 平台
- 系统
- 服务
- 解决方案
- 上游
- 中游
- 其他

## Priority scoring

When the user does not specify where to start, choose 3 to 8 refined targets by scoring:

- Business relevance: core to the industry or user goal.
- Enterprise discoverability: enough evidence terms exist.
- Decision value: useful for招商, sales, sourcing, investment, or risk analysis.
- Boundary clarity: can distinguish true companies from adjacent/noisy companies.
- Evidence strength: likely to have patents, jobs, bids, qualifications, or product pages.

## Search strategy generation

For each chosen target, internally prepare:

- Core terms: product/service/capability names.
- Synonyms: English, abbreviations, old names, adjacent technical terms.
- Scenario terms: where it is used and by whom.
- Action terms: 研发, 生产, 制造, 集成, 交付, 运维, 建设, 运营.
- Evidence terms: recruiting roles, patent phrases, bidding phrases, qualifications.
- Exclusions: training, consulting, tourism, repair, retail, unrelated generic platform/software when noisy.

## Result format

Prefer this business-readable structure:

```json
{
  "industry_map": ["..."],
  "priority_segments": ["..."],
  "search_strategy": ["..."],
  "candidates": ["..."],
  "decisions": [
    {
      "enterprise_name": "...",
      "matched_segment": "...",
      "decision": "confirmed|uncertain|rejected",
      "reason": "...",
      "next_action": "..."
    }
  ],
  "next_actions": ["..."]
}
```

Use tables for human-facing reports unless JSON is requested.
