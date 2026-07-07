#!/usr/bin/env python3
"""Build deterministic enterprise-search JSON for a refined industry segment."""
from __future__ import annotations

import argparse
import json
import re
from typing import Any, Dict, Iterable, List, Sequence

from common import json_dumps, print_json

GENERIC_TERMS = {
    "平台", "系统", "服务", "软件", "产品", "解决方案", "方案", "企业", "公司", "产业链",
    "上游", "中游", "下游", "环节", "业务", "技术", "研发", "生产", "制造", "开发",
}
BASE_NOISE = ["培训", "咨询", "贸易", "商贸", "代理", "零售", "批发", "维修", "营销策划", "信息咨询", "企业管理咨询"]
BUSINESS_FIELDS = ["businessKeywords", "business", "desc", "domainTitle", "domainKeywords", "domainDesc"]
STRONG_FIELDS = ["recruitingName", "recruitingDesc", "patentNameList", "biddingAnncTitleList", "appNames", "appDescList", "srName"]


def normalize_keyword(value: str) -> str:
    text = str(value).strip().replace(" ", "")
    text = re.sub(r"产业链$", "", text)
    text = re.sub(r"产业$", "", text) if len(text) > 4 else text
    return text


def clean_token(value: str) -> List[str]:
    value = re.sub(r"[()（）]", " ", value.strip())
    parts = re.split(r"[>›/、，,;；:：|\s]+", value)
    result = []
    for part in parts:
        part = normalize_keyword(part)
        if 2 <= len(part) <= 32 and part not in GENERIC_TERMS and not re.match(r"^L[1-6]$", part, re.I):
            result.append(part)
    return result


def dedupe(values: Iterable[str], limit: int = 24) -> List[str]:
    seen = set()
    out = []
    for value in values:
        text = normalize_keyword(str(value))
        if not (2 <= len(text) <= 32) or text in GENERIC_TERMS:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
        if len(out) >= limit:
            break
    return out


def expand_keywords(node: str, path: Sequence[str], user_keywords: Sequence[str] = ()) -> Dict[str, List[str]]:
    text = " ".join([node, *path, *user_keywords])
    base = dedupe([node, *user_keywords, *sum((clean_token(item) for item in path[-3:]), [])], 18)
    product: List[str] = [*base]
    evidence: List[str] = []
    recruiting: List[str] = []
    noise: List[str] = [*BASE_NOISE]

    def add(*items: str) -> None:
        product.extend(items)
        evidence.extend(items)

    def add_evidence(*items: str) -> None:
        evidence.extend(items)

    if re.search(r"eVTOL|垂直起降|低空|航空器|飞行器", text, re.I):
        add("eVTOL", "电动垂直起降飞行器", "低空飞行器", "航空器制造", "飞行器总装", "适航取证")
        add_evidence("飞控系统", "航电系统", "机体结构", "动力系统", "适航认证", "低空飞行服务")
        recruiting.extend(["飞控工程师", "航电工程师", "适航工程师", "结构工程师", "飞行器总体设计"])
        noise.extend(["航空培训", "旅游观光", "票务代理", "模型玩具"])
    if re.search(r"无人机|UAV|巡检|航拍", text, re.I):
        add("无人机", "工业无人机", "无人机制造", "无人机巡检", "无人机系统")
        recruiting.extend(["无人机工程师", "飞控算法工程师", "嵌入式工程师"])
    if re.search(r"飞控|导航|航电", text):
        add("飞控系统", "飞行控制系统", "航电系统", "导航控制", "惯性导航", "组合导航")
        recruiting.extend(["飞控算法工程师", "导航算法工程师", "航电工程师"])
    if re.search(r"电池|PACK|动力", text, re.I):
        add("动力电池", "电池PACK", "电池管理系统", "BMS", "电池热管理")
        recruiting.extend(["BMS工程师", "电池系统工程师", "PACK工程师"])
    if re.search(r"复合材料|碳纤维|结构件", text):
        add("碳纤维复合材料", "复合材料结构件", "轻量化结构件", "航空复合材料")
        recruiting.extend(["复合材料工程师", "结构设计工程师"])
    if re.search(r"数据中心|IDC|机房", text, re.I):
        add("数据中心机房建设", "IDC机房建设", "机房工程", "数据中心运维", "机房托管", "基础设施集成")
        recruiting.extend(["数据中心运维工程师", "IDC运维工程师", "暖通工程师"])
    if re.search(r"AI|人工智能|大模型|RAG|智能体", text, re.I):
        add("人工智能", "大模型", "RAG知识库", "智能体平台", "模型训练", "模型推理", "AI应用开发")
        recruiting.extend(["算法工程师", "大模型工程师", "NLP工程师", "AI产品经理"])
    if re.search(r"机器人|具身智能|机械臂", text):
        add("机器人", "智能机器人", "机器人控制系统", "机械臂", "具身智能")
        recruiting.extend(["机器人工程师", "运动控制工程师", "嵌入式工程师"])
    if re.search(r"传感器|雷达|视觉", text):
        add("传感器", "智能传感器", "激光雷达", "机器视觉", "视觉检测")
        recruiting.extend(["传感器工程师", "视觉算法工程师", "光学工程师"])

    stripped = re.sub(r"(服务平台|解决方案|服务|平台|系统|软件|设备|产品)$", "", node).strip()
    if stripped and stripped != node:
        if node.endswith("服务"):
            add(f"{stripped}服务", f"{stripped}建设", f"{stripped}运维", f"{stripped}实施", f"{stripped}集成", f"{stripped}交付")
        if re.search(r"(平台|系统|软件)$", node):
            add(f"{stripped}平台", f"{stripped}系统", f"{stripped}开发", f"{stripped}实施", f"{stripped}运维", f"{stripped}SaaS")
        if node.endswith("设备"):
            add(f"{stripped}设备", f"{stripped}制造", f"{stripped}生产", f"{stripped}研发", f"{stripped}集成")

    if not evidence:
        evidence.extend([f"{kw}研发" for kw in base[:6]] + [f"{kw}生产" for kw in base[:4]] + [f"{kw}项目" for kw in base[:4]])
    if not recruiting:
        recruiting.extend([f"{node}工程师", f"{node}产品经理", f"{node}销售", f"{node}研发"])

    return {
        "core": dedupe(product, 20),
        "evidence": dedupe(evidence, 28),
        "recruiting": dedupe(recruiting, 16),
        "noise": dedupe(noise, 24),
    }


