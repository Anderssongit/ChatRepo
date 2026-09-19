# -*- coding: utf-8 -*-
"""Freshness and month-end coverage, anchored on the real 2026-09-18 run."""
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import freshness as fr

AS_OF = date(2026, 9, 18)
SENTMOM_LAST = date(2026, 8, 19)


class SentMomStaleness(unittest.TestCase):
    """The leg the 2026-09-18 report called OK while it ran on month-old prices."""

    def test_thirty_day_old_prices_are_not_ok(self):
        check = fr.assess("Sentiment Momentum v3.1", SENTMOM_LAST, AS_OF, max_age_days=7)
        self.assertEqual(check.status, fr.STALE)
        self.assertEqual(check.age_days, 30)
        self.assertIn("re-running the model does not refresh its source prices",
                      check.message)

    def test_august_month_end_is_unreachable_and_says_why(self):
        coverage = fr.month_end_coverage("Sentiment Momentum v3.1", SENTMOM_LAST, AS_OF)
        self.assertEqual(coverage.last_usable_month_end, date(2026, 7, 31))
        self.assertEqual(coverage.dropped[0][0], date(2026, 8, 31))
        self.assertEqual(coverage.dropped[0][1], 8)      # business days, limit 5
        self.assertIn("8 business days before it", coverage.message)

    def test_a_week_of_slippage_still_reaches_the_month_end(self):
        coverage = fr.month_end_coverage("X", date(2026, 8, 26), AS_OF)
        self.assertEqual(coverage.last_usable_month_end, date(2026, 8, 31))
        self.assertEqual(coverage.dropped, [])


class FutureDatedRows(unittest.TestCase):
    """PB-ROE carried a 2026-09-30 label on a 2026-09-18 report."""

    def test_an_observation_after_the_report_date_is_rejected(self):
        check = fr.assess("PB-ROE-Momentum", date(2026, 9, 30), AS_OF, max_age_days=40)
        self.assertEqual(check.status, fr.STALE)
        self.assertIn("A future-dated row is a label, not an observed price",
                      check.message)


class Ordinary(unittest.TestCase):
    def test_current_data_passes(self):
        check = fr.assess("Innsidehandel", date(2026, 9, 18), AS_OF, max_age_days=7)
        self.assertTrue(check.ok)
        self.assertEqual(check.age_days, 0)

    def test_a_missing_date_is_reported_not_guessed(self):
        check = fr.assess("NLP Sentiment", None, AS_OF)
        self.assertEqual(check.status, fr.MISSING)
        self.assertIsNone(check.age_days)


class JointWindow(unittest.TestCase):
    """The question the 2026-09-18 report never answered: who caps the period?"""

    def setUp(self):
        self.coverages = [
            fr.month_end_coverage("PB-ROE-Momentum", date(2026, 8, 31), AS_OF),
            fr.month_end_coverage("NLP Sentiment - ledelse", date(2026, 8, 31), AS_OF),
            fr.month_end_coverage("Sentiment Momentum v3.1", SENTMOM_LAST, AS_OF),
            fr.month_end_coverage("Innsidehandel", date(2026, 9, 18), AS_OF)]

    def test_the_binding_component_is_named(self):
        window = fr.joint_window(self.coverages)
        self.assertEqual(window["binding_component"], "Sentiment Momentum v3.1")
        self.assertEqual(window["last_common_month_end"], date(2026, 7, 31))

    def test_the_explanation_says_fixing_others_will_not_help(self):
        window = fr.joint_window(self.coverages)
        self.assertIn("Refreshing any other strategy cannot extend it",
                      window["explanation"])

    def test_refreshing_sentmom_moves_the_window(self):
        fixed = [c for c in self.coverages if c.name != "Sentiment Momentum v3.1"]
        fixed.append(fr.month_end_coverage("Sentiment Momentum v3.1",
                                           date(2026, 8, 31), AS_OF))
        window = fr.joint_window(fixed)
        self.assertEqual(window["last_common_month_end"], date(2026, 8, 31))


class BusinessDays(unittest.TestCase):
    def test_counts_weekdays_strictly_after_the_start(self):
        self.assertEqual(fr.business_days_after(date(2026, 8, 19), date(2026, 8, 31)), 8)
        self.assertEqual(fr.business_days_after(date(2026, 7, 31), date(2026, 7, 31)), 0)

    def test_weekend_only_span_counts_zero(self):
        self.assertEqual(fr.business_days_after(date(2026, 9, 18), date(2026, 9, 20)), 0)


if __name__ == "__main__":
    unittest.main()
