import json
import pathlib
import subprocess
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "industry-chain-processing" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import common  # noqa: E402
import enterprise_search_preview  # noqa: E402
import mcp_client  # noqa: E402
import validate_config as config_validator  # noqa: E402


class McpConfigTests(unittest.TestCase):
    def test_token_builds_encoded_official_remote_url(self):
        url = common.build_mcp_url(token="a token,+")
        self.assertTrue(url.startswith("https://mcp.handaas.com/industry-chain/industry_chain?token="))
        self.assertIn("a%20token%2C%2B", url)

    def test_full_remote_url_does_not_duplicate_existing_token(self):
        url = common.build_mcp_url("https://example.test/mcp?token=existing", "second")
        self.assertEqual(url, "https://example.test/mcp?token=existing")

    def test_redaction_hides_url_and_mapping_tokens(self):
        redacted = common.redact({
            "url": "https://example.test/mcp?token=sensitive",
            "token": "sensitive",
        })
        self.assertNotIn("sensitive", str(redacted))
        self.assertIn("REDACTED", redacted["url"])

    def test_tool_count_supports_sdk_and_plain_list_shapes(self):
        self.assertEqual(mcp_client.tool_count({"tools": [{"name": "a"}, {"name": "b"}]}), 2)
        self.assertEqual(mcp_client.tool_count([{"name": "a"}]), 1)
        self.assertEqual(mcp_client.tool_count({"unexpected": []}), 0)

    def test_high_screen_reuses_unified_handaas_credentials(self):
        config = {
            "handaas": {
                "base_url": "https://console.handaas.com",
                "integrator_id": "integrator-id",
                "secret_id": "secret-id",
                "secret_key": "secret-key",
                "products": {
                    "高筛企业清单": {
                        "product_id": "690dcb1b9c9dc8d0ff3c40eb",
                        "default_page_size": 50,
                    }
                },
            }
        }
        section = common.get_high_screen_section(config)
        self.assertEqual(section["secret_id"], "secret-id")
        self.assertEqual(section["secret_key"], "secret-key")
        self.assertEqual(section["product_id"], "690dcb1b9c9dc8d0ff3c40eb")
        self.assertEqual(
            section["url"],
            "https://console.handaas.com/api/v1/integrator/call_api/integrator-id",
        )
        self.assertEqual(section["source"], "handaas.products.高筛企业清单")

    def test_legacy_high_screen_section_remains_readable_for_migration(self):
        section = common.get_high_screen_section({
            "high_screen": {
                "url": "https://example.test/high-screen",
                "product_id": "product",
                "secret_id": "id",
                "secret_key": "key",
            }
        })
        self.assertEqual(section["source"], "legacy_high_screen")

    def test_example_config_validates_without_duplicate_high_screen_credentials(self):
        config = common.load_json_file(ROOT / "industry-chain-processing/assets/config.example.json")
        result = config_validator.validate(config, allow_placeholders=True)
        self.assertTrue(result["ok"])
        self.assertTrue(result["modes"]["local_credentials"]["ok"])
        self.assertNotIn("high_screen", config)

    def test_local_high_screen_request_sends_only_filter_param(self):
        section = common.get_high_screen_section({
            "handaas": {
                "base_url": "https://console.handaas.com",
                "integrator_id": "integrator-id",
                "secret_id": "secret-id",
                "secret_key": "secret-key",
                "products": {"高筛企业清单": "690dcb1b9c9dc8d0ff3c40eb"},
            }
        })
        request = enterprise_search_preview.build_enterprise_search_request(
            section,
            {"must": [{"name": [{"in": ["汇川技术"]}]}]},
            page_index=2,
            page_size=20,
        )
        self.assertEqual(set(request["params"]), {"filter"})

    def test_local_preview_cli_uses_unified_config_without_pagination_params(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "enterprise_search_preview.py"),
                "--local",
                "--dry-run",
                "--config",
                str(ROOT / "industry-chain-processing/assets/config.example.json"),
                "--filter-json",
                '{"must":[{"name":[{"in":["汇川技术"]}]}]}',
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(set(payload["request"]["params"]), {"filter"})

    def test_remote_preview_prefers_complete_mcp_high_screen_tool(self):
        calls = []
        original = enterprise_search_preview.call_tool
        condition = {"must": [{"name": [{"in": ["汇川技术"]}]}]}

        def fake_call(tool, arguments, **kwargs):
            calls.append((tool, arguments))
            return {"total": 2, "resultList": [{"nameId": "1", "name": "深圳市汇川技术股份有限公司"}]}

        try:
            enterprise_search_preview.call_tool = fake_call
            result = enterprise_search_preview.call_remote_enterprise_search_preview(
                condition,
                chain="工业母机",
                node="伺服驱动器",
            )
        finally:
            enterprise_search_preview.call_tool = original

        self.assertEqual(calls, [("advanced_filter_get_enterprise_list", {"filter": condition})])
        self.assertEqual(result["mode"], "mcp_high_screen")
        self.assertFalse(result["precision_limited"])
        self.assertEqual(result["total"], 2)

    def test_remote_preview_falls_back_only_for_older_mcp(self):
        calls = []
        original = enterprise_search_preview.call_tool
        condition = {"must": [{"businessKeywords": [{"in": ["伺服驱动器"]}]}]}

        def fake_call(tool, arguments, **kwargs):
            calls.append(tool)
            if tool == "advanced_filter_get_enterprise_list":
                raise RuntimeError("tool not found")
            return {"total": 1, "resultList": [{"nameId": "1", "name": "测试伺服有限公司"}]}

        try:
            enterprise_search_preview.call_tool = fake_call
            result = enterprise_search_preview.call_remote_enterprise_search_preview(
                condition,
                chain="工业母机",
                node="伺服驱动器",
            )
        finally:
            enterprise_search_preview.call_tool = original

        self.assertEqual(calls[:2], ["advanced_filter_get_enterprise_list", "enterprise_get_keyword_search"])
        self.assertTrue(result["precision_limited"])
        self.assertEqual(result["search_tools"], ["enterprise_get_keyword_search"])


if __name__ == "__main__":
    unittest.main()
