import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "industry-chain-processing" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import probe_business_evidence as probe  # noqa: E402


SERVO_PATH = ["工业母机", "上游：核心零部件与基础材料", "伺服系统", "伺服驱动器"]


class BusinessEvidenceProbeTests(unittest.TestCase):
    def test_combination_generation_is_bounded(self):
        groups = probe.combinations(["a", "b", "c", "d"], max_size=2)
        self.assertEqual(len(groups), 10)
        self.assertIn(["a", "b"], groups)
        self.assertNotIn(["a", "b", "c"], groups)

    def test_confusion_metrics(self):
        rows = [
            {"expected": "positive", "accept": True},
            {"expected": "positive", "accept": False},
            {"expected": "negative", "accept": False},
            {"expected": "negative", "accept": True},
        ]
        metrics = probe.confusion_metrics(rows, "accept")
        self.assertEqual(metrics["tp"], 1)
        self.assertEqual(metrics["fp"], 1)
        self.assertEqual(metrics["precision"], 0.5)
        self.assertEqual(metrics["balanced_accuracy"], 0.5)

    def test_medium_sources_can_judge_business_but_not_confirm_link(self):
        cases = [{
            "enterprise": "正样本企业",
            "chain": "工业母机",
            "node": "伺服驱动器",
            "path": SERVO_PATH,
            "expected": "positive",
        }]
        identities = {"正样本企业": {"name": "正样本企业", "name_id": "p1"}}
        evidence = {
            "正样本企业": {
                "企业简介": {"data": {"desc": "研发生产伺服驱动器和运动控制产品。"}},
                "企业标签": {"data": {"businessTags": ["伺服驱动器", "伺服系统"]}},
            }
        }
        result = probe.evaluate_combination(["企业简介", "企业标签"], cases, identities, evidence)
        self.assertEqual(result["business_judgment"]["recall"], 1.0)
        self.assertEqual(result["strict_link_confirmation"]["recall"], 0.0)

    def test_strong_plus_medium_sources_confirm_known_positive_and_reject_negative(self):
        cases = [
            {
                "enterprise": "正样本企业",
                "chain": "工业母机",
                "node": "伺服驱动器",
                "path": SERVO_PATH,
                "expected": "positive",
            },
            {
                "enterprise": "负样本企业",
                "chain": "工业母机",
                "node": "伺服驱动器",
                "path": SERVO_PATH,
                "expected": "negative",
            },
        ]
        identities = {
            "正样本企业": {"name": "正样本企业", "name_id": "p1"},
            "负样本企业": {"name": "负样本企业", "name_id": "n1"},
        }
        evidence = {
            "正样本企业": {
                "企业简介": {"data": {"desc": "专注伺服驱动器研发生产。"}},
                "企业标签": {"data": {"businessTags": ["伺服驱动器"]}},
                "专利搜索": {"data": {"resultList": [{"patentName": "伺服驱动器控制方法"}]}},
            },
            "负样本企业": {
                "企业简介": {"data": {"desc": "生产工程机械整机。"}},
                "企业标签": {"data": {"businessTags": ["挖掘机"]}},
                "专利搜索": {"data": {"resultList": [{"patentName": "挖掘机液压系统"}]}},
            },
        }
        result = probe.evaluate_combination(
            ["企业简介", "企业标签", "专利搜索"],
            cases,
            identities,
            evidence,
        )
        self.assertEqual(result["strict_link_confirmation"]["precision"], 1.0)
        self.assertEqual(result["strict_link_confirmation"]["recall"], 1.0)
        self.assertEqual(result["strict_link_confirmation"]["specificity"], 1.0)


if __name__ == "__main__":
    unittest.main()
