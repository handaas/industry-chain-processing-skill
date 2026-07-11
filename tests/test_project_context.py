import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "industry-chain-processing" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import project_context  # noqa: E402


def fake_chain(name, node_names):
    return {
        "chain_name": name,
        "source": "sqlite_archive",
        "enterprise_count_cache": 10,
        "updated_at": "2026-01-01",
        "l5_nodes": [{"name": node, "path": [name, "L2", "L3", node]} for node in node_names],
    }


class ProjectContextTests(unittest.TestCase):
    def test_project_root_discovers_generic_working_directory_child(self):
        original_cwd = pathlib.Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir) / "industry-chain-map"
            (root / "src" / "data").mkdir(parents=True)
            try:
                os.chdir(temp_dir)
                with mock.patch.dict(
                    os.environ,
                    {"INDUSTRY_CHAIN_PROJECT_ROOT": "", "INDUSTRY_CHAIN_MAP_ROOT": ""},
                ):
                    self.assertEqual(project_context.resolve_project_root(), root.resolve())
            finally:
                os.chdir(original_cwd)

    def test_smart_manufacturing_does_not_match_smart_terminal(self):
        chosen = project_context.choose_chain([fake_chain("智能终端", ["智能手机"])], "智能制造")
        self.assertIsNone(chosen)

    def test_smart_manufacturing_composite_reuses_source_chains(self):
        chains = [
            fake_chain("半导体与集成电路", ["工业控制芯片"]),
            fake_chain("智能传感器", ["机器视觉传感器"]),
            fake_chain("精密仪器设备", ["在线检测设备"]),
            fake_chain("工业母机", ["数控机床"]),
            fake_chain("智能机器人", ["工业机器人"]),
            fake_chain("激光与增材制造", ["激光加工设备"]),
            fake_chain("软件与信息服务", ["制造执行系统"]),
        ]
        composite = project_context.build_smart_manufacturing_composite(chains)
        self.assertEqual(composite["chain_name"], "智能制造")
        self.assertEqual(composite["stats"]["l2"], 4)
        self.assertGreaterEqual(composite["stats"]["l5"], 15)
        self.assertIn("工业母机", composite["source_chains"])
        paths = [node["path"] for node in composite["l5_nodes"]]
        self.assertIn(["智能制造", "中游：智能装备与工艺系统", "数控机床与工业母机", "数控机床"], paths)
        self.assertTrue(any(path[-1] == "智能工厂总体解决方案" for path in paths))


if __name__ == "__main__":
    unittest.main()
