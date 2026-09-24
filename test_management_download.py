"""management_download.py against a fake Yahoo: no network, no real ExcelData."""
import contextlib
import io
import json
import os
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
    def __init__(self, prices, fail_first=0, always_fail=False, fail_with_repair=()):
        super().__init__("yfinance")
        self.fail_with_repair = set(fail_with_repair)
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
            if t in self.fail_with_repair and kwargs.get("repair"):
                self.shared._ERRORS[t] = "IntCastingNaNError('Cannot convert non-finite')"
                close = None
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
        """Runs without the article download unless the test passes --articles."""
        wanted = [a for a in args if a != "--articles"]
        if "--articles" not in args:
            wanted.append("--no-articles")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = MD.main([*wanted, "--excel-dir", str(self.base)])
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
        self.assertIn("[STEP 3/8] FAILED", out)
        self.assertIn("select_companies()", out)
        for n in (4, 5, 6, 7, 8):
            self.assertIn(f"[STEP {n}/8] ", out)
            self.assertRegex(out, rf"\[STEP {n}/8\] .* - SKIPPED \(step 3 failed\)")

    # ── the full run ────────────────────────────────────────────────────
    def test_all_repairs_units_excludes_jumps_and_continues(self):
        code, out = self.run_main("all")
        self.assertEqual(code, 2)
        for n in range(1, 9):
            self.assertRegex(out, rf"\[STEP {n}/8\] (OK|WARN)")
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
        self.assertIn("[STEP 6/8] FAILED", out)
        self.assertIn("check_prices()", out)
        self.assertIn("JMP.OL", out)
        self.assertRegex(out, r"\[STEP 7/8\] .* - SKIPPED")
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
        self.assertIn("[STEP 5/8] FAILED", out)
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
        self.assertIn("[STEP 5/8] OK", out)

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
        self.assertIn("[STEP 1/8] FAILED", out)
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
        self.assertIn("[STEP 8/8] OK", out)
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
        self.assertIn("[STEP 2/8] WARN", out)
        self.assertIn("[STEP 8/8] OK", out)

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
        self.assertIn("[STEP 8/8] WARN", out)


def fake_scraper(nlp, fail=None):
    """An Only_260820 module whose scraper adds one new BSP article, as the real one does."""
    module = types.ModuleType("Only_260820")
    module.calls = []

    def SentimentManagement():
        keys = ("AKSJE_NLP_HENT", "AKSJE_NLP_ONLY_DOWNLOAD", "AKSJE_NLP_SELSKAPER",
                "AKSJE_BASE_DIR")
        module.calls.append({k: os.environ.get(k) for k in keys})
        old = pd.read_excel(nlp / "NLP_Sentiment_Detail_2026.xlsx")
        new = pd.DataFrame([{"Company": "BSP", "Article_Date": "22 Sep 2026",
                             "Final_Score": 0.4, "Article_Title": "BSP Q3",
                             "Text_Length": 900}])
        pd.concat([old, new]).to_excel(nlp / "NLP_Sentiment_Detail_2026-09-23_FINAL.xlsx",
                                       index=False)
        if fail is not None:
            raise fail

    module.SentimentManagement = SentimentManagement
    module._kjor_async = lambda coro: None      # marks the fixed scraper
    return module


