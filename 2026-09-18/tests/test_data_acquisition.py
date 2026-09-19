# -*- coding: utf-8 -*-
"""Row-building for the three upstream workbooks. No pandas, no network."""
import sys
import unittest
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import data_acquisition as da

COMPANIES = [
    {"Selskap": "EQUINOR", "Ticker": "EQNR.OL", "Symbol": "EQNR",
     "ISIN": "NO0010096985", "Marked": "Oslo Bors"},
    {"Selskap": "DNB BANK", "Ticker": "DNB.OL", "Symbol": "DNB",
     "ISIN": "NO0010161896", "Marked": "Oslo Bors"},
]


class TickerWorkbook(unittest.TestCase):
    """PBROE builds tradingview.com/symbols/OSL-<Company>/ from this column."""

    def test_company_holds_the_bare_symbol(self):
        rows = da.ticker_workbook_rows(COMPANIES)
        self.assertEqual([r["Company"] for r in rows], ["DNB", "EQNR"])

    def test_company_is_not_the_first_column(self):
        # load_tickers() does df.drop(df.columns[0], axis=1) before reading
        # "Company"; the workbook is written with index=True so the dropped
        # column is the index, never Company.
        self.assertEqual(da.TICKER_COLUMNS[0], "Company")

    def test_suffix_is_stripped_and_duplicates_collapse(self):
        rows = da.ticker_workbook_rows(COMPANIES + [dict(COMPANIES[0])])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1]["Ticker"], "EQNR.OL")

    def test_name_falls_back_to_the_symbol(self):
        rows = da.ticker_workbook_rows([{"Symbol": "XXL", "Selskap": ""}])
        self.assertEqual(rows[0]["Name"], "XXL")


class PriceWorkbook(unittest.TestCase):
    def setUp(self):
        self.book = {"EQNR": {date(2026, 9, 17): {"close": 300.0, "adjclose": 299.0,
                                                  "volum": 1000.0},
                              date(2026, 9, 18): {"close": 310.0, "adjclose": 309.0,
                                                  "volum": 1100.0}}}

    def test_produces_the_four_required_columns(self):
        rows = da.price_workbook_rows(self.book, {"EQNR": "EQUINOR"})
        self.assertEqual(rows[0]["Company"], "EQUINOR")
        self.assertEqual(rows[0]["Ticker"], "EQNR.OL")
        self.assertEqual(rows[0]["Close"], 300.0)
        self.assertEqual(rows[0]["Date"], date(2026, 9, 17))

    def test_company_name_matches_step4_so_the_ticker_map_joins(self):
        names = da.company_names(COMPANIES)
        self.assertEqual(names["EQNR"], "EQUINOR")
        rows = da.price_workbook_rows(self.book, names)
        self.assertEqual({r["Company"] for r in rows}, {"EQUINOR"})

    def test_index_series_are_left_out(self):
        book = dict(self.book, **{"^OSEBX": {date(2026, 9, 18): {"close": 1500.0}}})
        rows = da.price_workbook_rows(book, {})
        self.assertEqual({r["Ticker"] for r in rows}, {"EQNR.OL"})

    def test_non_positive_and_missing_closes_are_dropped_not_zeroed(self):
        book = {"A": {date(2026, 9, 17): {"close": None},
                      date(2026, 9, 18): {"close": -1.0},
                      date(2026, 9, 21): {"close": 5.0}}}
        rows = da.price_workbook_rows(book, {})
        self.assertEqual([r["Close"] for r in rows], [5.0])

    def test_start_bound_is_respected(self):
        rows = da.price_workbook_rows(self.book, {}, start=date(2026, 9, 18))
        self.assertEqual([r["Date"] for r in rows], [date(2026, 9, 18)])


