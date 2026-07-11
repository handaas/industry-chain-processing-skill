#!/usr/bin/env python3
"""Build field-valid HandaaS high-screen ES conditions for one L5 node."""
from __future__ import annotations

import argparse
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from common import json_dumps, print_json
from project_context import build_project_context


FIELD_RULES: Dict[str, Dict[str, Any]] = {
    "operStatus_v2": {"operators": {"eq", "neq"}},
    "enterpriseType": {"operators": {"eq", "neq"}},
    "regCapitalRmb": {"operators": {"gte", "lte", "gt", "lt"}},
    "industriesV2": {"operators": {"eq", "neq"}},
    "name": {"operators": {"in", "nin"}, "max_keywords": 10},
    "businessKeywords": {"operators": {"in", "nin"}, "max_keywords": 10},
    "business": {"operators": {"in", "nin"}, "max_keywords": 10},
    "desc": {"operators": {"in", "nin"}, "max_keywords": 10},
    "domainTitle": {"operators": {"in", "nin"}, "max_keywords": 30},
    "domainKeywords": {"operators": {"in", "nin"}, "max_keywords": 30},
    "domainDesc": {"operators": {"in", "nin"}, "max_keywords": 30},
    "recruitingName": {"operators": {"in", "nin"}, "max_keywords": 30},
    "recruitingDesc": {"operators": {"in", "nin"}, "max_keywords": 30},
    "patentNameList": {"operators": {"in", "nin"}, "max_keywords": 10},
    "biddingAnncTitleList": {"operators": {"in", "nin"}, "max_keywords": 10},
}
BUSINESS_FIELDS = ("businessKeywords", "business", "desc", "domainTitle", "domainKeywords", "domainDesc")
STRONG_FIELDS = ("recruitingName", "recruitingDesc", "patentNameList", "biddingAnncTitleList")
GENERIC_TERMS = {
    "平台", "系统", "服务", "软件", "产品", "解决方案", "方案", "企业", "公司", "产业链",
    "上游", "中游", "下游", "环节", "业务", "技术", "研发", "生产", "制造", "开发",
    "核心零部件", "核心零部件与基础材料", "原材料与核心设备", "应用领域", "行业应用",
}
GENERIC_SUPPORTING_TERMS = {"立式", "卧式", "龙门", "高端", "中端", "低端", "大型", "中型", "小型"}
NAME_NOISE = ["培训", "咨询", "贸易", "商贸", "经贸", "工贸", "代理", "经销", "维修", "租赁"]
TEXT_NOISE = ["教育培训", "职业培训", "纯贸易", "批发零售", "票务代理", "汽车维修", "家电维修", "营销策划"]