class PriceFixes(unittest.TestCase):
    setUp, tearDown = ManagementDownload.setUp, ManagementDownload.tearDown
    run_main, folder, status = (ManagementDownload.run_main, ManagementDownload.folder,
                                ManagementDownload.status)

    def test_a_one_day_bad_price_is_removed_not_rescaled(self):
        # ELABS.OL 2021-09-29: 242 -> 23.9 -> 238.5, one bad day.
        elabs = walk(240.0, 20)
        elabs.iloc[150] = elabs.iloc[149] * 0.0988
        elabs.iloc[151] = elabs.iloc[150] * 9.979
        self.yahoo.prices = {**universe(), "AAA.OL": elabs}
        code, out = self.run_main("AAA")
        self.assertIn("removed 1 one-day bad price(s)", out)
        self.assertNotIn("repaired unit error", out)
        self.assertEqual(self.status("subset")["AAA.OL"], "repaired")
        close = pd.read_csv(self.folder("subset") / "management_prices_close.csv",
                            index_col="Date", parse_dates=True)["AAA.OL"]
        self.assertTrue(np.isnan(close.iloc[150]))
        self.assertAlmostEqual(close.iloc[0], elabs.iloc[0])      # nothing rescaled
        self.assertLess((close / close.shift(1)).max(), MD.UPPER_RATIO)

    def test_a_series_that_is_mostly_zeros_is_excluded(self):
        # OTEC.OL: 902 of 1940 prices were zero.
        otec = walk(5.0, 21)
        otec.iloc[::2] = 0.0
        self.yahoo.prices = {**universe(), "AAA.OL": otec}
        code, out = self.run_main("AAA", "BSP")
        self.assertIn("prices are zero, negative or not numbers - ticker excluded", out)
        self.assertEqual(self.status("subset")["AAA.OL"], "excluded")

    def test_a_ticker_failing_inside_yahoos_repair_is_retried_without_it(self):
        self.yahoo.fail_with_repair = {"CCC.OL"}
        code, out = self.run_main("5")
        self.assertIn("CCC.OL: prices found without Yahoo's price repair", out)
        self.assertEqual(self.status("subset")["CCC.OL"], "ok")

    def test_unreadable_dates_are_shown(self):
        rows = pd.read_excel(self.nlp / "NLP_Sentiment_Detail_2026.xlsx")
        rows.loc[0, "Article_Date"] = "12 mai 2025"
        rows.to_excel(self.nlp / "NLP_Sentiment_Detail_2026.xlsx", index=False)
        code, out = self.run_main("5")
        self.assertIn("dates that could not be read, e.g.: '12 mai 2025'", out)


class ArticleStep(unittest.TestCase):
    setUp, tearDown = ManagementDownload.setUp, ManagementDownload.tearDown
    run_main, folder, status = (ManagementDownload.run_main, ManagementDownload.folder,
                                ManagementDownload.status)

    def run_with(self, scraper, *args):
        with patch.dict(sys.modules, {"Only_260820": scraper}), \
                patch.object(MD, "SCRAPER_PACKAGES", ()):
            return self.run_main(*args, "--articles")

    def test_missing_scraper_packages_skip_the_download(self):
        scraper = fake_scraper(self.nlp)
        with patch.dict(sys.modules, {"Only_260820": scraper}), \
                patch.object(MD, "SCRAPER_PACKAGES", ("no_such_package_xyz",)):
            code, out = self.run_main("5", "--articles")
        self.assertEqual(scraper.calls, [], "the scraper must not start")
        self.assertIn("Article download skipped: the scraper needs no_such_package_xyz", out)
        self.assertIn("[STEP 4/8] WARN", out)
        self.assertIn("[STEP 8/8] OK", out)

    def test_new_articles_are_downloaded_for_the_chosen_companies(self):
        scraper = fake_scraper(self.nlp)
        before = os.environ.get("AKSJE_NLP_SELSKAPER")
        code, out = self.run_with(scraper, "5")
        self.assertEqual(scraper.calls[0]["AKSJE_NLP_SELSKAPER"], "2020,AAA,BSP,CCC,DDD")
        self.assertEqual(scraper.calls[0]["AKSJE_NLP_HENT"], "1")
        self.assertEqual(scraper.calls[0]["AKSJE_NLP_ONLY_DOWNLOAD"], "1")
        self.assertIn("[STEP 4/8] OK", out)
        self.assertIn("1 new article(s); newest article is now 2026-09-22", out)
        self.assertIn("[STEP 8/8] OK", out)
        self.assertEqual(os.environ.get("AKSJE_NLP_SELSKAPER"), before, "env restored")

    def test_all_means_every_company_in_the_scrapers_own_list(self):
        scraper = fake_scraper(self.nlp)
        self.run_with(scraper, "all")
        self.assertEqual(scraper.calls[0]["AKSJE_NLP_SELSKAPER"], "")

    def test_a_failed_download_warns_and_prices_are_still_downloaded(self):
        scraper = fake_scraper(self.nlp, RuntimeError("Management download incomplete: EAM"))
        code, out = self.run_with(scraper, "5")
        self.assertIn("[STEP 4/8] WARN", out)
        self.assertIn("Article download failed: RuntimeError: Management download "
                      "incomplete: EAM", out)
        self.assertIn("(1 new ones were saved first)", out)
        self.assertIn("[STEP 8/8] OK", out)
        self.assertEqual(code, 2)

    def test_the_scraper_calling_sys_exit_does_not_end_the_run(self):
        code, out = self.run_with(fake_scraper(self.nlp, SystemExit(1)), "5")
        self.assertIn("the scraper stopped with exit code 1", out)
        self.assertIn("[STEP 8/8] OK", out)

    def test_an_old_scraper_file_is_reported_not_counted_as_ok(self):
        scraper = fake_scraper(self.nlp)
        del scraper._kjor_async
        code, out = self.run_with(scraper, "5")
        self.assertEqual(scraper.calls, [], "the old scraper must not be started")
        self.assertIn("is the old version", out)
        self.assertIn("loaded before this step", out)
        self.assertIn("[STEP 4/8] WARN", out)

    def test_no_articles_skips_the_download(self):
        code, out = self.run_main("5")
        self.assertIn("skipped (--no-articles)", out)
        self.assertIn("[STEP 4/8] OK", out)


