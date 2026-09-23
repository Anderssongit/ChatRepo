"""management_download.py against a fake Yahoo: no network, no real ExcelData."""
import contextlib
import io
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import management_download as MD  # noqa: E402

DAYS = pd.bdate_range("2019-01-01", periods=300)


def walk(start, seed):
    steps = np.random.default_rng(seed).normal(0.0, 0.01, len(DAYS))
    return pd.Series(start * np.cumprod(1.0 + steps), index=DAYS)


def universe():
    """Normal tickers plus one of each problem the real run met."""
    bsp = walk(0.1, 1)
    bsp.iloc[150:] *= bsp.iloc[149] / bsp.iloc[150]   # flat day, then
    bsp.iloc[150:] *= 100.0                      # exact x100: provider unit error,
                                                 # as BSP.OL 2024-12-30 -> 2025-01-02
    jmp = walk(10.0, 2)
    jmp.iloc[200:] = jmp.iloc[200:] * 5.0        # x5: unverified, not a unit error
    zero = walk(20.0, 3)
    zero.iloc[100] = 0.0                         # not a price
    return {"2020.OL": walk(30.0, 4), "AAA.OL": walk(50.0, 5), "BSP.OL": bsp,
            "CCC.OL": walk(70.0, 6), "DDD.OL": walk(80.0, 7), "JMP.OL": jmp,
            "ZERO.OL": zero}                     # GONE.OL has no prices at all


class FakeYahoo(types.ModuleType):
    def __init__(self, prices, fail_first=0, always_fail=False):
        super().__init__("yfinance")
        self.__version__ = "fake"
        self.shared = types.SimpleNamespace(_ERRORS={})
        self.prices, self.fail_first, self.always_fail = prices, fail_first, always_fail
        self.calls = []

    def download(self, tickers, start=None, **kwargs):
        self.calls.append((list(tickers), kwargs))
        self.shared._ERRORS = {}
        if self.always_fail or self.fail_first > 0:
            self.fail_first -= 1
            raise ConnectionError("Failed to perform, curl: (7) CONNECT tunnel failed, "
                                  "response 403")
        columns = {}
        for t in tickers:
            close = self.prices.get(t)
            if close is None:
                self.shared._ERRORS[t] = "YFTzMissingError('possibly delisted')"
                close = pd.Series(np.nan, index=DAYS)
            columns[("Close", t)] = close
            columns[("High", t)] = close * 1.01
            columns[("Low", t)] = close * 0.99
        frame = pd.DataFrame(columns)
        frame.columns = pd.MultiIndex.from_tuples(frame.columns, names=["Price", "Ticker"])
        return frame


def write_articles(folder):
    nlp = folder / "DataNLP"
    nlp.mkdir(parents=True)
    rows = []
    for company in (2020, "AAA", "BSP", "CCC", "DDD", "GONE", "JMP", "ZERO"):
        for day, score in (("15 Mar 2019", 0.1), ("20 Jun 2019", 0.3)):
            rows.append({"Company": company, "Article_Date": day, "Final_Score": score,
                         "Article_Title": f"{company} {day}", "Text_Length": 100})
    pd.DataFrame(rows).to_excel(nlp / "NLP_Sentiment_Detail_2026.xlsx", index=False)
    return nlp


