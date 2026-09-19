# -*- coding: utf-8 -*-
"""Price-repair regressions. Pure Python: no pandas, numpy or network."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import price_repair as pr


def series(pairs):
    return [(f"2025-01-{day:02d}", value) for day, value in pairs]


class NearestScale(unittest.TestCase):
    def test_exact_powers_of_ten_are_recognised(self):
        for ratio, expected in ((100.0, 100.0), (0.01, 0.01), (10.0, 10.0),
                                (1000.0, 1000.0), (0.001, 0.001)):
            self.assertEqual(pr.nearest_scale(ratio), expected)

    def test_a_genuine_large_move_is_not_a_scale(self):
        for ratio in (4.0, 4.7, 6.2, 0.25, 0.21, 9.0, 12.0):
            self.assertIsNone(pr.nearest_scale(ratio), ratio)

    def test_tolerance_is_tight_enough_to_exclude_near_misses(self):
        self.assertIsNotNone(pr.nearest_scale(100.4))    # within 0.5%
        self.assertIsNone(pr.nearest_scale(103.0))       # 3% off is a price move


class BspRealCase(unittest.TestCase):
    """The exact series named in VALIDATION.md and the failing 2026-09-18 run."""

    def setUp(self):
        self.raw = [("2024-12-30", 0.101440), ("2025-01-02", 10.144007),
                    ("2025-01-03", 10.20)]
        self.result = pr.repair_series("BSP.OL", self.raw)

    def test_the_hundredfold_step_is_classified_as_a_unit_artifact(self):
        self.assertEqual(len(self.result.repairs), 1)
        repair = self.result.repairs[0]
        self.assertEqual(repair.kind, pr.KIND_UNIT_SCALE)
        # The real series is 100.000069x, not a textbook 100.0 - which is
        # exactly why a tolerance, rather than equality, decides this.
        self.assertAlmostEqual(repair.ratio, 100.0, delta=0.001)
        self.assertEqual(repair.factor, 100.0)

    def test_repair_resolves_the_series(self):
        self.assertTrue(self.result.resolved)
        self.assertEqual(self.result.unresolved, [])

    def test_recent_prices_are_never_modified(self):
        # Live positions are marked against the newest quotes; only history moves.
        self.assertAlmostEqual(self.result.prices[1][1], 10.144007)
        self.assertAlmostEqual(self.result.prices[2][1], 10.20)

    def test_history_is_rescaled_onto_the_current_denomination(self):
        self.assertAlmostEqual(self.result.prices[0][1], 10.1440)


class RepairPreservesEconomics(unittest.TestCase):
    def test_every_return_except_the_artifact_is_unchanged(self):
        raw = series([(1, 1.00), (2, 1.10), (3, 1.05), (4, 105.0), (5, 110.25)])
        result = pr.repair_series("X.OL", raw)
        self.assertTrue(result.resolved)
        before = [raw[i + 1][1] / raw[i][1] for i in range(len(raw) - 1)]
        after = [result.prices[i + 1][1] / result.prices[i][1]
                 for i in range(len(result.prices) - 1)]
        self.assertAlmostEqual(after[0], before[0])   # 1.10
        self.assertAlmostEqual(after[1], before[1])   # 0.9545...
        self.assertAlmostEqual(after[2], 1.0)         # the artifact, neutralised
        self.assertAlmostEqual(after[3], before[3])   # 1.05

    def test_repairing_twice_changes_nothing(self):
        once = pr.repair_series("X.OL", series([(1, 0.5), (2, 50.0), (3, 51.0)]))
        twice = pr.repair_series("X.OL", once.prices)
        self.assertEqual(twice.repairs, [])
        self.assertEqual([p for _, p in once.prices], [p for _, p in twice.prices])

    def test_a_clean_series_is_returned_untouched(self):
        raw = series([(1, 100.0), (2, 110.0), (3, 85.0), (4, 95.0)])
        result = pr.repair_series("A.OL", raw)
        self.assertTrue(result.resolved)
        self.assertFalse(result.changed)
        self.assertEqual([p for _, p in result.prices], [p for _, p in raw])


class NeverGuesses(unittest.TestCase):
    def test_an_unexplained_jump_still_blocks(self):
        result = pr.repair_series("B.OL", series([(1, 10.0), (2, 47.0)]))
        self.assertFalse(result.resolved)
        self.assertFalse(result.changed)
        self.assertEqual(result.unresolved[0].kind, pr.KIND_UNVERIFIED)
        self.assertEqual([p for _, p in result.prices], [10.0, 47.0])

    def test_an_unexplained_collapse_still_blocks(self):
        result = pr.repair_series("C.OL", series([(1, 10.0), (2, 2.0)]))
        self.assertFalse(result.resolved)

    def test_non_positive_prices_are_never_repairable(self):
        result = pr.repair_series("D.OL", series([(1, 10.0), (2, -3.0), (3, 10.0)]))
        self.assertFalse(result.resolved)
        self.assertIn(pr.KIND_NON_POSITIVE, [b.kind for b in result.unresolved])

    def test_a_ticker_with_both_kinds_is_not_partially_published(self):
        result = pr.repair_series("E.OL", series([(1, 0.5), (2, 50.0), (3, 240.0)]))
        self.assertTrue(result.changed)        # the x100 step was repaired
        self.assertFalse(result.resolved)      # the 4.8x step still blocks
        self.assertEqual(pr.blocked_tickers([result]), ["E.OL"])


class GapsAndCascades(unittest.TestCase):
    def test_missing_observations_are_skipped_not_filled(self):
        raw = [("2024-12-30", 0.10144), ("2024-12-31", None), ("2025-01-02", 10.144)]
        result = pr.repair_series("BSP.OL", raw)
        self.assertTrue(result.resolved)
        self.assertIsNone(result.prices[1][1])

    def test_two_cascading_artifacts_both_resolve(self):
        result = pr.repair_series("F.OL", series([(1, 1.0), (2, 100.0), (3, 10000.0)]))
        self.assertTrue(result.resolved)
        self.assertEqual([round(p, 6) for _, p in result.prices], [10000.0] * 3)


class AuditTrail(unittest.TestCase):
    def test_repaired_and_blocked_rows_are_both_recorded(self):
        good = pr.repair_series("BSP.OL", series([(1, 0.1), (2, 10.0)]))
        bad = pr.repair_series("B.OL", series([(1, 10.0), (2, 47.0)]))
        rows = pr.audit_rows([good, bad])
        self.assertEqual(len(rows), 2)
        by_ticker = {r["ticker"]: r for r in rows}
        self.assertEqual(by_ticker["BSP.OL"]["resolution"], "rescaled_earlier_segment")
        self.assertEqual(by_ticker["BSP.OL"]["applied_factor"], 100.0)
        self.assertEqual(by_ticker["B.OL"]["resolution"], "blocked_needs_verification")
        self.assertEqual(by_ticker["B.OL"]["applied_factor"], "")

    def test_summary_separates_repaired_from_blocked(self):
        results = pr.repair_universe({
            "BSP.OL": series([(1, 0.1), (2, 10.0)]),
            "B.OL": series([(1, 10.0), (2, 47.0)]),
            "A.OL": series([(1, 10.0), (2, 11.0)])}).values()
        found = pr.summary(results)
        self.assertEqual(found["repaired_tickers"], ["BSP.OL"])
        self.assertEqual(found["blocked_tickers"], ["B.OL"])
        self.assertEqual(found["repairs"], 1)


if __name__ == "__main__":
    unittest.main()
