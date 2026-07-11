import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "industry-chain-processing" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build_condition  # noqa: E402
import link_enterprises  # noqa: E402


SERVO_PATH = ["工业母机", "上游：核心零部件与基础材料", "伺服系统", "伺服驱动器"]


def iter_field_conditions(value):
    if isinstance(value, list):
        for item in value:
            yield from iter_field_conditions(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            if key in {"must", "should", "must_not"}:
                yield from iter_field_conditions(item)
            elif isinstance(item, list):
                yield key, item


class LinkingConditionTests(unittest.TestCase):
    def test_strict_plan_uses_role_and_project_node_keywords(self):
        project = {
            "available": True,
            "matched_nodes": [
                {
                    "node_name": "伺服驱动器",
                    "path": SERVO_PATH,
                    "condition_source": "high_screen_es_skill_template",
                    "condition_keywords": ["伺服驱动器", "运动控制", "上游", "核心零部件与基础材料"],
                    "condition": {"must": [{"operStatus_v2": [{"eq": [["营业"]]}]}]},
                }
            ],
        }
        plan = build_condition.build_search_plan(
            "工业母机",
            "伺服驱动器",
            SERVO_PATH,
            precision="strict",
            project_context=project,
        )
        self.assertEqual(plan["node_context"]["role"], "upstream")
        self.assertEqual(plan["node_context"]["canonical_path"], SERVO_PATH)
        self.assertIn("伺服驱动器", plan["keyword_profile"]["exact"])
        self.assertIn("运动控制", plan["keyword_profile"]["supporting"])
        self.assertNotIn("核心零部件与基础材料", plan["keyword_profile"]["exact"])
        self.assertTrue(plan["quality_checks"]["valid"])
        self.assertEqual(plan["condition_origin"], "generated_from_project_node")

    def test_generated_fields_respect_handaas_limits_and_noise_scope(self):
        plan = build_condition.build_search_plan(
            "工业母机",
            "伺服驱动器",
            SERVO_PATH,
            precision="strict",
        )
        condition = plan["condition"]
        for field, operations in iter_field_conditions(condition):
            limit = build_condition.FIELD_RULES.get(field, {}).get("max_keywords")
            if not limit:
                continue
            for operation in operations:
                for operator in ("in", "nin"):
                    values = operation.get(operator)
                    if isinstance(values, list):
                        self.assertLessEqual(len(values), limit, field)
        self.assertNotIn("must_not", condition)
        must = condition.get("must") or []
        name_noise = next(item["name"][0]["nin"] for item in must if "name" in item and "nin" in item["name"][0])
        business_noise = next(item["business"][0]["nin"] for item in must if "business" in item and "nin" in item["business"][0])
        self.assertIn("维修", name_noise)
        self.assertIn("经贸", name_noise)
        self.assertNotIn("维修", business_noise)

    def test_validator_rejects_unsupported_top_level_must_not(self):
        checks = build_condition.validate_condition_group({
            "must": [{"operStatus_v2": [{"eq": [["营业"]]}]}],
            "must_not": [{"name": [{"nin": ["贸易"]}]}],
        }, require_strong=False)
        self.assertFalse(checks["valid"])
        self.assertTrue(any("must_not" in error for error in checks["errors"]))

    def test_legacy_negative_group_is_migrated_to_must(self):
        normalized, migrated = build_condition.normalize_legacy_negative_groups({
            "must": [{"operStatus_v2": [{"eq": [["营业"]]}]}],
            "must_not": [{"name": [{"nin": ["贸易"]}]}],
        })
        self.assertTrue(migrated)
        self.assertNotIn("must_not", normalized)
        self.assertEqual(normalized["must"][-1], {"name": [{"nin": ["贸易"]}]})

    def test_strict_servo_plan_has_field_specific_recall_routes(self):
        plan = build_condition.build_search_plan(
            "工业母机",
            "伺服驱动器",
            SERVO_PATH,
            precision="strict",
        )
        routes = {item["id"]: item for item in plan["recall_routes"]}
        self.assertEqual(plan["recall_strategy"], "multi_route")
        self.assertEqual(
            list(routes),
            [
                "industry_business_consensus",
                "industry_registration_scope",
                "industry_business_keyword",
                "business_consensus_precision",
                "registration_scope_precision",
                "business_keyword_precision",
            ],
        )
        self.assertTrue(plan["node_context"]["industry_paths"])
        industry_keyword_fields = [field for field, _ in iter_field_conditions(routes["industry_business_keyword"]["condition"])]
        scope_fields = [field for field, _ in iter_field_conditions(routes["registration_scope_precision"]["condition"])]
        self.assertIn("industriesV2", industry_keyword_fields)
        self.assertIn("businessKeywords", industry_keyword_fields)
        self.assertIn("business", scope_fields)
        self.assertIn("desc", scope_fields)
        self.assertNotIn("businessKeywords", scope_fields)
        self.assertNotIn("industriesV2", scope_fields)
        for route in routes.values():
            self.assertTrue(route["quality_checks"]["strong_evidence_fields"])
        self.assertEqual(routes["industry_business_consensus"]["minimum_evidence_groups"], 3)
        self.assertEqual(routes["business_consensus_precision"]["minimum_evidence_groups"], 3)
        self.assertEqual(routes["business_keyword_precision"]["minimum_evidence_groups"], 2)

    def test_chain_name_alone_does_not_force_manufacturing_industry(self):
        plan = build_condition.build_search_plan(
            "工业母机",
            "CAD/CAM/CAE软件",
            ["工业母机", "上游：核心零部件与基础材料", "工业软件", "CAD/CAM/CAE软件"],
            precision="strict",
        )
        self.assertEqual(plan["node_context"]["industry_paths"], [])
        self.assertEqual(
            [item["id"] for item in plan["recall_routes"]],
            ["business_consensus_precision", "registration_scope_precision", "business_keyword_precision"],
        )

    def test_downstream_node_uses_operation_terms_not_manufacturing_terms(self):
        plan = build_condition.build_search_plan(
            "智能网联汽车",
            "Robotaxi运营服务",
            ["智能网联汽车", "下游：应用与运营", "出行服务", "Robotaxi运营服务"],
            precision="strict",
        )
        profile = plan["keyword_profile"]
        self.assertEqual(plan["node_context"]["role"], "downstream")
        self.assertTrue(any("运营" in item for item in profile["business"]))
        self.assertFalse(any(item.endswith("制造") for item in profile["business"]))

    def test_downstream_product_node_uses_manufacturing_terms(self):
        plan = build_condition.build_search_plan(
            "工业母机",
            "挖掘机",
            ["工业母机", "下游：应用领域", "工程机械", "挖掘机"],
            precision="strict",
        )
        profile = plan["keyword_profile"]
        self.assertIn("挖掘机制造", profile["action"])
        self.assertNotIn("挖掘机运营", profile["action"])
        self.assertTrue(plan["node_context"]["industry_paths"])

    def test_business_consensus_route_requires_keyword_and_scope_groups(self):
        plan = build_condition.build_search_plan(
            "工业母机",
            "伺服驱动器",
            SERVO_PATH,
            precision="strict",
        )
        route = next(item for item in plan["recall_routes"] if item["id"] == "business_consensus_precision")
        top_level_fields = []
        for clause in route["condition"]["must"]:
            if "businessKeywords" in clause:
                top_level_fields.append("businessKeywords")
            if "should" in clause:
                fields = set().union(*(item.keys() for item in clause["should"]))
                if fields == {"business", "desc"}:
                    top_level_fields.append("registration_scope")
        self.assertEqual(top_level_fields, ["businessKeywords", "registration_scope"])

    def test_parenthetical_node_expands_searchable_product_variants(self):
        plan = build_condition.build_search_plan(
            "工业母机",
            "加工中心（立式、卧式、龙门）",
            ["工业母机", "中游：机床设备", "金属切削机床", "加工中心（立式、卧式、龙门）"],
            precision="strict",
        )
        exact = plan["keyword_profile"]["exact"]
        self.assertIn("加工中心", exact)
        self.assertIn("立式加工中心", exact)
        self.assertIn("卧式加工中心", exact)
        self.assertIn("龙门加工中心", exact)
        self.assertNotIn("加工中心（立式、卧式、龙门）", exact)
        self.assertTrue(plan["node_context"]["industry_paths"])

    def test_operator_confirmed_project_condition_is_preserved(self):
        confirmed = {
            "must": [
                {"operStatus_v2": [{"eq": [["营业"]]}]},
                {"businessKeywords": [{"in": ["伺服驱动器"]}]},
            ]
        }
        project = {
            "available": True,
            "matched_nodes": [
                {
                    "node_name": "伺服驱动器",
                    "path": SERVO_PATH,
                    "condition_source": "operator_confirmed_high_screen",
                    "condition_keywords": ["伺服驱动器"],
                    "condition": confirmed,
                }
            ],
        }
        plan = build_condition.build_search_plan(
            "工业母机",
            "伺服驱动器",
            SERVO_PATH,
            project_context=project,
        )
        self.assertEqual(plan["condition"], confirmed)
        self.assertEqual(plan["condition_origin"], "operator_confirmed_project")


class CandidateReviewTests(unittest.TestCase):
    def setUp(self):
        self.profile = build_condition.build_keyword_profile("工业母机", "伺服驱动器", SERVO_PATH)
        self.company = {"id": "ent-1", "name": "测试伺服科技有限公司"}

    def test_independent_patent_tag_and_profile_evidence_confirms_link(self):
        evidence = {
            "企业简介": {"data": {"desc": "专注运动控制和伺服驱动产品研发。"}},
            "企业标签": {"data": {"businessTags": ["伺服系统", "伺服驱动器"]}},
            "专利搜索": {"data": {"resultList": [{"patentName": "一种伺服驱动器控制方法"}]}},
        }
        decision = link_enterprises.classify_candidate(
            self.company,
            evidence,
            "伺服驱动器",
            [],
            keyword_profile=self.profile,
        )
        self.assertEqual(decision["decision"], "confirmed")
        self.assertEqual(decision["business_fit"], "matched")
        self.assertGreaterEqual(decision["review_score"], 65)
        self.assertGreaterEqual(decision["evidence_source_count"], 2)
        self.assertGreaterEqual(decision["strong_source_count"], 1)

    def test_broad_automation_scope_does_not_confirm_exact_node(self):
        evidence = {
            "工商照面": {"data": {"business": "自动化设备销售、安装和技术服务。"}},
            "企业简介": {"data": {"desc": "提供工业自动化综合服务。"}},
        }
        decision = link_enterprises.classify_candidate(
            self.company,
            evidence,
            "伺服驱动器",
            [],
            keyword_profile=self.profile,
        )
        self.assertNotEqual(decision["decision"], "confirmed")
        self.assertNotEqual(decision["business_fit"], "matched")
        self.assertEqual(decision["strong_source_count"], 0)

    def test_patent_search_uses_enterprise_name_as_applicant(self):
        query = link_enterprises.evidence_query_for_company("专利搜索", self.company)
        self.assertEqual(query["keyword"], self.company["name"])
        self.assertEqual(query["key_type"], "申请人")

    def test_project_seed_is_a_recall_route_not_confirmation_evidence(self):
        company = {
            "id": "ent-seed",
            "name": "深圳市汇川技术股份有限公司",
            "recall_routes": ["project_seed"],
            "project_seeds": ["汇川技术（Inovance）"],
        }
        decision = link_enterprises.classify_candidate(
            company,
            {},
            "伺服驱动器",
            [],
            keyword_profile=self.profile,
        )
        self.assertEqual(decision["decision"], "uncertain")
        self.assertEqual(decision["strong_source_count"], 0)
        self.assertEqual(decision["recall_routes"], ["project_seed"])
        self.assertEqual(decision["recall_score"], 0)

    def test_seed_alias_resolves_legal_enterprise_name(self):
        rows = [
            {"id": "other", "name": "山东汇川机电设备有限公司"},
            {"id": "target", "name": "深圳市汇川技术股份有限公司"},
        ]
        selected = link_enterprises.select_seed_matches("汇川技术（Inovance）", rows)
        self.assertEqual(selected[0]["id"], "target")

    def test_group_seed_prefers_main_legal_entity_over_local_factory(self):
        rows = [
            {"id": "factory", "name": "永嘉县三菱电机厂"},
            {"id": "china", "name": "三菱电机(中国)有限公司"},
            {"id": "branch", "name": "三菱电机自动化(中国)有限公司深圳分公司"},
        ]
        selected = link_enterprises.select_seed_matches("三菱电机（Mitsubishi Electric）", rows)
        self.assertEqual(selected[0]["id"], "china")

    def test_generic_registered_scope_terms_do_not_create_conflicts(self):
        evidence = {
            "企业简介": {"data": {"desc": "研发生产伺服驱动器，并提供技术咨询和设备维修服务。"}},
            "企业标签": {"data": {"businessTags": ["伺服驱动器", "运动控制"]}},
            "专利搜索": {"data": {"resultList": [{"patentName": "一种伺服驱动器控制方法"}]}},
        }
        decision = link_enterprises.classify_candidate(
            self.company,
            evidence,
            "伺服驱动器",
            [],
            keyword_profile=self.profile,
        )
        self.assertEqual(decision["decision"], "confirmed")
        self.assertEqual(decision["conflict_hits"], [])


if __name__ == "__main__":
    unittest.main()
