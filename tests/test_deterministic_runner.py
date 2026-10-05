import unittest

from proof_eval.optimization.summary import aggregate


def record(name, score, status="passed"):
    result = {
        "status": status,
        "scores": dict.fromkeys(
            (
                "length_reduction_pct",
                "heartbeat_reduction_pct",
                "compatibility_pct",
                "combined_pct",
            ),
            score,
        ),
    }
    return {
        "name": name,
        "initial": result,
        "final": result,
        "changed": False,
        "attempts": 0,
    }


class AggregationTests(unittest.TestCase):
    def test_mean_uses_all_problems_including_known_failures(self):
        result = aggregate([record("a", 80), record("b", 0, "failed")], 2)
        self.assertEqual(result["full_benchmark_combined_pct"], 40)
        self.assertEqual(result["fully_scored_problems"], 2)

    def test_missing_infrastructure_is_not_zero_or_a_full_benchmark_mean(self):
        result = aggregate([record("a", 80), record("b", None, "incomplete")], 2)
        self.assertIsNone(result["full_benchmark_combined_pct"])
        self.assertEqual(result["measured_subset_final_mean"]["combined_pct"], 80)
        self.assertEqual(result["unscored_names"], ["b"])

    def test_unprocessed_rows_stay_in_full_denominator(self):
        result = aggregate([record("a", 80)], 15)
        self.assertIsNone(result["full_benchmark_combined_pct"])


if __name__ == "__main__":
    unittest.main()
