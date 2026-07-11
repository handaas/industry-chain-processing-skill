import argparse
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "industry-chain-processing" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import enterprise_chain_positioning as positioning  # noqa: E402
import render_report  # noqa: E402


def fake_chains():
    return [
        {
            "chain_name": "智能机器人",
            "chain_id": "chain_robot",
            "source": "sqlite_archive",
            "l5_nodes": [
                {
                    "name": "工业机器人系统集成",
                    "path": ["智能机器人", "中游：机器人本体与系统集成", "系统集成", "工业机器人系统集成"],
                },
                {
                    "name": "减速器",
                    "path": ["智能机器人", "上游：核心零部件", "传动系统", "减速器"],
                },
            ],
        },
        {
            "chain_name": "软件与信息服务",
            "chain_id": "chain_software",
            "source": "sqlite_archive",
            "l5_nodes": [
                {
                    "name": "企业资源管理 (ERP)",
                    "path": ["软件与信息服务", "中游：软件产品", "管理软件", "企业资源管理 (ERP)"],
                }
            ],
        },
    ]


def evidence_fixture():
    return {
        "企业业务": {
            "data": {
                "resultList": [
                    {
                        "productName": "工业机器人系统集成",
                        "productDomain": "机器人自动化生产线",
                        "desc": "面向制造企业提供工业机器人系统集成和自动化产线解决方案。",
                    }
                ]
            }
        },
        "专利搜索": {
            "data": {
                "resultList": [
                    {"patentName": "一种工业机器人系统集成控制方法"},
                ]
            }
        },
        "企业标签": {"data": {"businessTags": ["工业机器人", "智能制造"]}},
    }


class EnterpriseChainPositioningTests(unittest.TestCase):
    def test_enterprise_resolution_prefers_exact_name(self):
        rows = [
            {"name": "深圳测试科技有限公司", "nameId": "1"},
            {"name": "深圳测试科技股份有限公司", "nameId": "2"},
        ]
        identity = positioning.choose_enterprise(rows, "深圳测试科技股份有限公司")
        self.assertEqual(identity["name_id"], "2")

    def test_business_and_patent_evidence_rank_correct_node(self):
        signals = positioning.evidence_signals(evidence_fixture())
        ranked = positioning.rank_positions(fake_chains(), signals)
        self.assertEqual(ranked["nodes"][0]["chain"], "智能机器人")
        self.assertEqual(ranked["nodes"][0]["l5_node"], "工业机器人系统集成")
        self.assertGreaterEqual(ranked["nodes"][0]["score"], 72)
        self.assertEqual(ranked["chains"][0]["chain"], "智能机器人")

    def test_project_anchor_and_role_weight_beat_generic_downstream_application(self):
        chains = [
            {
                "chain_name": "智能传感器",
                "chain_id": "sensor",
                "l5_nodes": [
                    {
                        "name": "工业自动化",
                        "path": ["智能传感器", "下游：应用领域", "工业", "工业自动化"],
                    }
                ],
            },
            {
                "chain_name": "工业母机",
                "chain_id": "machine",
                "l5_nodes": [
                    {
                        "name": "伺服驱动器",
                        "path": ["工业母机", "上游：核心零部件", "伺服系统", "伺服驱动器"],
                        "representative_companies": ["汇川技术（Inovance）"],
                    }
                ],
            },
        ]
        evidence = {
            "企业简介": {"data": {"desc": "公司聚焦工业自动化控制与驱动技术。"}},
            "企业标签": {"data": {"businessTags": ["工业自动化控制产品", "伺服系统", "伺服驱动器"]}},
            "企业招投标信息": {"data": {"resultList": [{"title": "采购伺服驱动器"}]}},
        }
        signals = positioning.evidence_signals(evidence)
        ranked = positioning.rank_positions(
            chains,
            signals,
            enterprise_name="深圳市汇川技术股份有限公司",
        )
        self.assertEqual(ranked["chains"][0]["chain"], "工业母机")
        self.assertEqual(ranked["primary_node"]["l5_node"], "伺服驱动器")
        self.assertEqual(ranked["primary_node"]["project_anchor"]["representative"], "汇川技术（Inovance）")
        generic = positioning.score_node(
            chains[0],
            chains[0]["l5_nodes"][0],
            signals,
            enterprise_name="深圳市汇川技术股份有限公司",
        )
        self.assertEqual(generic["role_adjustment"], "下游应用场景降权")
        self.assertLess(generic["score"], ranked["primary_node"]["score"])

    def test_nested_mcp_product_error_is_reported(self):
        payload = {
            "mode": "mcp",
            "product": "企业业务",
            "data": {"error": "请求异常", "message": "HandaaS 接口未返回数据。"},
        }
        self.assertEqual(positioning.evidence_error(payload), "请求异常：HandaaS 接口未返回数据。")
        rows = positioning.evidence_summary_rows({"企业业务": payload}, [])
        self.assertEqual(rows[0]["status"], "error")
        self.assertIn("HandaaS 接口未返回数据", rows[0]["representative_evidence"])
        self.assertEqual(render_report.evidence_status_label(rows[0]["status"]), "接口异常")

    def test_offline_report_requires_only_enterprise_name(self):
        fixture = {
            "identity": {"name": "测试机器人有限公司", "name_id": "ent_1"},
            "candidates": [{"name": "测试机器人有限公司", "name_id": "ent_1"}],
            "evidence": evidence_fixture(),
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            path = pathlib.Path(temp_dir) / "evidence.json"
            path.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")
            args = argparse.Namespace(
                enterprise="测试机器人有限公司",
                config=None,
                project_root=None,
                evidence_product=[],
                evidence_input=str(path),
                max_nodes=12,
                max_chains=5,
                timeout=30,
                local=False,
                title=None,
                output=None,
            )
            with mock.patch.object(positioning, "load_project_chains", return_value=(pathlib.Path(temp_dir), fake_chains())):
                report = positioning.build_report(args)
        self.assertEqual(report["report_type"], "enterprise_chain_positioning")
        self.assertEqual(report["primary_position"]["chain"], "智能机器人")
        self.assertEqual(report["primary_position"]["l5_node"], "工业机器人系统集成")
        self.assertEqual(report["primary_position"]["status"], "明确归属")
        self.assertIn("工业机器人系统集成", report["summary"])
        html = render_report.render_html(report, report["title"])
        markdown = render_report.render_markdown(report, report["title"])
        self.assertIn("主归属产业链环节", html)
        self.assertIn("候选产业链对比", html)
        self.assertIn("证据覆盖与关键命中", html)
        self.assertIn("工业机器人系统集成", html)
        self.assertIn("## 二、主归属产业链环节", markdown)
        self.assertNotIn("原始 JSON", html)


if __name__ == "__main__":
    unittest.main()