def parse_path(path_text: str | None, chain: str, node: str) -> List[str]:
    if not path_text:
        return [chain, node]
    return [item.strip() for item in re.split(r">|›|/", path_text) if item.strip()]


def industry_condition(paths: Sequence[str]) -> Dict[str, Any] | None:
    clean = []
    for path in paths:
        parts = [item.strip() for item in re.split(r">|/", path) if item.strip()]
        if parts:
            clean.append(parts)
    if not clean:
        return None
    return {"industriesV2": [{"eq": clean}]}


def should_group(fields: Sequence[str], keywords: Sequence[str]) -> Dict[str, Any]:
    return {"should": [{field: [{"in": list(keywords)}]} for field in fields if keywords]}


def build_condition_group(
    chain: str,
    node: str,
    path: Sequence[str] | None = None,
    keywords: Sequence[str] = (),
    industries: Sequence[str] = (),
    exclude: Sequence[str] = (),
) -> Dict[str, Any]:
    path = list(path or [chain, node])
    profile = expand_keywords(node, path, keywords)
    must: List[Dict[str, Any]] = [
        {"operStatus_v2": [{"eq": [["营业"]]}]},
        {"enterpriseType": [{"neq": [["个体户"]]}]},
    ]
    industry = industry_condition(industries)
    if industry:
        must.append(industry)
    must.append(should_group(BUSINESS_FIELDS, profile["core"]))
    must.append(should_group(STRONG_FIELDS, dedupe([*profile["evidence"], *profile["recruiting"]], 32)))
    noise = dedupe([*profile["noise"], *exclude], 28)
    return {
        "must": must,
        "must_not": [
            {"name": [{"nin": noise}]},
            {"business": [{"nin": noise}]},
            {"desc": [{"nin": noise}]},
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build enterprise-search JSON for a refined industry segment.")
    parser.add_argument("--chain", required=True, help="Industry chain name, e.g. 低空经济")
    parser.add_argument("--node", required=True, help="Refined business segment, product, technology, service, or capability, e.g. eVTOL整机制造")
    parser.add_argument("--path", help="Full path separated by > or /.")
    parser.add_argument("--keyword", action="append", default=[], help="Extra business keyword. Repeatable.")
    parser.add_argument("--industry", action="append", default=[], help="Industry path, e.g. 制造业/铁路、船舶、航空航天和其他运输设备制造业")
    parser.add_argument("--exclude", action="append", default=[], help="Extra noise term. Repeatable.")
    parser.add_argument("--output", help="Write enterprise-search JSON to file.")
    args = parser.parse_args()

    path = parse_path(args.path, args.chain, args.node)
    condition = build_condition_group(args.chain, args.node, path, args.keyword, args.industry, args.exclude)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(json_dumps(condition, pretty=True) + "\n")
    print_json(condition)


if __name__ == "__main__":
    main()