DOMAIN_PROFILES = [
    (
        r"伺服驱动|伺服系统|运动控制",
        {
            "exact": ["伺服驱动器", "伺服驱动", "交流伺服驱动器", "伺服控制器"],
            "supporting": ["伺服系统", "运动控制", "电机控制", "伺服电机"],
            "recruiting": ["伺服驱动工程师", "运动控制工程师", "电机控制工程师"],
            "noise": ["变频器维修", "电机维修", "自动化培训"],
        },
    ),
    (
        r"工业机器人系统集成|机器人系统集成|自动化集成",
        {
            "exact": ["工业机器人系统集成", "机器人系统集成", "自动化产线集成", "机器人工作站"],
            "supporting": ["机械臂集成", "机器人控制", "自动化生产线", "工装夹具"],
            "recruiting": ["机器人工程师", "机器人集成工程师", "自动化工程师", "电气工程师"],
            "noise": ["机器人培训", "机器人租赁", "玩具机器人"],
        },
    ),
    (
        r"自动驾驶|智能驾驶|ADAS|Robotaxi",
        {
            "exact": ["自动驾驶", "智能驾驶", "自动驾驶解决方案", "ADAS", "Robotaxi"],
            "supporting": ["感知融合", "路径规划", "决策控制", "域控制器", "车路协同"],
            "recruiting": ["自动驾驶算法工程师", "感知算法工程师", "规划控制工程师", "定位算法工程师"],
            "noise": ["驾驶培训", "驾校", "汽车维修", "网约车租赁"],
        },
    ),
    (
        r"eVTOL|垂直起降|低空飞行器|航空器整机",
        {
            "exact": ["eVTOL", "电动垂直起降飞行器", "低空飞行器", "航空器整机"],
            "supporting": ["飞行器总装", "飞控系统", "航电系统", "机体结构", "适航认证"],
            "recruiting": ["飞控工程师", "航电工程师", "适航工程师", "飞行器总体设计"],
            "noise": ["航空培训", "旅游观光", "票务代理", "模型玩具"],
        },
    ),
    (
        r"动力电池|电池PACK|电芯|BMS",
        {
            "exact": ["动力电池", "电池PACK", "电池包", "电芯", "电池管理系统", "BMS"],
            "supporting": ["电池模组", "电池热管理", "锂离子电池", "电池系统"],
            "recruiting": ["BMS工程师", "电池系统工程师", "PACK工程师", "电芯研发工程师"],
            "noise": ["电池回收门店", "电动车维修", "蓄电池零售"],
        },
    ),
    (
        r"传感器|激光雷达|毫米波雷达|机器视觉",
        {
            "exact": ["传感器", "智能传感器", "激光雷达", "毫米波雷达", "机器视觉"],
            "supporting": ["感知系统", "视觉检测", "信号采集", "数据融合", "光电检测"],
            "recruiting": ["传感器工程师", "视觉算法工程师", "光学工程师", "硬件工程师"],
            "noise": ["监控安装", "摄影服务", "安防工程施工"],
        },
    ),
    (
        r"机器人|机械臂|具身智能",
        {
            "exact": ["工业机器人", "智能机器人", "机械臂", "具身智能"],
            "supporting": ["机器人控制", "运动控制", "机器人本体", "末端执行器"],
            "recruiting": ["机器人工程师", "运动控制工程师", "嵌入式工程师"],
            "noise": ["机器人培训", "机器人租赁", "玩具机器人"],
        },
    ),
]

INFERRED_INDUSTRIES = [
    (
        r"伺服驱动|伺服系统|运动控制|变频器|电机控制",
        [
            "制造业/电气机械和器材制造业",
            "制造业/通用设备制造业",
            "制造业/仪器仪表制造业",
        ],
    ),
    (
        r"工业机器人|机器人本体|机器人系统集成|工业母机|数控机床",
        ["制造业/通用设备制造业", "制造业/专用设备制造业"],
    ),
    (
        r"数控车床|数控铣床|加工中心|磨床|齿轮加工机床|钻床|激光加工设备|冲床|压力机|折弯机|剪板机|电火花机床|线切割机床",
        ["制造业/通用设备制造业", "制造业/专用设备制造业"],
    ),
    (
        r"滚珠丝杠|直线导轨|齿轮|电主轴|机械主轴|刀具|轴承|铸件|钣金|机床附件",
        ["制造业/通用设备制造业", "制造业/金属制品业"],
    ),
    (
        r"传感器|激光雷达|毫米波雷达|芯片|半导体",
        ["制造业/计算机、通信和其他电子设备制造业", "制造业/仪器仪表制造业"],
    ),
    (
        r"动力电池|电池PACK|电芯|BMS",
        ["制造业/电气机械和器材制造业", "制造业/汽车制造业"],
    ),
    (
        r"eVTOL|垂直起降飞行器|航空器整机",
        ["制造业/铁路、船舶、航空航天和其他运输设备制造业"],
    ),
    (
        r"挖掘机|起重机|装载机|压路机|混凝土机械|盾构机|矿山机械",
        ["制造业/专用设备制造业", "制造业/通用设备制造业"],
    ),
    (
        r"汽车制造|整车制造|汽车零部件",
        ["制造业/汽车制造业"],
    ),
    (
        r"航空航天.*(?:飞机制造|发动机制造|航天器制造)|飞机制造|航天器制造",
        ["制造业/铁路、船舶、航空航天和其他运输设备制造业"],
    ),
    (
        r"发电设备|核电设备|石油化工装备",
        ["制造业/通用设备制造业", "制造业/专用设备制造业"],
    ),
]


