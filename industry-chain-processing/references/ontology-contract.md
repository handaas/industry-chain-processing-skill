# Ontology Contract

## Levels

- L1: industry chain domain, e.g. `低空经济产业链`.
- L2: value segment, preferably industry-specific instead of generic upstream/midstream/downstream when possible.
- L3: industry segment or business module.
- L4: optional/folded context; this skill normally outputs compact L2 → L3 → L5.
- L5: product, technology, service, material, equipment, platform, solution, or capability standard node.

## Enterprise boundary

Enterprises are linked records, not ontology nodes.

```text
L1 Industry Chain
  L2 Value Segment
    L3 Industry Segment
      L5 Product/Technology/Service Node
        enterprise links: separate candidate records
```

## Good L5 examples

- eVTOL整机制造
- 飞控系统
- 低空空域管理平台
- 动力电池PACK
- 碳纤维复合材料结构件
- 产业招商企业线索核验服务

## Bad L5 examples

- 企业 names such as `亿航智能`, `小鹏汇天`, `大疆`.
- Vague nodes such as `平台`, `系统`, `服务`, `解决方案`, `其他`.
- Structural nodes such as `上游`, `中游`, `下游` as L5 names.

## Validation checklist

- No L6 appears in the ontology output.
- No enterprise/company/brand names appear as children.
- L5 nodes have empty `children` in normalized JSON.
- L5 counts vary by L3 complexity; avoid fixed three-per-L3 output.
- Every L5 is specific enough to become a high-screen condition.