class ManagementDownload(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.nlp = write_articles(self.base)
        self.yahoo = FakeYahoo(universe())
        self.patches = [patch.dict(sys.modules, {"yfinance": self.yahoo,
                                                 "scipy": types.ModuleType("scipy")}),
                        patch.object(MD, "_sleep", lambda s: None),
                        patch.object(MD, "FALLBACK_LOG_DIR", self.base)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def run_main(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = MD.main([*args, "--excel-dir", str(self.base)])
        return code, out.getvalue()

    def folder(self, name="all"):
        return self.base / MD.OUTPUT_DIR / "management_download" / name

    def status(self, name="all"):
        rows = pd.read_csv(self.folder(name) / "ticker_status.csv")
        return dict(zip(rows["ticker"], rows["status"]))

    # ── selecting companies ─────────────────────────────────────────────
    def test_five_takes_the_first_five_from_the_article_list(self):
        code, out = self.run_main("5")
        # A provable unit repair is reported, but it is not a warning.
        self.assertEqual(code, 0, out)
        self.assertIn("BSP.OL       repaired unit error", out)
        self.assertEqual(list(self.status("subset")),
                         ["2020.OL", "AAA.OL", "BSP.OL", "CCC.OL", "DDD.OL"])
        self.assertFalse(self.folder("all").exists(), "a test run must not touch all/")
        self.assertIn("5 of 8 companies", out)

    def test_named_companies_come_from_the_same_list(self):
        code, out = self.run_main("bsp", "2020.OL", "EAM")
        self.assertEqual(list(self.status("subset")), ["BSP.OL", "2020.OL"])
        self.assertIn("Not in the article list, ignored: EAM", out)

    def test_zero_companies_fails_in_step_three_and_skips_the_rest(self):
        code, out = self.run_main("0")
        self.assertEqual(code, 1)
        self.assertIn("[STEP 3/7] FAILED", out)
        self.assertIn("select_companies()", out)
        for n in (4, 5, 6, 7):
            self.assertIn(f"[STEP {n}/7] ", out)
            self.assertRegex(out, rf"\[STEP {n}/7\] .* - SKIPPED \(step 3 failed\)")

    # ── the full run ────────────────────────────────────────────────────
    def test_all_repairs_units_excludes_jumps_and_continues(self):
        code, out = self.run_main("all")
        self.assertEqual(code, 2)
        for n in range(1, 8):
            self.assertRegex(out, rf"\[STEP {n}/7\] (OK|WARN)")
        self.assertEqual(self.status(), {
            "2020.OL": "ok", "AAA.OL": "ok", "BSP.OL": "repaired", "CCC.OL": "ok",
            "DDD.OL": "ok", "GONE.OL": "no_prices", "JMP.OL": "excluded",
            "ZERO.OL": "repaired"})

        close = pd.read_csv(self.folder() / "management_prices_close.csv",
                            index_col="Date", parse_dates=True)
        self.assertNotIn("JMP.OL", close.columns)
        raw = universe()["BSP.OL"]
        # Rescaled backwards: the newest prices are exactly what Yahoo sent.
        self.assertAlmostEqual(close["BSP.OL"].iloc[-1], raw.iloc[-1])
        self.assertAlmostEqual(close["BSP.OL"].iloc[0], raw.iloc[0] * 100.0)
        ratio = close["BSP.OL"] / close["BSP.OL"].shift(1)
        self.assertLess(ratio.max(), MD.UPPER_RATIO)
        self.assertTrue(np.isnan(close["ZERO.OL"].iloc[100]))

        issues = pd.read_csv(self.folder() / "price_issues.csv")
        actions = dict(zip(issues["ticker"], issues["action"]))
        self.assertEqual(actions["BSP.OL"], "earlier_prices_rescaled_x100")
        self.assertEqual(actions["JMP.OL"], "ticker_excluded")
        self.assertEqual(actions["ZERO.OL"], "observation_removed")

        summary = json.loads((self.folder() / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["exit_code"], 2)
        self.assertEqual(summary["tickers_excluded"], ["JMP.OL"])
        self.assertEqual(summary["tickers_without_prices"], ["GONE.OL"])
        self.assertIn("possibly delisted", out)
        for name in ("management_prices_high.csv", "management_prices_low.csv",
                     "indicators_last.csv", "market_index.csv", "management_download.log"):
            self.assertTrue((self.folder() / name).exists(), name)

    def test_clean_prices_give_exit_code_zero(self):
        self.yahoo.prices = {t: walk(40.0 + i, 10 + i) for i, t in enumerate(
            ("2020.OL", "AAA.OL", "BSP.OL", "CCC.OL", "DDD.OL", "GONE.OL", "JMP.OL",
             "ZERO.OL"))}
        code, out = self.run_main("all")
        self.assertEqual(code, 0, out)
        self.assertIn("FINISHED - every step OK", out)

    def test_strict_stops_like_the_lab_but_still_writes_the_issue_list(self):
        code, out = self.run_main("all", "--strict")
        self.assertEqual(code, 1)
        self.assertIn("[STEP 5/7] FAILED", out)
        self.assertIn("check_prices()", out)
        self.assertIn("JMP.OL", out)
        self.assertRegex(out, r"\[STEP 6/7\] .* - SKIPPED")
        self.assertTrue((self.folder() / "price_issues.csv").exists())
        self.assertFalse((self.folder() / "management_prices_close.csv").exists())

    def test_accept_keeps_a_ticker_checked_by_hand(self):
        code, _ = self.run_main("all", "--accept", "JMP")
        self.assertEqual(self.status()["JMP.OL"], "accepted")
        close = pd.read_csv(self.folder() / "management_prices_close.csv", index_col="Date")
        self.assertIn("JMP.OL", close.columns)

    # ── downloading ─────────────────────────────────────────────────────
    def test_network_failure_names_the_step_function_and_what_to_do(self):
        self.yahoo.always_fail = True
        code, out = self.run_main("5", "--retries", "3")
        self.assertEqual(code, 1)
        self.assertIn("[STEP 4/7] FAILED", out)
        self.assertIn("Where : download_prices()", out)
        self.assertIn("ConnectionError", out)
        self.assertIn("Hint  : Check the internet connection", out)
        self.assertEqual(len(self.yahoo.calls), 3)      # one batch, three attempts
        log = (self.folder("subset") / "management_download.log").read_text(encoding="utf-8")
        self.assertIn("Traceback", log)

    def test_a_failed_attempt_is_retried(self):
        self.yahoo.fail_first = 1
        code, out = self.run_main("5")
        self.assertIn("attempt 1/3 failed", out)
        self.assertIn("succeeded on attempt 2", out)
        self.assertIn("[STEP 4/7] OK", out)

    def test_batches_split_the_tickers(self):
        self.run_main("all", "--batch-size", "3")
        batches = [c[0] for c in self.yahoo.calls if len(c[0]) > 1]
        self.assertEqual([len(b) for b in batches], [3, 3, 2])

    def test_without_scipy_repair_is_off_and_said_so(self):
        with patch.dict(sys.modules, {"scipy": None}):
            code, out = self.run_main("5")
        self.assertIn("scipy is not installed", out)
        self.assertTrue(all(c[1]["repair"] is False for c in self.yahoo.calls))

    # ── inputs and outputs ──────────────────────────────────────────────
    def remove_articles(self):
        for f in self.nlp.iterdir():
            f.unlink()
        self.nlp.rmdir()

    def test_no_articles_and_no_ticker_list_fails_step_one_with_a_hint(self):
        self.remove_articles()
        code, out = self.run_main("5")
        self.assertEqual(code, 1)
        self.assertIn("[STEP 1/7] FAILED", out)
        self.assertIn("Neither articles", out)
        self.assertIn("--excel-dir", out)
        self.assertTrue((self.base / "management_download.log").exists())

    def test_without_articles_the_ticker_list_is_downloaded(self):
        self.remove_articles()
        (self.base / "Data_BT").mkdir()
        # Laid out as PBROE_All3 reads it: an index column, then Company.
        pd.DataFrame({"Company": ["AAA", "CCC", "DDD"]}).to_excel(
            self.base / MD.TICKER_LIST)
        code, out = self.run_main("all")
        self.assertIn("No article files", out)
        self.assertIn("[STEP 7/7] OK", out)
        self.assertEqual(list(self.status()), ["AAA.OL", "CCC.OL", "DDD.OL"])

    def test_an_empty_exceldata_next_to_the_script_is_skipped(self):
        empty = self.base / "script" / "ExcelData"
        empty.mkdir(parents=True)
        with patch.object(MD, "THIS_FILE", self.base / "script" / "x.py"), \
                patch.object(MD, "LEGACY_EXCEL_DIR", str(self.base)), \
                patch.dict(MD.os.environ, {}, clear=False):
            MD.os.environ.pop("AKSJE_BASE_DIR", None)
            found, searched = MD.find_excel_dir(None)
        self.assertEqual(found, self.base.resolve())
        self.assertIn("no articles or ticker list", searched[0])

    def test_an_unreadable_article_file_is_skipped_not_fatal(self):
        (self.nlp / "NLP_Sentiment_Detail_bad.xlsx").write_bytes(b"not an excel file")
        code, out = self.run_main("5")
        self.assertIn("NLP_Sentiment_Detail_bad.xlsx: cannot be read", out)
        self.assertIn("[STEP 2/7] WARN", out)
        self.assertIn("[STEP 7/7] OK", out)

    def test_a_file_open_in_excel_is_written_under_another_name(self):
        original = pd.DataFrame.to_csv

        def locked(frame, path=None, *args, **kwargs):
            if Path(str(path)).name == "management_prices_close.csv":
                raise PermissionError(13, "Permission denied")
            return original(frame, path, *args, **kwargs)

        with patch.object(pd.DataFrame, "to_csv", locked):
            code, out = self.run_main("5")
        self.assertIn("management_prices_close.csv is locked", out)
        self.assertTrue(list(self.folder("subset").glob("management_prices_close_*.csv")))
        self.assertIn("[STEP 7/7] WARN", out)


class YahooReasons(unittest.TestCase):
    def test_the_precise_cause_wins_over_the_summary_line(self):
        log = MD.YahooLog()
        logger = MD.logging.getLogger("test_yahoo_reasons")
        logger.addHandler(log)
        logger.propagate = False
        try:
            logger.error("Failed to get ticker 'BSP.OL' reason: Failed to perform, curl: "
                         "(7) CONNECT tunnel failed, response 403. See https://curl.se/x")
            logger.error("['BSP.OL', 'EAM.OL']: YFTzMissingError('possibly delisted')")
            logger.error("\n2 Failed downloads:")          # ignored, no ticker
        finally:
            logger.removeHandler(log)
        mods = {"yf": types.SimpleNamespace(), "yahoo_log": log}
        self.assertEqual(MD.yahoo_reasons(mods, ["BSP.OL", "EAM.OL", "AAA.OL"]), {
            "BSP.OL": "Failed to perform, curl: (7) CONNECT tunnel failed, response 403.",
            "EAM.OL": "YFTzMissingError('possibly delisted')"})


class PriceRules(unittest.TestCase):
    def test_only_powers_of_ten_count_as_unit_errors(self):
        self.assertEqual(MD.unit_factor(100.0), 100.0)
        self.assertEqual(MD.unit_factor(100.4), 100.0)
        self.assertEqual(MD.unit_factor(0.01), 0.01)
        self.assertIsNone(MD.unit_factor(5.0))
        self.assertIsNone(MD.unit_factor(101.0))
        self.assertIsNone(MD.unit_factor(float("nan")))

    def test_high_and_low_are_rescaled_with_close(self):
        close = pd.Series([0.1, 0.1, 10.0, 10.0], index=DAYS[:4])
        r = MD.check_one(pd, np, "BSP.OL", close, close * 1.01, close * 0.99)
        self.assertEqual(r["units"], 1)
        self.assertEqual(r["unresolved"], [])
        self.assertAlmostEqual(r["high"].iloc[0], 10.0 * 1.01)
        self.assertAlmostEqual(r["low"].iloc[0], 10.0 * 0.99)


if __name__ == "__main__":
    unittest.main()