def normalize_keyword(value: Any) -> str:
    text = str(value or "").strip().replace(" ", "")
    text = re.sub(r"产业链$", "", text)
    text = re.sub(r"产业$", "", text) if len(text) > 4 else text
    return text


def clean_token(value: Any) -> List[str]:
    text = re.sub(r"[()（）]", " ", str(value or "").strip())
    parts = re.split(r"[>›/、，,;；:：|\s]+", text)
    return [item for item in (normalize_keyword(part) for part in parts) if 2 <= len(item) <= 30 and item not in GENERIC_TERMS and not re.match(r"^L[1-6]$", item, re.I)]


def dedupe(values: Iterable[Any], limit: int = 24) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for value in values:
        text = normalize_keyword(value)
        if not (2 <= len(text) <= 30) or text in GENERIC_TERMS:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
        if len(out) >= limit:
            break
    return out


def parse_path(path_text: str | None, chain: str, node: str) -> List[str]:
    if not path_text:
        return [chain, node]
    return [item.strip() for item in re.split(r">|›|/", path_text) if item.strip()]


def infer_role(path: Sequence[str]) -> str:
    l2 = str(path[1] if len(path) > 1 else "")
    if "上游" in l2:
        return "upstream"
    if "下游" in l2:
        return "downstream"
    if "中游" in l2:
        return "midstream"
    return "cross_chain"


def domain_profile(text: str) -> Dict[str, List[str]]:
    merged: Dict[str, List[str]] = {"exact": [], "supporting": [], "recruiting": [], "noise": []}
    for pattern, profile in DOMAIN_PROFILES:
        if not re.search(pattern, text, re.I):
            continue
        for key in merged:
            merged[key].extend(profile.get(key) or [])
    return {key: dedupe(values, 24) for key, values in merged.items()}


def infer_industries(chain: str, node: str, path: Sequence[str]) -> List[str]:
    if infer_role(path) == "downstream" and re.search(r"服务|运营|平台|解决方案|应用$|场景$", node):
        return []
    # Industry paths are a precision route, so infer them from L3/L5 semantics.
    # A broad L1 chain name such as "工业母机" must not force software nodes into manufacturing.
    text = " ".join([node, *path[2:]])
    for pattern, paths in INFERRED_INDUSTRIES:
        if re.search(pattern, text, re.I):
            return list(paths)
    return []


def node_exact_terms(node: str) -> List[str]:
    text = str(node or "").strip()
    base = re.sub(r"[（(].*?[）)]", "", text).strip()
    values: List[str] = [base or text]
    match = re.search(r"[（(](.*?)[）)]", text)
    if not match or not base:
        return dedupe(values, 10)
    options = [item.strip() for item in re.split(r"[、，,;/；]+", match.group(1)) if item.strip()]
    suffix = next(
        (item for item in ("加工中心", "驱动器", "传感器", "控制器", "机器人", "机床", "设备", "刀具", "系统", "软件", "材料", "电机", "轴承") if base.endswith(item)),
        base,
    )
    for option in options:
        if option in GENERIC_SUPPORTING_TERMS or len(option) <= 4:
            values.append(f"{option}{suffix}")
        else:
            values.append(option if suffix in option else f"{option}{suffix}")
    return dedupe(values, 10)


def role_actions(role: str, node: str) -> Sequence[str]:
    if role == "upstream":
        return ("研发", "生产", "制造")
    if role == "midstream":
        return ("制造", "集成", "交付")
    if role == "downstream":
        if re.search(r"服务|运营|平台|解决方案|应用$|场景$", node):
            return ("运营", "应用", "服务")
        return ("生产", "制造", "应用")
    return ("研发", "生产", "集成")


