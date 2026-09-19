"""Offline regression tests; no scraping, credentials or email sending."""
import copy
import sys
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import innsidehandel_pipeline as ip
from insider_selection import (_entry_counts, _split, select_robust_variant,
                               strategy_rules, variant_rules, resolve_choice)


class RobustSelectionTests(unittest.TestCase):
    def rows(self):
        return [{"Variant": name, "Train_Days": 400, "Train_Entries": 30,
                 "Train_Tickers": 10, "Train_Moderate_CAGR_Pst": 15.0,
                 "Train_Stress_Worst_Half_CAGR_Pst": stress,
                 "Train_Turnover_Per_Year_Pst": turnover,
                 "Test_CAGR_Pst": test, "Full_CAGR_Pst": test}
                for name, stress, turnover, test in
                [("daglig", 1, 1000, 80), ("forfall-60", 3, 800, -90),
                 ("scorevektet", 2, 600, 100)]]

    def test_later_returns_cannot_change_selection(self):
        rows = self.rows()
        self.assertEqual(select_robust_variant(rows)[0]["Variant"], "forfall-60")
        for n, row in enumerate(rows):
            row["Test_CAGR_Pst"] = (n - 1) * 1_000_000
            row["Full_CAGR_Pst"] = -row["Test_CAGR_Pst"]
        self.assertEqual(select_robust_variant(rows)[0]["Variant"], "forfall-60")

    def test_cost_sensitivity_beats_gross_return(self):
        rows = self.rows()
        rows[1]["Train_Stress_Worst_Half_CAGR_Pst"] = -10
        self.assertEqual(select_robust_variant(rows)[0]["Variant"], "scorevektet")

    def test_tie_uses_lower_training_turnover(self):
        rows = self.rows()
        rows[1]["Train_Stress_Worst_Half_CAGR_Pst"] = 2
        self.assertEqual(select_robust_variant(rows)[0]["Variant"], "scorevektet")

    def test_insufficient_training_retains_baseline(self):
        rows = self.rows()
        for row in rows:
            row["Train_Days"] = 120
        self.assertEqual(select_robust_variant(rows)[0]["Variant"], "daglig")

    def test_no_positive_moderate_return_retains_baseline(self):
        rows = self.rows()
        for row in rows:
            row["Train_Moderate_CAGR_Pst"] = -1
        self.assertEqual(select_robust_variant(rows)[0]["Variant"], "daglig")

    def test_negative_stress_is_explicitly_disclosed(self):
        rows = self.rows()
        for row in rows:
            row["Train_Stress_Worst_Half_CAGR_Pst"] -= 10
        chosen, reason = select_robust_variant(rows)
        self.assertEqual(chosen["Variant"], "forfall-60")
        self.assertIn("ingen nettofordel", reason)

    def test_manual_override_preserves_automatic_recommendation_in_audit(self):
        chosen, reason, recommendation, manual = resolve_choice(self.rows(), "daglig")
        self.assertEqual(chosen["Variant"], "daglig")
        self.assertEqual(recommendation, "forfall-60")
        self.assertTrue(manual)
        self.assertIn("Manuelt valg", reason)

    def test_unknown_manual_override_fails(self):
        with self.assertRaisesRegex(ValueError, "Unknown AKSJE_INNSIDE_VALG"):
            resolve_choice(self.rows(), "imaginary")

    def test_rebalances_do_not_count_as_new_entries(self):
        trades = [{"Dato": "2024-01-02", "Ticker": "A", "Type": "KJØP"},
                  {"Dato": "2024-01-03", "Ticker": "A", "Type": "KJØP"},
                  {"Dato": "2024-01-04", "Ticker": "A", "Type": "TRIMM"},
                  {"Dato": "2024-01-05", "Ticker": "A", "Type": "SELG"},
                  {"Dato": "2024-01-06", "Ticker": "A", "Type": "KJØP"},
                  {"Dato": "2025-01-06", "Ticker": "B", "Type": "KJØP"}]
        self.assertEqual(_entry_counts(trades, "2024-12-31"), (2, 1))

    def test_holdout_and_halves_include_boundary_return(self):
        rows = [{"Dato": f"2024-01-0{n}", "Verdi_NOK": n} for n in range(1, 8)]
        train, test, first, second = _split(rows, "2024-01-05")
        self.assertEqual(test[0], train[-1])
        self.assertEqual(first[-1], second[0])
        self.assertEqual(len(first) + len(second) - 1, len(train))


class CostBasisTests(unittest.TestCase):
    def setUp(self):
        self.opp = ip.Oppsett()
        self.opp.min_navn_portefolje = 1
        self.st = ip.Strategi("test", takt="dag")
        self.market = SimpleNamespace(kurs={"A": [20.0], "B": [20.0]})
        self.book = {"A": ip.Posisjon(10.0, 10.0, 0)}

    def rebalance(self, targets, cash=0, cost=0):
        history = []
        result = ip._sett_portefolje(self.market, self.book, targets, 0,
                                    date(2025, 1, 1), cash, cost, self.st,
                                    self.opp, history)
        return result

    def test_unchanged_position_retains_cost_and_profit(self):
        self.rebalance([("A", 60)])
        self.assertEqual(self.book["A"].inn_kurs, 10)
        self.assertEqual(20 / self.book["A"].inn_kurs - 1, 1)

    def test_trim_retains_cost_basis(self):
        self.rebalance([("A", 60), ("B", 60)])
        self.assertAlmostEqual(self.book["A"].antall, 5)
        self.assertAlmostEqual(self.book["A"].inn_kurs, 10)
        self.assertAlmostEqual(self.book["B"].inn_kurs, 20)

    def test_add_uses_weighted_average_actual_purchase_price(self):
        self.rebalance([("A", 60)], cash=200)
        self.assertAlmostEqual(self.book["A"].antall, 20)
        self.assertAlmostEqual(self.book["A"].inn_kurs, 15)

    def test_cost_scaling_uses_final_share_count(self):
        self.rebalance([("A", 60)], cash=200, cost=0.01)
        pos = self.book["A"]
        self.assertAlmostEqual(pos.inn_kurs,
                               (100 + (pos.antall - 10) * 20) / pos.antall)

    def test_closing_keeps_existing_cash_free_of_sell_cost(self):
        cash = self.rebalance([], cash=100, cost=0.01)
        self.assertAlmostEqual(cash, 298)
        self.assertEqual(self.book, {})

    def test_rules_match_actual_event_refill_and_daily_rebalance(self):
        event = next(st for st in ip.VARIANTER if st.navn == "hendelse-20")
        self.assertIn("samme dag", strategy_rules(event, self.opp)["Exit"])
        daily = variant_rules("daglig", self.opp)
        self.assertIn("uendret", dict(daily)["Utgang"])
        decay = next(st for st in ip.VARIANTER if st.navn == "forfall-60")
        self.assertIn("børsdager", strategy_rules(decay, self.opp)["Ranking"])


if __name__ == "__main__":
    unittest.main()
