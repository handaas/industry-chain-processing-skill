import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "industry-chain-processing" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import common  # noqa: E402
import mcp_client  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