def build_keyword_profile(
    chain: str,
    node: str,
    path: Sequence[str],
    user_keywords: Sequence[str] = (),
    project_keywords: Sequence[str] = (),
    exclude: Sequence[str] = (),
) -> Dict[str, List[str]]:
    role = infer_role(path)
    text = " ".join([chain, node, *path, *user_keywords, *project_keywords])
    domain = domain_profile(text)
    exact = dedupe([*node_exact_terms(node), *user_keywords, *domain["exact"]], 10)
    blocked_project_terms = {
        normalize_keyword(chain).lower(),
        *(normalize_keyword(item).lower() for item in path[1:2]),
        *(normalize_keyword(item).lower() for item in exact),
    }
    project_terms = [
        item
        for item in dedupe(project_keywords, 20)
        if item.lower() not in blocked_project_terms and item not in GENERIC_SUPPORTING_TERMS
    ]
    supporting = dedupe([
        *project_terms,
        *domain["supporting"],
        *sum((clean_token(item) for item in path[2:-1]), []),
    ], 14)
    canonical_node = exact[0] if exact else node
    root = re.sub(r"(总体解决方案|解决方案|运营服务|服务平台|服务|平台|系统|软件|设备|产品)$", "", canonical_node).strip() or canonical_node
    actions = role_actions(role, node)
    action_terms = [f"{root}{action}" for action in actions]
    business = dedupe([*exact, *supporting, *action_terms], 18)
    evidence = dedupe([*exact, *domain["supporting"], root], 12)
    recruiting = dedupe([
        *domain["recruiting"],
        f"{root}工程师",
        f"{root}研发工程师",
        f"{root}产品经理",
    ], 16)
    name_noise = dedupe([*NAME_NOISE, *domain["noise"], *exclude], 10)
    text_noise = dedupe([*TEXT_NOISE, *domain["noise"], *exclude], 10)
    return {
        "exact": exact,
        "supporting": supporting,
        "action": dedupe(action_terms, 8),
        "business": business,
        "evidence": evidence,
        "recruiting": recruiting,
        "name_noise": name_noise,
        "text_noise": text_noise,
    }


def expand_keywords(node: str, path: Sequence[str], user_keywords: Sequence[str] = ()) -> Dict[str, List[str]]:
    profile = build_keyword_profile(path[0] if path else "", node, path, user_keywords)
    return {
        "core": dedupe([*profile["exact"], *profile["supporting"]], 20),
        "evidence": profile["evidence"],
        "recruiting": profile["recruiting"],
        "noise": dedupe([*profile["name_noise"], *profile["text_noise"]], 20),
    }


def industry_condition(paths: Sequence[str]) -> Optional[Dict[str, Any]]:
    clean: List[List[str]] = []
    for path in paths:
        parts = [item.strip() for item in re.split(r">|/", path) if item.strip()]
        if parts:
            clean.append(parts)
    return {"industriesV2": [{"eq": clean}]} if clean else None


def field_condition(field: str, operator: str, values: Sequence[str]) -> Optional[Dict[str, Any]]:
    rules = FIELD_RULES[field]
    limit = int(rules.get("max_keywords") or len(values) or 1)
    items = dedupe(values, limit)
    if not items:
        return None
    return {field: [{operator: items}]}


def should_group(field_values: Mapping[str, Sequence[str]]) -> Dict[str, Any]:
    rows = [field_condition(field, "in", values) for field, values in field_values.items()]
    return {"should": [item for item in rows if item]}


def identity_conditions(industries: Sequence[str] = ()) -> List[Dict[str, Any]]:
    must: List[Dict[str, Any]] = [
        {"operStatus_v2": [{"eq": [["营业"]]}]},
        {"enterpriseType": [{"neq": [["个体户"]]}]},
        {"regCapitalRmb": [{"gte": 10}]},
    ]
    industry = industry_condition(industries)
    if industry:
        must.append(industry)
    return must


def strong_evidence_values(
    profile: Mapping[str, Sequence[str]],
    precision: str,
) -> Dict[str, Sequence[str]]:
    exact_norms = [normalize_keyword(item).lower() for item in profile["exact"]]
    strict_recruiting = [
        item
        for item in profile["recruiting"]
        if any(term and term in normalize_keyword(item).lower() for term in exact_norms)
    ] or [f"{profile['exact'][0]}工程师"]
    recruiting = strict_recruiting if precision == "strict" else profile["recruiting"]
    return {
        "recruitingName": recruiting,
        "recruitingDesc": dedupe(
            [*recruiting, *profile["exact"], *([] if precision == "strict" else profile["supporting"])],
            30,
        ),
        "patentNameList": profile["exact"],
        "biddingAnncTitleList": profile["exact"],
    }


