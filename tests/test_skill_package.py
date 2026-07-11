import json
import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL = ROOT / "industry-chain-processing"


class SkillPackageTests(unittest.TestCase):
    def test_required_skill_metadata(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
        self.assertIsNotNone(match)
        frontmatter = match.group(1)
        self.assertIn("name: industry-chain-processing", frontmatter)
        self.assertIn("description:", frontmatter)

    def test_json_assets_are_valid(self):
        for path in (SKILL / "assets").glob("*.json"):
            with self.subTest(path=path.name):
                json.loads(path.read_text(encoding="utf-8"))

    def test_documented_scripts_exist(self):
        required = {
            "compose_industry_report.py",
            "policy_analysis.py",
            "enterprise_node_report.py",
            "enterprise_chain_positioning.py",
            "link_enterprises.py",
            "link_chain_nodes.py",
            "probe_business_evidence.py",
            "tune_search_conditions.py",
            "render_report.py",
            "mcp_client.py",
        }
        existing = {path.name for path in (SKILL / "scripts").glob("*.py")}
        self.assertTrue(required.issubset(existing))

    def test_public_files_do_not_contain_personal_absolute_paths(self):
        candidates = [ROOT / "README.md", *SKILL.rglob("*.md"), *SKILL.rglob("*.py")]
        for path in candidates:
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertNotIn("/" + "Users/", path.read_text(encoding="utf-8"))

    def test_readme_uses_handaas_repository_urls(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("github.com/handaas/industry-chain-processing-skill", text)
        self.assertIn("github.com/handaas/industry-chain-mcp-server", text)
        self.assertNotIn("github.com/" + "sunjackson/industry-chain-processing-skill", text)


if __name__ == "__main__":
    unittest.main()
