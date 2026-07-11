# Internal Ontology Contract

This file defines the internal hierarchy used by the skill. Do not require users to provide these labels.

## Internal hierarchy

Use the project graph hierarchy when available:

- L1 / Industry domain: the overall chain, e.g. `智能网联汽车` or `低空经济产业链`.
- L2 / Value segment: major value-creation area, preferably industry-specific instead of generic upstream/midstream/downstream.
- L3 / Business module: concrete industry segment or business module.
- L4 / Optional fine-grained direction or capability group: optional compatibility layer between L3 and L5 for technology routes, product families, application directions, or capability groups. Current project graphs often skip explicit L4 and connect L3 directly to L5.
- L5 / Terminal target: product, technology, service, material, equipment, platform, solution, or capability that can be matched to companies.

L5 is the enterprise-linking target. Preserve existing node IDs and paths from the current project when present. Do not invent L4 nodes when the project graph does not model them; explain L4 as optional/reserved.

## Enterprise boundary

Enterprises are linked records, not hierarchy nodes.

```text
Industry Chain
  Value Segment
    Business Module
      Terminal Target
        enterprise links: separate candidate records
```

## Good terminal target examples

- eVTOL整机制造
- 飞控系统
- 低空空域管理平台
- 动力电池PACK
- 碳纤维复合材料结构件
- 产业招商企业线索核验服务

## Bad terminal target examples

- 企业 names such as `亿航智能`, `小鹏汇天`, `大疆`.
- Vague nodes such as `平台`, `系统`, `服务`, `解决方案`, `其他`.
- Structural names such as `上游`, `中游`, `下游`.

## Validation checklist

- Do not create extra hierarchy below L5/terminal targets.
- No enterprise/company/brand names appear as children.
- L5/terminal targets have empty `children` in normalized JSON.
- Terminal target counts vary by module complexity; avoid fixed counts per module.
- Every terminal target is specific enough to become an enterprise search strategy.
