import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "industry-chain-processing" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import render_report  # noqa: E402


class EnterpriseReportOutputTests(unittest.TestCase):
    def test_enterprise_node_analysis_has_dedicated_html_and_markdown(self):
        payload = {
            "report_type": "enterprise_node_analysis",
            "title": "测试企业伺服驱动器节点分析报告",
            "enterprise": "测试企业有限公司",
            "chain": "工业母机",
            "node": "伺服驱动器",
            "summary": "企业产品和专利证据共同指向伺服驱动器节点。",
            "enterprise_profile": {
                "name": "测试企业有限公司",
                "oper_status": "存续",
                "business_scope": "伺服驱动器研发与制造",
            },
            "node_mapping": {
                "canonical_chain": "工业母机",
                "primary_project_path": "工业母机 > 上游 > 伺服系统 > 伺服驱动器",
            },
            "fit_assessment": {
                "target_node": "伺服驱动器",
                "project_node": "伺服驱动器",
                "project_node_path": "工业母机 > 上游 > 伺服系统 > 伺服驱动器",
                "decision": "confirmed",
                "evidence_strength": "strong",
                "fit_score": 88,
                "reason": "工商、产品与专利证据一致",
            },
            "evidence_summary": [
                {
                    "product": "专利搜索",
                    "status": "available",
                    "signal_strength": "strong",
                    "matched_keywords": "伺服驱动器",
                    "key_findings": "伺服驱动控制专利",
                    "data_points": "2件",
                }
            ],
            "risk_flags": ["经营范围不能单独作为确认挂链依据。"],
            "evidence": {"专利搜索": {"raw": "should not render"}},
        }
        html = render_report.render_html(payload, payload["title"])
        markdown = render_report.render_markdown(payload, payload["title"])
        self.assertIn("企业产业链节点分析报告", html)
        self.assertIn("确认挂链", html)
        self.assertIn("证据核验", html)
        self.assertIn("## 二、产业链节点定位", markdown)
        self.assertNotIn("should not render", html)
        self.assertNotIn("原始数据", html)

    def test_single_node_linking_report_separates_decisions(self):
        payload = {
            "report_type": "enterprise_node_linking",
            "title": "伺服驱动器节点企业挂链报告",
            "chain": "工业母机",
            "node": "伺服驱动器",
            "path": ["工业母机", "上游", "伺服系统", "伺服驱动器"],
            "link_summary": {"candidate_count": 3, "confirmed": 1, "manual_review": 1, "rejected": 1, "evidence_reviewed": True},
            "preview": {"route_results": [{"route_id": "business_consensus_precision", "purpose": "业务共识", "priority": 5, "total": 12, "sample_count": 3}]},
            "decisions": [
                {"enterprise_name": "确认企业", "decision": "confirmed", "review_score": 86, "evidence_strength": "strong", "evidence_source_count": 3, "strong_source_count": 1, "matched_evidence": [{"source": "专利搜索"}], "reason": "多来源一致"},
                {"enterprise_name": "复核企业", "decision": "uncertain", "review_score": 42, "evidence_strength": "medium", "reason": "缺少强证据"},
                {"enterprise_name": "排除企业", "decision": "rejected", "review_score": 5, "evidence_strength": "weak", "reason": "无直接证据"},
            ],
        }
        html = render_report.render_html(payload, payload["title"])
        markdown = render_report.render_markdown(payload, payload["title"])
        self.assertIn("确认企业", html)
        self.assertIn("待复核企业", html)
        self.assertIn("排除企业", html)
        self.assertIn("## 三、确认挂链企业", markdown)
        self.assertIn("## 五、排除企业", markdown)

    def test_chain_linking_report_summarizes_nodes_and_enterprises(self):
        payload = {
            "report_type": "industry_chain_linking",
            "title": "工业母机产业链节点企业挂链总报告",
            "chain": "工业母机",
            "selection": {"selected_node_count": 2},
            "summary": {"completed_nodes": 2, "failed_nodes": 0, "candidate_count": 4, "confirmed": 2, "manual_review": 1, "rejected": 1},
            "nodes": [
                {
                    "node": "伺服驱动器",
                    "path": ["工业母机", "上游", "伺服系统", "伺服驱动器"],
                    "candidate_count": 2,
                    "confirmed": 1,
                    "manual_review": 1,
                    "rejected": 0,
                    "reviewed_enterprises": [
                        {"enterprise_name": "企业甲", "decision": "confirmed", "review_score": 88, "evidence_source_count": 3, "strong_source_count": 1, "reason": "多来源一致"},
                        {"enterprise_name": "企业乙", "decision": "uncertain", "review_score": 45, "evidence_source_count": 1, "strong_source_count": 0, "reason": "待补证"},
                    ],
                },
                {
                    "node": "加工中心",
                    "path": ["工业母机", "中游", "数控机床", "加工中心"],
                    "candidate_count": 2,
                    "confirmed": 1,
                    "manual_review": 0,
                    "rejected": 1,
                    "reviewed_enterprises": [{"enterprise_name": "企业丙", "decision": "confirmed", "review_score": 91, "evidence_source_count": 4, "strong_source_count": 2, "reason": "产品与专利一致"}],
                },
            ],
            "failures": [],
        }
        html = render_report.render_html(payload, payload["title"])
        markdown = render_report.render_markdown(payload, payload["title"])
        self.assertIn("节点覆盖总览", html)
        self.assertIn("企业甲", html)
        self.assertIn("企业丙", html)
        self.assertIn("## 二、节点覆盖明细", markdown)
        self.assertIn("## 三、企业挂链明细", markdown)

    def test_write_report_uses_extension_and_creates_parent(self):
        payload = {
            "report_type": "enterprise_node_linking",
            "title": "节点挂链报告",
            "chain": "工业母机",
            "node": "伺服驱动器",
            "link_summary": {},
            "decisions": [],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            output = pathlib.Path(temp_dir) / "reports" / "linking.md"
            result = render_report.write_report(payload, output)
            content = output.read_text(encoding="utf-8")
        self.assertEqual(result["format"], "markdown")
        self.assertIn("# 节点挂链报告", content)


if __name__ == "__main__":
    unittest.main()
