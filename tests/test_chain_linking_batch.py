import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "industry-chain-processing" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import link_chain_nodes  # noqa: E402


class ChainLinkingBatchTests(unittest.TestCase):
    def setUp(self):
        self.nodes = [
            {
                "name": "伺服驱动器",
                "path": ["工业母机", "上游：核心零部件与基础材料", "伺服系统", "伺服驱动器"],
            },
            {
                "name": "加工中心",
                "path": ["工业母机", "中游：整机与制造系统", "数控机床", "加工中心"],
            },
            {
                "name": "设备运维服务",
                "path": ["工业母机", "下游：应用与服务", "工业服务", "设备运维服务"],
            },
        ]

    def test_select_nodes_filters_role_pattern_and_limit(self):
        selected = link_chain_nodes.select_nodes(
            self.nodes,
            roles=["upstream"],
            node_pattern="伺服|驱动",
            max_nodes=1,
        )
        self.assertEqual([item["name"] for item in selected], ["伺服驱动器"])
        self.assertEqual(selected[0]["role"], "upstream")

    def test_zero_max_nodes_means_all_matching_nodes(self):
        selected = link_chain_nodes.select_nodes(self.nodes, max_nodes=0)
        self.assertEqual(len(selected), 3)

    def test_anchored_pattern_matches_node_name(self):
        selected = link_chain_nodes.select_nodes(
            self.nodes,
            node_pattern="^伺服驱动器$",
            max_nodes=0,
        )
        self.assertEqual([item["name"] for item in selected], ["伺服驱动器"])

    def test_node_file_name_is_stable_and_ascii(self):
        first = link_chain_nodes.node_file_name(2, "伺服驱动器")
        second = link_chain_nodes.node_file_name(2, "伺服驱动器")
        self.assertEqual(first, second)
        self.assertRegex(first, r"^node-0003-[0-9a-f]{10}\.json$")


if __name__ == "__main__":
    unittest.main()