def noise_conditions(profile: Mapping[str, Sequence[str]]) -> List[Dict[str, Any]]:
    return [
        item
        for item in (
            field_condition("name", "nin", profile["name_noise"]),
            field_condition("business", "nin", profile["text_noise"]),
            field_condition("desc", "nin", profile["text_noise"]),
        )
        if item
    ]


def is_negative_field_clause(value: Any) -> bool:
    if not isinstance(value, Mapping) or not value:
        return False
    for field, operations in value.items():
        if field in {"must", "should", "must_not"}:
            if not isinstance(operations, list) or not all(is_negative_field_clause(item) for item in operations):
                return False
            continue
        if not isinstance(operations, list) or not operations:
            return False
        for operation in operations:
            if not isinstance(operation, Mapping) or not operation:
                return False
            if any(operator not in {"nin", "neq"} for operator in operation):
                return False
    return True


def normalize_legacy_negative_groups(condition: Mapping[str, Any]) -> tuple[Dict[str, Any], bool]:
    """Move legacy negative field clauses into must, where HandaaS executes nin/neq."""
    legacy = condition.get("must_not")
    if not isinstance(legacy, list) or not legacy or not all(is_negative_field_clause(item) for item in legacy):
        return dict(condition), False
    normalized = {key: value for key, value in condition.items() if key != "must_not"}
    normalized["must"] = [*(condition.get("must") or []), *legacy]
    return normalized, True


def route_condition(
    profile: Mapping[str, Sequence[str]],
    industries: Sequence[str],
    business_field_groups: Sequence[Sequence[str]],
    precision: str,
) -> Dict[str, Any]:
    must = identity_conditions(industries)
    business_terms = dedupe(
        [
            *profile["exact"],
            *profile["action"],
            *([] if precision == "strict" else profile["supporting"]),
        ],
        18,
    )
    for fields in business_field_groups:
        business_values = {field: business_terms for field in fields}
        if len(business_values) == 1:
            field, values = next(iter(business_values.items()))
            business_clause = field_condition(field, "in", values)
        else:
            business_clause = should_group(business_values)
        if business_clause:
            must.append(business_clause)
    must.append(should_group(strong_evidence_values(profile, precision)))
    must.extend(noise_conditions(profile))
    return {"must": must}


def generated_condition(
    profile: Mapping[str, Sequence[str]],
    industries: Sequence[str],
    precision: str,
) -> Dict[str, Any]:
    return route_condition(profile, industries, [BUSINESS_FIELDS], precision)