OLD_STYLE_SCRAPER = """
import asyncio
import os

calls = []


def SentimentManagement():
    def NLP_Euronext_Quarter4_v41():
        async def main():
            calls.append(os.environ.get("AKSJE_NLP_SELSKAPER"))

        if __name__ == "__main__":
            asyncio.run(main())
    NLP_Euronext_Quarter4_v41()


if __name__ == "__main__":
    raise SystemExit("the module-level check must stay")
"""


def repo_original():
    """Only_260820.py as it was before the fix, from git history."""
    import subprocess
    try:
        return subprocess.run(["git", "show", "7c21574:Only_260820.py"], check=True,
                              capture_output=True, cwd=Path(__file__).resolve().parent
                              ).stdout.decode("utf-8")
    except Exception:
        return None


def v41(text):
    text = text.replace("\r\n", "\n")
    return text[text.index(MD.SCRAPER_START):text.index(MD.SCRAPER_END)]


class ScraperFixedInMemory(unittest.TestCase):
    def test_the_original_file_becomes_the_fixed_scraper(self):
        original = repo_original()
        if original is None:
            self.skipTest("git history not available")
        text, done, missing = MD.patch_scraper_source(original)
        self.assertEqual(missing, [])
        self.assertIn(f"only new articles: all {len(MD.SCRAPER_PATCHES)} changes applied", done)
        self.assertIn("scraper start fixed in 2 place(s)", done)
        self.assertIn("one article without text or score no longer stops the scraper", done)
        fixed = (Path(__file__).resolve().parent / "Only_260820.py").read_text(encoding="utf-8")
        self.assertEqual(v41(text), v41(fixed))
        compile(text, "Only_260820.py", "exec", dont_inherit=True)

    def test_a_file_that_differs_still_runs_but_downloads_everything(self):
        original = repo_original()
        if original is None:
            self.skipTest("git history not available")
        changed = original.replace(
            "row_data = await collect_all_article_rows(page, config, sl)",
            "row_data = await collect_all_article_rows(page, config,  sl)", 1)
        text, done, missing = MD.patch_scraper_source(changed)
        self.assertIn("scraper start fixed in 2 place(s)", done)
        self.assertTrue(any("do not match your file" in m for m in missing), missing)
        self.assertNotIn("def load_known_articles", text)
        compile(text, "Only_260820.py", "exec", dont_inherit=True)

    def test_the_sturdiness_change_is_applied_even_when_the_others_do_not_fit(self):
        original = repo_original()
        if original is None:
            self.skipTest("git history not available")
        changed = original.replace(
            "row_data = await collect_all_article_rows(page, config, sl)",
            "row_data = await collect_all_article_rows(page, config,  sl)", 1)
        self.assertNotEqual(changed, original)
        text, done, missing = MD.patch_scraper_source(changed)
        self.assertIn("one article without text or score no longer stops the scraper", done)
        self.assertTrue(any("do not match your file" in m for m in missing), missing)
        self.assertIn("prøves igjen neste gang", v41(text))
        compile(text, "Only_260820.py", "exec", dont_inherit=True)

    def test_the_fixed_file_is_used_as_it_is(self):
        fixed = (Path(__file__).resolve().parent / "Only_260820.py").read_text(encoding="utf-8")
        text, done, missing = MD.patch_scraper_source(fixed)
        self.assertEqual(done, ["already the fixed version, used as it is"])
        self.assertEqual(text, fixed.replace("\r\n", "\n"))

    def test_an_old_style_file_on_disk_is_run_and_left_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Only_260820.py"
            path.write_text(OLD_STYLE_SCRAPER, encoding="utf-8")
            before = path.read_bytes()
            log = io.StringIO()
            report = MD.Report()
            step = MD.Step(report, 4, "test")
            with patch.object(MD, "find_scraper_file", lambda: path), \
                    patch.dict(sys.modules), contextlib.redirect_stdout(log):
                sys.modules.pop("Only_260820", None)
                module = MD.load_scraper(step)
                os.environ["AKSJE_NLP_SELSKAPER"] = "BSP"
                try:
                    module.SentimentManagement()
                finally:
                    os.environ.pop("AKSJE_NLP_SELSKAPER", None)
            self.assertEqual(module.calls, ["BSP"], "the scraper must really run")
            self.assertEqual(path.read_bytes(), before, "the file on disk is not changed")
            self.assertTrue(any("v4.1 scraper was not found" in w for w in step.warnings))


