# -*- coding: utf-8 -*-
"""The blend must say WHICH strategy caps the joint window, and why."""
import calendar
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

# portfolio_blend is patched in place in the repository root, not shadowed by a
# copy in this folder: two files with one module name means the version you get
# depends on import order.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from portfolio_blend import (PortfolioDataError, _monthly_observations,
                             build_capital_portfolio)

AS_OF = date(2026, 9, 18)


def month_ends(start: date, end: date):
    days, cursor = [], start
    while cursor <= end:
        days.append(cursor.replace(day=calendar.monthrange(cursor.year, cursor.month)[1]))
        cursor = (cursor.replace(day=28) + timedelta(days=7)).replace(day=1)
    return [d for d in days if d <= end]


def curve(name, last, *, extra=(), growth=1.01):
    observations = [(str(d), 1000.0 * growth ** n)
                    for n, d in enumerate(month_ends(date(2025, 6, 30), last))]
    observations += [(str(d), v) for d, v in extra]
    return {"name": name, "observations": observations, "frequency": "monthly",
            "valid": True, "source": {"path": f"/tmp/{name}.xlsx"}}


class MonthlyObservations(unittest.TestCase):
    def test_returns_usable_months_and_the_dropped_ones(self):
        rows = {date(2026, 7, 31): 100.0, date(2026, 8, 19): 101.0}
        usable, dropped = _monthly_observations(rows, AS_OF)
        self.assertEqual(sorted(usable), [date(2026, 7, 31)])
        self.assertEqual(len(dropped), 1)
        self.assertEqual(dropped[0]["month_end"], date(2026, 8, 31))
        self.assertEqual(dropped[0]["gap_business_days"], 8)

    def test_a_month_end_within_the_gap_limit_is_kept(self):
        usable, dropped = _monthly_observations({date(2026, 8, 26): 100.0}, AS_OF)
        self.assertEqual(sorted(usable), [date(2026, 8, 31)])
        self.assertEqual(dropped, [])


class RealScenario(unittest.TestCase):
    """2026-09-18: three legs reach August, Sentiment Momentum stops 08-19."""

    def setUp(self):
        self.curves = [
            curve("PB-ROE-Momentum", date(2026, 8, 31)),
            curve("NLP Sentiment - ledelse", date(2026, 8, 31)),
            curve("Sentiment Momentum v3.1", date(2026, 7, 31),
                  extra=[(date(2026, 8, 19), 1200.0)]),
            curve("Innsidehandel - Oslo Bors", date(2026, 8, 31),
                  extra=[(date(2026, 9, 18), 1300.0)])]
        self.result = build_capital_portfolio(self.curves, as_of=AS_OF)

    def test_the_joint_window_stops_at_july(self):
        self.assertEqual(self.result["common_period"]["end"], "2026-07-31")

    def test_the_binding_component_is_named_in_the_payload(self):
        self.assertEqual(self.result["binding_component"], "Sentiment Momentum v3.1")

    def test_the_dropped_month_is_explained_in_the_warnings(self):
        joined = " ".join(self.result["warnings"])
        self.assertIn("Sentiment Momentum v3.1: 2026-08-31 excluded", joined)
        self.assertIn("8 business days", joined)
        self.assertIn("Refreshing the other strategies cannot recover this month", joined)

    def test_coverage_records_each_leg(self):
        coverage = self.result["coverage"]
        self.assertEqual(coverage["Sentiment Momentum v3.1"]["last_observation"], "2026-08-19")
        self.assertEqual(coverage["Sentiment Momentum v3.1"]["last_usable_month_end"], "2026-07-31")
        self.assertEqual(coverage["PB-ROE-Momentum"]["last_usable_month_end"], "2026-08-31")

    def test_refreshing_the_stale_leg_extends_the_window(self):
        fixed = [c for c in self.curves if c["name"] != "Sentiment Momentum v3.1"]
        fixed.append(curve("Sentiment Momentum v3.1", date(2026, 8, 31)))
        result = build_capital_portfolio(fixed, as_of=AS_OF)
        self.assertEqual(result["common_period"]["end"], "2026-08-31")


class ErrorsNameTheCause(unittest.TestCase):
    def test_too_few_common_months_names_the_binding_component(self):
        curves = [curve("A", date(2026, 8, 31)), curve("B", date(2026, 8, 31)),
                  curve("C", date(2026, 8, 31)),
                  # Two raw observations, but both fall in the same month, so D
                  # can substantiate exactly one common month-end.
                  {"name": "D", "frequency": "monthly", "valid": True,
                   "observations": [(str(date(2025, 6, 27)), 1000.0),
                                    (str(date(2025, 6, 30)), 1010.0)]}]
        with self.assertRaises(PortfolioDataError) as caught:
            build_capital_portfolio(curves, as_of=AS_OF)
        message = str(caught.exception)
        self.assertIn("Binding component: D", message)
        self.assertIn("2025-06-30", message)

    def test_a_leg_with_no_month_end_at_all_is_named(self):
        curves = [curve("A", date(2026, 8, 31)), curve("B", date(2026, 8, 31)),
                  curve("C", date(2026, 8, 31)),
                  {"name": "D", "frequency": "daily", "valid": True,
                   "observations": [(str(date(2026, 9, 17)), 1000.0),
                                    (str(date(2026, 9, 18)), 1001.0)]}]
        with self.assertRaises(PortfolioDataError) as caught:
            build_capital_portfolio(curves, as_of=AS_OF)
        self.assertIn("No completed month-end can be substantiated for: D",
                      str(caught.exception))


if __name__ == "__main__":
    unittest.main()