class Step4Changes(unittest.TestCase):
    """Sentiment_Change is the move from the company's previous report."""

    def detail(self):
        return [
            {"Company": "EQUINOR", "Article_Date": "2026-09-01", "Final_Score": 0.20,
             "Article_Title": "Q2", "Positive_Score": 0.6, "Negative_Score": 0.4},
            {"Company": "EQUINOR", "Article_Date": "2026-09-10", "Final_Score": 0.50,
             "Article_Title": "Q3", "Positive_Score": 0.8, "Negative_Score": 0.3},
            {"Company": "DNB BANK", "Article_Date": "2026-09-05", "Final_Score": -0.10,
             "Article_Title": "Update", "Positive_Score": 0.3, "Negative_Score": 0.4},
        ]

    def test_change_is_measured_against_the_previous_report(self):
        rows = da.sentiment_change_rows(self.detail())
        eq = [r for r in rows if r["Company"] == "EQUINOR"]
        self.assertEqual(eq[0]["Sentiment_Change"], 0.0)      # no predecessor
        self.assertAlmostEqual(eq[1]["Sentiment_Change"], 0.30)
        self.assertAlmostEqual(eq[1]["Previous_Score"], 0.20)

    def test_each_company_has_its_own_chain(self):
        rows = da.sentiment_change_rows(self.detail())
        dnb = [r for r in rows if r["Company"] == "DNB BANK"]
        self.assertEqual(len(dnb), 1)
        self.assertEqual(dnb[0]["Sentiment_Change"], 0.0)
        self.assertEqual(dnb[0]["Report_Index"], 1)

    def test_out_of_order_input_is_sorted_before_differencing(self):
        rows = da.sentiment_change_rows(list(reversed(self.detail())))
        eq = [r for r in rows if r["Company"] == "EQUINOR"]
        self.assertAlmostEqual(eq[1]["Sentiment_Change"], 0.30)

    def test_placeholder_rows_are_dropped(self):
        detail = self.detail() + [{"Company": "XXL", "Article_Date": "",
                                   "Article_Title": "INGEN ARTIKLER",
                                   "Final_Score": 0.0}]
        rows = da.sentiment_change_rows(detail)
        self.assertNotIn("XXL", {r["Company"] for r in rows})

    def test_rows_without_a_date_or_score_are_skipped(self):
        detail = [{"Company": "A", "Article_Date": "nonsense", "Final_Score": 0.1},
                  {"Company": "B", "Article_Date": "2026-09-01", "Final_Score": None}]
        self.assertEqual(da.sentiment_change_rows(detail), [])

    def test_the_required_columns_are_present(self):
        rows = da.sentiment_change_rows(self.detail(),
                                        tickers={"EQUINOR": "EQNR"})
        for column in ("Company", "Article_Date", "Article_Title",
                       "Final_Score", "Sentiment_Change"):
            self.assertIn(column, rows[0])
        self.assertEqual([r for r in rows if r["Company"] == "EQUINOR"][0]["Ticker"],
                         "EQNR.OL")

    def test_output_is_chronological(self):
        rows = da.sentiment_change_rows(self.detail())
        self.assertEqual([r["Article_Date"] for r in rows],
                         sorted(r["Article_Date"] for r in rows))


class DateParsing(unittest.TestCase):
    def test_accepts_the_shapes_the_scraper_emits(self):
        for value, expected in (("2026-09-18", date(2026, 9, 18)),
                                ("18.09.2026", date(2026, 9, 18)),
                                ("2026-09-18 10:30:00", date(2026, 9, 18)),
                                ("2026-09-18T10:30:00Z", date(2026, 9, 18)),
                                (datetime(2026, 9, 18, 10), date(2026, 9, 18))):
            self.assertEqual(da.parse_date(value), expected, value)

    def test_unparsable_values_return_none_rather_than_today(self):
        for value in ("", None, "n/a", "forrige uke"):
            self.assertIsNone(da.parse_date(value))


class Refresh(unittest.TestCase):
    def test_a_missing_file_always_needs_building(self):
        stale, why = da.needs_refresh(None, date(2026, 9, 18), 5)
        self.assertTrue(stale)
        self.assertEqual(why, "missing")

    def test_unknown_step_names_are_rejected(self):
        with self.assertRaises(ValueError):
            da.build_all(Path("."), None, None, steps=("tickers", "nonsense"))


if __name__ == "__main__":
    unittest.main()