def generated_recall_routes(
    profile: Mapping[str, Sequence[str]],
    industries: Sequence[str],
    precision: str,
) -> List[Dict[str, Any]]:
    specs: List[Dict[str, Any]] = []
    if industries:
        specs.extend([
            {
                "id": "industry_business_consensus",
                "purpose": "工商基础、行业边界、业务关键词、经营范围或简介和强证据共同命中",
                "industries": industries,
                "business_field_groups": [["businessKeywords"], ["business", "desc"]],
                "priority": 6,
            },
            {
                "id": "industry_registration_scope",
                "purpose": "工商基础、行业边界、经营范围或企业简介和强证据共同命中",
                "industries": industries,
                "business_field_groups": [["business", "desc"]],
                "priority": 5,
            },
            {
                "id": "industry_business_keyword",
                "purpose": "工商基础、行业边界、业务关键词和强证据共同命中",
                "industries": industries,
                "business_field_groups": [["businessKeywords"]],
                "priority": 4,
            },
        ])
    specs.extend([
        {
            "id": "business_consensus_precision",
            "purpose": "业务关键词、经营范围或简介和强证据共同命中，不依赖行业标签",
            "industries": [],
            "business_field_groups": [["businessKeywords"], ["business", "desc"]],
            "priority": 5,
        },
        {
            "id": "registration_scope_precision",
            "purpose": "经营范围或企业简介和强证据共同命中，覆盖业务关键词字段缺失企业",
            "industries": [],
            "business_field_groups": [["business", "desc"]],
            "priority": 4,
        },
        {
            "id": "business_keyword_precision",
            "purpose": "业务关键词和强证据共同命中，补回行业标签缺失或错分企业",
            "industries": [],
            "business_field_groups": [["businessKeywords"]],
            "priority": 3,
        },
    ])
    if precision == "balanced":
        specs.append({
            "id": "web_presence_recall",
            "purpose": "官网标题、关键词或简介和强证据共同命中，仅用于平衡召回",
            "industries": [],
            "business_field_groups": [["domainTitle", "domainKeywords", "domainDesc"]],
            "priority": 1,
        })
    routes: List[Dict[str, Any]] = []
    for spec in specs:
        condition = route_condition(
            profile,
            spec["industries"],
            spec["business_field_groups"],
            precision,
        )
        business_fields = [field for group in spec["business_field_groups"] for field in group]
        routes.append({
            **spec,
            "business_fields": business_fields,
            "minimum_evidence_groups": len(spec["business_field_groups"]) + 1,
            "condition": condition,
            "quality_checks": validate_condition_group(condition, require_strong=True),
        })
    return routes


def validate_condition_group(condition: Any, *, require_strong: bool = True) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []
    fields: set[str] = set()
    strong_present = False

    def visit(value: Any) -> None:
        nonlocal strong_present
        if isinstance(value, list):
            for item in value:
                visit(item)
            return
        if not isinstance(value, Mapping):
            return
        for key, payload in value.items():
            if key == "must_not":
                errors.append("旷湖高筛不执行顶层 must_not；请把 nin/neq 字段条件直接放入 must")
                visit(payload)
                continue
            if key in {"must", "should"}:
                visit(payload)
                continue
            fields.add(str(key))
            if key in STRONG_FIELDS:
                strong_present = True
            rules = FIELD_RULES.get(str(key))
            if not rules:
                warnings.append(f"未在本 Skill 字段契约中登记：{key}")
                continue
            if not isinstance(payload, list):
                errors.append(f"字段 {key} 的条件必须是数组")
                continue
            for operation in payload:
                if not isinstance(operation, Mapping):
                    errors.append(f"字段 {key} 的操作必须是对象")
                    continue
                for operator, operand in operation.items():
                    if operator not in rules["operators"]:
                        errors.append(f"字段 {key} 不支持操作符 {operator}")
                    limit = rules.get("max_keywords")
                    if limit and operator in {"in", "nin"} and isinstance(operand, list) and len(operand) > int(limit):
                        errors.append(f"字段 {key} 关键词数量 {len(operand)} 超过限制 {limit}")

    if not isinstance(condition, Mapping):
        errors.append("条件组顶层必须是对象")
    else:
        visit(condition)
    if require_strong and not strong_present:
        errors.append("严格模式必须包含招聘、专利或招投标强证据字段")
    return {
        "valid": not errors,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "fields": sorted(fields),
        "strong_evidence_fields": strong_present,
    }