class ScraperCompanyList(unittest.TestCase):
    TEXT = (MD.SCRAPER_START + "\n        class Config:\n"
            "            tickers_file: str       = r\"Data_BT\\AllTickers_OSEBX_TW_current.xlsx\"\n"
            + MD.SCRAPER_END + "\n")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def settings(self, companies):
        s = MD.Settings(base_dir=self.base, companies=companies)
        s.out_dir.mkdir(parents=True)
        return s

    def point(self, companies, names):
        step = MD.Step(MD.Report(), 4, "test")
        with contextlib.redirect_stdout(io.StringIO()):
            text = MD.point_at_company_list(step, self.settings(companies), self.TEXT, names)
        return text, step

    def test_a_missing_list_is_replaced_by_the_chosen_companies(self):
        text, step = self.point(["all"], ["2020", "ABG", "BSP"])
        target = self.base / MD.OUTPUT_DIR / "management_download" / "all" / "scraper_companies.xlsx"
        self.assertIn(repr(str(target)), text)
        self.assertNotIn("TW_current", text)
        saved = pd.read_excel(target)
        self.assertEqual(saved["Company"].astype(str).tolist(), ["2020", "ABG", "BSP"])
        # Same layout as AllTickers: dropping the first column leaves Company.
        self.assertEqual(list(saved.drop(columns=saved.columns[0]).columns), ["Company"])
        self.assertTrue(any("is missing" in w for w in step.warnings))

    def test_a_full_run_keeps_its_own_list_when_it_exists(self):
        (self.base / "Data_BT").mkdir()
        pd.DataFrame({"Company": ["X"]}).to_excel(
            self.base / "Data_BT" / "AllTickers_OSEBX_TW_current.xlsx")
        text, step = self.point(["all"], ["BSP"])
        self.assertEqual(text, self.TEXT)

    def test_five_companies_always_get_their_own_list(self):
        (self.base / "Data_BT").mkdir()
        pd.DataFrame({"Company": ["X"]}).to_excel(
            self.base / "Data_BT" / "AllTickers_OSEBX_TW_current.xlsx")
        text, step = self.point(["5"], ["2020", "ABG", "BSP", "EAM", "ZAL"])
        self.assertIn("scraper_companies.xlsx", text)
        self.assertEqual(step.warnings, [])


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
