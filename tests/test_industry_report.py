import pathlib
import sys
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "industry-chain-processing" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import compose_industry_report  # noqa: E402
import render_report  # noqa: E402


class IndustryReportTests(unittest.TestCase):
    def assert_complete_graph(self, tree):
        self.assertTrue(compose_industry_report.graph_tree_is_complete(tree))
        stats = compose_industry_report.graph_tree_stats(tree)
        self.assertGreater(stats["l2"], 0)
        self.assertGreater(stats["l3"], 0)
        self.assertGreater(stats["l5"], 0)
        for section in tree["children"]:
            self.assertTrue(section["children"])
            for module in section["children"]:
                self.assertTrue(module["children"])

    def test_fallback_report_always_builds_nonempty_l2_l3_l5_graph(self):
        with mock.patch.object(compose_industry_report, "build_project_context", return_value={"available": False}):
            payload = compose_industry_report.build_payload(
                {},
                chain_arg="生物制药",
                node_arg="抗体药物",
            )
        self.assert_complete_graph(payload["project_graph_tree"])
        self.assertEqual(payload["project_graph_summary"]["graph_validation"], "complete")
        self.assertGreater(payload["project_graph_summary"]["l5_count"], 0)
        html = render_report.render_chain_analysis_html(payload, payload["title"])
        self.assertIn("抗体药物", html)
        self.assertNotIn("暂无 L5 节点", html)

    def test_available_but_empty_project_graph_is_repaired_before_rendering(self):
        empty_project = {
            "available": True,
            "chain": {"name": "空图谱产业", "id": "empty"},
            "stats": {"l2": 0, "l3": 0, "l5": 0},
            "value_chain": [],
            "l5_nodes": [],
            "matched_nodes": [],
        }
        with mock.patch.object(compose_industry_report, "build_project_context", return_value=empty_project):
            payload = compose_industry_report.build_payload({}, chain_arg="空图谱产业", node_arg="核心设备")
        self.assert_complete_graph(payload["project_graph_tree"])
        self.assertGreaterEqual(payload["project_graph_summary"]["l2_count"], 3)
        self.assertGreater(payload["project_graph_summary"]["l5_count"], 0)

    def test_renderer_rejects_unrepairable_empty_industry_graph(self):
        payload = {
            "report_type": "industry_chain_analysis",
            "title": "空图谱报告",
            "chain": "空图谱产业",
            "project_graph_tree": {"name": "空图谱产业", "children": []},
            "value_chain": [],
        }
        with self.assertRaisesRegex(ValueError, "拒绝生成空图谱报告"):
            render_report.render_chain_analysis_html(payload, payload["title"])
        with self.assertRaisesRegex(ValueError, "拒绝生成空图谱报告"):
            render_report.render_chain_analysis_markdown(payload, payload["title"])

    def test_optional_l4_path_keeps_last_item_as_l5(self):
        tree = compose_industry_report.project_graph_tree(
            {
                "l5_nodes": [{
                    "path": ["智能制造", "中游", "工业软件", "生产管理", "制造执行系统"],
                }]
            },
            "智能制造",
        )
        self.assert_complete_graph(tree)
        self.assertEqual(tree["children"][0]["children"][0]["children"][0]["name"], "制造执行系统")

    def test_professional_summary_uses_graph_and_external_context(self):
        summary = compose_industry_report.build_professional_summary(
            "智能网联汽车",
            "自动驾驶",
            {"l2_count": 3, "l3_count": 13, "l5_count": 49},
            [
                {
                    "l2_segment": "上游：基础元器件与技术支持",
                    "l3_segments": "核心芯片、传感器",
                },
                {
                    "l2_segment": "中游：系统集成与整车制造",
                    "l3_segments": "智能驾驶系统、智能座舱系统",
                },
                {
                    "l2_segment": "下游：应用与服务",
                    "l3_segments": "出行服务、智慧交通",
                },
            ],
            [
                {
                    "topic": "准入试点",
                    "finding": "智能网联汽车准入和上路通行试点持续推进。",
                    "source": "工业和信息化部",
                }
            ],
            [
                {
                    "node_name": "自动驾驶解决方案",
                    "path": "智能网联汽车 > 中游：系统集成与整车制造 > 智能驾驶系统 > 自动驾驶解决方案",
                }
            ],
        )
        self.assertIn("3 个 L2", summary)
        self.assertIn("49 个 L5", summary)
        self.assertIn("工业和信息化部", summary)
        self.assertIn("自动驾驶解决方案", summary)
        self.assertNotIn("联网收集", summary)
        self.assertNotIn("用于增强", summary)

    def test_report_abstract_is_cover_length_and_structure_focused(self):
        abstract = compose_industry_report.build_report_abstract(
            "智能制造",
            {"l2_count": 4, "l3_count": 8, "l5_count": 70},
            [
                {"l2_segment": "上游：工业基础与核心部件"},
                {"l2_segment": "中游：智能装备与工艺系统"},
                {"l2_segment": "下游：智能工厂集成与行业应用"},
            ],
            [{"topic": "智能制造标准化"}, {"topic": "智能工厂建设"}],
        )
        self.assertIn("4 个 L2", abstract)
        self.assertIn("70 个 L5", abstract)
        self.assertIn("智能制造标准化", abstract)
        self.assertLess(len(abstract), 420)

    def test_professional_structure_builders(self):
        value_chain = [
            {"l2_segment": "上游：基础部件", "l3_count": 1, "l5_count": 2, "l3_segments": "工业芯片", "l5_samples": "AI芯片、控制芯片"},
            {"l2_segment": "中游：装备系统", "l3_count": 1, "l5_count": 2, "l3_segments": "工业机器人", "l5_samples": "协作机器人、控制器"},
            {"l2_segment": "下游：场景应用", "l3_count": 1, "l5_count": 2, "l3_segments": "工厂集成", "l5_samples": "智能工厂、数字化车间"},
        ]
        graph_tree = {
            "name": "智能制造",
            "children": [
                {"name": "上游：基础部件", "children": [{"name": "工业芯片", "children": [{"name": "AI芯片"}, {"name": "控制芯片"}]}]},
            ],
        }
        segments = compose_industry_report.segment_analysis_rows(value_chain)
        nodes = compose_industry_report.key_node_system_rows(graph_tree)
        flows = compose_industry_report.value_flow_rows(value_chain)
        features = compose_industry_report.structural_characteristic_rows(
            "智能制造", {"l2_count": 3, "l3_count": 3, "l5_count": 6}, value_chain
        )
        self.assertEqual(len(segments), 3)
        self.assertEqual(segments[0]["stage"], "上游")
        self.assertEqual(nodes[0]["l3_module"], "工业芯片")
        self.assertEqual(flows[0]["relationship"], "基础供给")
        self.assertEqual(flows[1]["relationship"], "集成转化")
        self.assertEqual(len(features), 4)

    def test_node_name_parser_preserves_parenthetical_lists(self):
        names = compose_industry_report.split_names(
            "图像传感器、物理量传感器（温度、压力、湿度、流量）、机器视觉系统"
        )
        self.assertEqual(
            names,
            ["图像传感器", "物理量传感器（温度、压力、湿度、流量）", "机器视觉系统"],
        )

    def test_commercial_renderer_hides_internal_sections(self):
        payload = {
            "report_type": "industry_chain_analysis",
            "title": "智能网联汽车产业链分析报告",
            "chain": "智能网联汽车",
            "node": "自动驾驶",
            "summary": "专业摘要。",
            "project_graph_summary": {"l2_count": 1, "l3_count": 1, "l5_count": 1},
            "level_definitions": [],
            "hierarchy_analysis": [],
            "priority_segments": [],
            "project_graph_tree": {
                "name": "智能网联汽车",
                "children": [
                    {
                        "name": "中游",
                        "children": [
                            {"name": "智能驾驶系统", "children": [{"name": "自动驾驶解决方案"}]}
                        ],
                    }
                ],
            },
            "candidates": [{"name": "不应展示的企业"}],
            "recommendations": ["不应展示的建议"],
        }
        html = render_report.render_html(payload, payload["title"])
        self.assertIn("产业链图谱", html)
        self.assertIn("grid-template-columns: repeat(1, minmax(0, 1fr))", html)
        self.assertNotIn("不应展示的企业", html)
        self.assertNotIn("不应展示的建议", html)
        self.assertNotIn("原始数据", html)
        self.assertNotIn("挂链", html)

    def test_commercial_renderer_uses_short_links_and_wrapped_graph_columns(self):
        payload = {
            "report_type": "industry_chain_analysis",
            "title": "智能制造产业链分析报告",
            "chain": "智能制造",
            "abstract": "短版专业摘要。",
            "summary": "不应优先展示的长版摘要。",
            "market_context": [{"topic": "标准", "finding": "标准化推进。", "url": "https://example.com/policy"}],
            "industry_definition": [{"dimension": "产业定义", "content": "智能制造完整价值体系。"}],
            "segment_analysis": [{"segment": "上游", "stage": "上游", "functional_positioning": "基础供给。", "composition": "芯片", "representative_nodes": "AI芯片", "scale": "L3 1 个；L5 1 个", "linkage": "向中游供给。"}],
            "key_node_system": [{"l2_segment": "上游", "l3_module": "芯片", "node_count": 1, "capability_boundary": "提供计算能力。", "representative_nodes": "AI芯片"}],
            "value_flow": [{"from_segment": "上游", "to_segment": "中游", "relationship": "基础供给", "transmission_content": "芯片", "transmission_logic": "形成装备基础。"}],
            "structural_characteristics": [{"feature": "多层级专业分工", "evidence": "包含多个层级。", "interpretation": "构成复合产业体系。"}],
            "project_graph_tree": {
                "name": "智能制造",
                "children": [
                    {"name": "上游", "children": [{"name": "基础部件", "children": [{"name": "工业芯片"}]}]},
                    {"name": "中游", "children": [{"name": "智能装备", "children": [{"name": "工业机器人"}]}]},
                    {"name": "下游", "children": [{"name": "系统集成", "children": [{"name": "智能工厂"}]}]},
                    {"name": "应用", "children": [{"name": "行业场景", "children": [{"name": "数字化车间"}]}]},
                ],
            },
        }
        html = render_report.render_html(payload, payload["title"])
        self.assertIn("短版专业摘要", html)
        self.assertNotIn("不应优先展示的长版摘要", html)
        self.assertIn("grid-template-columns: repeat(2, minmax(0, 1fr))", html)
        self.assertIn(".cover-grid { grid-template-columns:190px minmax(0,1fr)", html)
        self.assertIn(".graph-l2 { break-inside:avoid", html)
        self.assertIn(">查看原文</a>", html)
        self.assertNotIn(">https://example.com/policy</td>", html)
        self.assertNotIn("挂链", html)
        self.assertNotIn("联网收集", html)
        self.assertNotIn("用于增强", html)
        self.assertNotIn("分析口径", html)
        self.assertIn("政策导向、市场演进与技术路线", html)
        self.assertIn("产业定义与层级口径", html)
        self.assertIn("价值环节深度解析", html)
        self.assertIn("关键节点与产品技术体系", html)
        self.assertIn("价值传导与协同关系", html)
        self.assertIn("产业结构特征", html)
        self.assertNotIn("关键环节与结构洞察", html)
        self.assertNotIn(">high<", html)
        self.assertNotIn(">medium<", html)


if __name__ == "__main__":
    unittest.main()
