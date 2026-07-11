import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "industry-chain-processing" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import policy_analysis  # noqa: E402
import render_report  # noqa: E402


class PolicyAnalysisTests(unittest.TestCase):
    def test_parse_regions_deduplicates_and_accepts_csv(self):
        self.assertEqual(
            policy_analysis.parse_regions(["国家部委", "广东省,上海"], "广东省,江苏省"),
            ["国家部委", "广东省", "上海", "江苏省"],
        )

    def test_web_context_loader_keeps_source_fields(self):
        payload = {
            "policy_context": [
                {
                    "region": "广东省",
                    "topic": "场景示范",
                    "finding": "推进智能网联汽车道路测试和示范应用。",
                    "source": "广东省人民政府",
                    "url": "https://www.gd.gov.cn/example",
                    "date": "2026-01-01",
                }
            ]
        }
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "context.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            items = policy_analysis.load_web_context(str(path))
        self.assertEqual(items[0]["region"], "广东省")
        self.assertEqual(items[0]["source"], "广东省人民政府")
        self.assertTrue(items[0]["url"].startswith("https://"))

    def test_build_payload_works_offline_with_web_context(self):
        web_context = [
            {
                "region": "国家部委",
                "topic": "准入试点",
                "finding": "推进智能网联汽车准入和上路通行试点。",
                "source": "工业和信息化部",
                "url": "https://www.miit.gov.cn/example",
                "date": "2026-01-01",
            },
            {
                "region": "广东省",
                "topic": "示范应用",
                "finding": "支持道路测试、示范运营和基础设施建设。",
                "source": "广东省人民政府",
                "url": "https://www.gd.gov.cn/example",
                "date": "2026-02-01",
            },
        ]
        payload = policy_analysis.build_payload(
            chain="智能汽车",
            keyword="智能网联汽车 自动驾驶",
            regions=["国家部委", "广东省"],
            pn_type="全部",
            policy_start="2025-01-01",
            policy_end=None,
            page_size=5,
            config_path=None,
            skip_mcp=True,
            dry_run=False,
            web_context=web_context,
        )
        self.assertEqual(payload["report_type"], "policy_analysis")
        self.assertEqual(len(payload["mcp_queries"]), 2)
        self.assertEqual(payload["data_quality"]["web_policy_count"], 2)
        self.assertEqual([row["region"] for row in payload["regional_policy_analysis"]], ["国家部委", "广东省"])
        self.assertTrue(payload["policy_dimensions"])

        html = render_report.render_html(payload, payload["title"])
        markdown = render_report.render_markdown(payload, payload["title"])
        self.assertIn("各地政策情况对比", html)
        self.assertIn("代表性政策与联网依据", html)
        self.assertIn("各地政策情况对比", markdown)
        self.assertNotIn("展开 JSON", html)


if __name__ == "__main__":
    unittest.main()
