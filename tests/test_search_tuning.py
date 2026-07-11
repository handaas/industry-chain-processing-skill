import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "industry-chain-processing" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import tune_search_conditions as tuning  # noqa: E402


class SearchTuningMetricTests(unittest.TestCase):
    def setUp(self):
        self.labels = {
            "positive_enterprises": ["甲伺服科技有限公司", "乙运动控制股份有限公司"],
            "negative_enterprises": ["丙培训咨询有限公司"],
            "ratings": {},
        }

    def test_precision_mrr_and_dcg_use_enterprise_judgments(self):
        names = ["甲伺服科技有限公司", "丙培训咨询有限公司", "乙运动控制股份有限公司"]
        precision = tuning.precision_at_k(names, self.labels, 3)
        self.assertEqual(precision["judged"], 3)
        self.assertAlmostEqual(precision["precision"], 2 / 3, places=4)
        self.assertAlmostEqual(precision["judged_precision"], 2 / 3, places=4)
        self.assertEqual(tuning.mean_reciprocal_rank(names, self.labels), 1.0)
        self.assertGreater(tuning.discounted_cumulative_gain(names, self.labels, 3), 0)

    def test_anchor_hits_resolve_legal_name_variants(self):
        hits = tuning.anchor_hits(
            ["深圳市汇川技术股份有限公司"],
            ["汇川技术（Inovance）"],
        )
        self.assertEqual(hits[0]["enterprise"], "深圳市汇川技术股份有限公司")

    def test_overlap_metrics_reports_route_jaccard(self):
        rows = tuning.overlap_metrics({
            "route_a": ["甲公司", "乙公司"],
            "route_b": ["乙公司", "丙公司"],
        })
        self.assertEqual(rows[0]["intersection"], 1)
        self.assertAlmostEqual(rows[0]["jaccard"], 1 / 3, places=4)

    def test_unique_contribution_keeps_only_route_specific_enterprises(self):
        result = tuning.unique_contribution({
            "route_a": ["甲公司", "乙公司"],
            "route_b": ["乙公司", "丙公司"],
        })
        self.assertEqual(result["route_a"], ["甲公司"])
        self.assertEqual(result["route_b"], ["丙公司"])

    def test_evidence_metrics_calculates_noise_rate(self):
        decisions = {
            tuning.normalize_match_text("甲公司"): {"decision": "confirmed", "business_fit": "matched", "strong_source_count": 1},
            tuning.normalize_match_text("乙公司"): {"decision": "rejected", "business_fit": "partial", "strong_source_count": 0},
        }
        metrics = tuning.evidence_metrics(["甲公司", "乙公司"], decisions)
        self.assertEqual(metrics["precision"], 0.5)
        self.assertEqual(metrics["noise_rate"], 0.5)
        self.assertEqual(metrics["business_match_rate"], 0.5)
        self.assertEqual(metrics["business_coverage_rate"], 1.0)

    def test_stratified_candidates_samples_each_route_before_filling(self):
        merged = {}
        for name, route in (("甲公司", "route_a"), ("乙公司", "route_a"), ("丙公司", "route_b")):
            tuning.merge_candidate(merged, {"id": name, "name": name}, route)
        selected = tuning.stratified_candidates(
            {"route_a": ["甲公司", "乙公司"], "route_b": ["丙公司"]},
            merged,
            2,
        )
        self.assertEqual([item["name"] for item in selected], ["甲公司", "丙公司"])


if __name__ == "__main__":
    unittest.main()
