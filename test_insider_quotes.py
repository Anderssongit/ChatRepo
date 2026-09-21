"""An observed valuation mark does not establish an executable market quote."""
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import innsidehandel_pipeline as ip


class InsiderQuoteTests(unittest.TestCase):
    def setUp(self):
        self.opp = ip.Oppsett()
        self.opp.startkapital = 1000.0
        self.opp.min_navn_portefolje = 1
        self.opp.maks_navn = 1
        self.opp.min_score_portefolje = 0
        self.opp.min_omsetning_nok = 0
        self.opp.signal_vindu_dager = 30
        self.opp.spread_pst = self.opp.kurtasje_pst = 0.0
        self.strategy = ip.Strategi("test", takt="dag")

    def market(self, observed, signal_day=0, marks=None):
        dates = []
        day = date(2024, 1, 2)
        while len(dates) < len(observed):
            if day.weekday() < 5:
                dates.append(day)
            day += timedelta(days=1)
        if marks is None:
            marks, previous = [], None
            for value in observed:
                if value is not None:
                    previous = value
                marks.append(previous)
        return SimpleNamespace(kalender=dates, dager=list(range(len(dates))),
                               handelskurs={"A": observed}, kurs={"A": marks},
                               signaler=[(signal_day, "A", 80.0, 1_000_000.0)],
                               _dager_i_signal=[signal_day], ref=None)

    def test_missing_candidate_quote_does_not_buy_at_carried_mark(self):
        market = self.market([None, 120.0], marks=[100.0, 120.0])
        equity, trades, _, _ = ip.kjor_strategi(market, self.strategy, self.opp)
        self.assertEqual(equity[0]["Antall_Navn"], 0)
        self.assertEqual(equity[0]["Verdi_NOK"], 1000.0)
        self.assertEqual([t["Dato"] for t in trades], [market.kalender[1].isoformat()])
        self.assertEqual(trades[0]["Type"], "KJØP")

    def test_expired_position_waits_for_real_quote_then_realizes_actual_loss(self):
        market = self.market([100.0, 110.0, None, None, 80.0])
        strategy = ip.Strategi("expiry", takt="dag", hold_dager=2, vindu_dager=1)
        equity, trades, written_down, holdings = ip.kjor_strategi(market, strategy, self.opp)
        self.assertEqual([r["Verdi_NOK"] for r in equity], [1000, 1100, 1100, 1100, 800])
        self.assertEqual([t["Dato"] for t in trades],
                         [market.kalender[0].isoformat(), market.kalender[4].isoformat()])
        self.assertEqual(trades[-1]["Type"], "UTLØPT")
        self.assertEqual(trades[-1]["Verdi_NOK"], 800.0)
        self.assertEqual(written_down, 0)
        self.assertEqual(holdings[0]["Ticker"], "(kontanter)")

    def test_rebalance_never_sells_or_mutates_a_holding_without_actual_quote(self):
        market = self.market([None], marks=[150.0])
        book = {"A": ip.Posisjon(10.0, 100.0, 0)}
        trades = []
        cash = ip._sett_portefolje(market, book, [], 0, market.kalender[0],
                                  50.0, 0.0, self.strategy, self.opp, trades)
        self.assertEqual(cash, 50.0)
        self.assertEqual(book["A"].antall, 10.0)
        self.assertEqual(trades, [])

    def test_rebalance_does_not_buy_missing_candidate_quote(self):
        market = self.market([None], marks=[150.0])
        book, trades = {}, []
        cash = ip._sett_portefolje(market, book, [("A", 80)], 0,
                                  market.kalender[0], 1000.0, 0.0,
                                  self.strategy, self.opp, trades)
        self.assertEqual(cash, 1000.0)
        self.assertEqual(book, {})
        self.assertEqual(trades, [])

    def test_five_missing_sessions_may_be_marked_but_sixth_blocks_result(self):
        market = self.market([100.0] + [None] * 5)
        equity, trades, written_down, _ = ip.kjor_strategi(market, self.strategy, self.opp)
        self.assertEqual([r["Verdi_NOK"] for r in equity], [1000.0] * 6)
        self.assertEqual(len(trades), 1)
        self.assertEqual(written_down, 0)
        # Even a caller passing an unlimited filled mark cannot waive the bound.
        self.opp.maks_fyll_dager = 99
        with self.assertRaisesRegex(RuntimeError, "valuation incomplete.*A"):
            ip.kjor_strategi(self.market([100.0] + [None] * 6), self.strategy, self.opp)

    def test_shorter_configured_mark_limit_is_respected(self):
        self.opp.maks_fyll_dager = 1
        with self.assertRaisesRegex(RuntimeError, "maximum 1 missing sessions"):
            ip.kjor_strategi(self.market([100.0, None, None]), self.strategy, self.opp)

    def test_unobserved_unheld_series_does_not_block_portfolio(self):
        market = self.market([None] * 10)
        equity, trades, _, holdings = ip.kjor_strategi(market, self.strategy, self.opp)
        self.assertEqual(equity[-1]["Verdi_NOK"], 1000.0)
        self.assertEqual(trades, [])
        self.assertEqual(holdings[0]["Ticker"], "(kontanter)")

    def test_production_market_separates_execution_prices_from_bounded_marks(self):
        with tempfile.TemporaryDirectory() as directory:
            opp = ip.Oppsett(base_dir=Path(directory))
            opp.maks_fyll_dager = 99
            opp.lag_mapper()
            dates = self.market([100] * 8).kalender
            ip.skriv_kalenderfil(opp.kalender_csv, dates)
            book = ip.Kursbok(opp.s4_dir)
            book.slå_sammen("A.OL", {
                dates[0]: {"close": 100.0, "adjclose": 100.0, "volum": 100.0},
                dates[-1]: {"close": 90.0, "adjclose": 90.0, "volum": 100.0},
            })
            book.lagre_ticker("A.OL")
            market = ip.Marked([{"Ticker": "A.OL", "Handelsdag_0": dates[0].isoformat(),
                                  "Bullish_Score": 80, "Omsetning_Snitt_NOK": 10000}], opp)
            self.assertIsNone(market.handelskurs["A.OL"][1])
            self.assertEqual(market.kurs["A.OL"][1], 100.0)
            self.assertEqual(market.kurs["A.OL"][5], 100.0)
            self.assertIsNone(market.kurs["A.OL"][6])
            self.assertEqual(market.handelskurs["A.OL"][7], 90.0)


if __name__ == "__main__":
    unittest.main()