def build_search_plan(
    chain: str,
    node: str,
    path: Sequence[str] | None = None,
    keywords: Sequence[str] = (),
    industries: Sequence[str] = (),
    exclude: Sequence[str] = (),
    *,
    precision: str = "strict",
    project_context: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    canonical_path = list(path or [chain, node])
    project_node: Mapping[str, Any] = {}
    matched_nodes = project_context.get("matched_nodes") if isinstance(project_context, Mapping) else None
    if isinstance(matched_nodes, list) and matched_nodes:
        project_node = matched_nodes[0] if isinstance(matched_nodes[0], Mapping) else {}
        if project_node.get("path"):
            canonical_path = [str(item) for item in project_node.get("path") or []]
        node = str(project_node.get("node_name") or node)
        chain = str(canonical_path[0] if canonical_path else chain)
    project_keywords = project_node.get("condition_keywords") if isinstance(project_node.get("condition_keywords"), list) else []
    profile = build_keyword_profile(chain, node, canonical_path, keywords, project_keywords, exclude)
    saved_condition = project_node.get("condition") if isinstance(project_node.get("condition"), Mapping) else {}
    source = str(project_node.get("condition_source") or "")
    if saved_condition and source.startswith("operator_confirmed"):
        condition, migrated_negative_group = normalize_legacy_negative_groups(saved_condition)
        origin = "operator_confirmed_project"
        checks = validate_condition_group(condition, require_strong=False)
        checks["migrated_legacy_must_not"] = migrated_negative_group
        applied_industries = list(industries)
        recall_routes = [
            {
                "id": "operator_confirmed",
                "purpose": "复用项目内经人工确认的高筛条件",
                "condition": condition,
                "quality_checks": checks,
            }
        ]
    else:
        applied_industries = list(industries) or (infer_industries(chain, node, canonical_path) if precision == "strict" else [])
        recall_routes = generated_recall_routes(profile, applied_industries, precision)
        condition = recall_routes[0]["condition"]
        origin = "generated_from_project_node" if project_node else "generated"
        checks = validate_condition_group(condition, require_strong=precision == "strict")
    return {
        "condition": condition,
        "condition_origin": origin,
        "precision": precision,
        "recall_strategy": "multi_route" if len(recall_routes) > 1 else "single_route",
        "recall_routes": recall_routes,
        "node_context": {
            "chain": chain,
            "node": node,
            "role": infer_role(canonical_path),
            "canonical_path": canonical_path,
            "project_condition_source": source or None,
            "industry_paths": applied_industries,
        },
        "keyword_profile": profile,
        "quality_checks": checks,
    }


def build_condition_group(
    chain: str,
    node: str,
    path: Sequence[str] | None = None,
    keywords: Sequence[str] = (),
    industries: Sequence[str] = (),
    exclude: Sequence[str] = (),
    *,
    precision: str = "strict",
    project_context: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    return build_search_plan(
        chain,
        node,
        path,
        keywords,
        industries,
        exclude,
        precision=precision,
        project_context=project_context,
    )["condition"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build HandaaS high-screen ES JSON for one refined L5 node.")
    parser.add_argument("--chain", required=True, help="Industry-chain name")
    parser.add_argument("--node", required=True, help="L5 product, technology, service, or capability node")
    parser.add_argument("--path", help="Full path separated by > or /")
    parser.add_argument("--keyword", action="append", default=[], help="Extra exact/supporting keyword; repeatable")
    parser.add_argument("--industry", action="append", default=[], help="Explicit industriesV2 path; repeatable")
    parser.add_argument("--exclude", action="append", default=[], help="Extra noise term; repeatable")
    parser.add_argument("--precision", choices=["strict", "balanced"], default="strict")
    parser.add_argument("--project-root", help="industry-chain-map project root")
    parser.add_argument("--project-chain", help="Canonical project chain override")
    parser.add_argument("--project-node", help="Canonical project L5 node override")
    parser.add_argument("--explain", action="store_true", help="Print the complete search plan instead of only the ES condition")
    parser.add_argument("--output", help="Write ES condition JSON to file")
    parser.add_argument("--plan-output", help="Write complete search plan JSON to file")
    args = parser.parse_args()

    path = parse_path(args.path, args.chain, args.node)
    context = build_project_context(
        args.chain,
        args.project_node or args.node,
        project_root=args.project_root,
        preferred_chain=args.project_chain,
        limit=4,
    )
    plan = build_search_plan(
        args.chain,
        args.node,
        path,
        args.keyword,
        args.industry,
        args.exclude,
        precision=args.precision,
        project_context=context if context.get("available") else None,
    )
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(json_dumps(plan["condition"], pretty=True) + "\n")
    if args.plan_output:
        with open(args.plan_output, "w", encoding="utf-8") as handle:
            handle.write(json_dumps(plan, pretty=True) + "\n")
    print_json(plan if args.explain else plan["condition"])


if __name__ == "__main__":
    main()
