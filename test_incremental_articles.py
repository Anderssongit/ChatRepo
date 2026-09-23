"""Only new articles: the v4.1 scraper's own functions, against a fake browser page.

The functions are taken from Only_260820.py itself (no copy), so these tests
fail if the scraper changes. Nothing here opens a browser or the network.
"""
import ast
import asyncio
import logging
import sys
import tempfile
import textwrap
import time
import types
import unittest
from pathlib import Path
from typing import List, Optional, Set

import pandas as pd

SOURCE = Path(__file__).resolve().parent / "Only_260820.py"
WANTED = ("_selskapsnokkel", "_artikkel_url", "_er_kjent", "load_known_articles",
          "collect_all_article_rows", "save_results")


def scraper_functions(**extra):
    text = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(text)
    outer = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                 and n.name == "NLP_Euronext_Quarter4_v41")
    ns = {"pd": pd, "log": logging.getLogger("test_incremental"), "time": time,
          "Set": Set, "List": List, "Optional": Optional, "Path": Path,
          "Config": object, "StepLogger": object, **extra}
    for node in outer.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in WANTED:
            exec(textwrap.dedent(ast.get_source_segment(text, node)), ns)
    missing = [w for w in WANTED if w not in ns]
    assert not missing, missing
    return ns


class Log:
    def __init__(self):
        self.lines = []

    def info(self, text):
        self.lines.append(text)

    ok = warn = fail = step = info


class FakePage:
    """Each page is the list of rows the article table's JavaScript returns."""

    def __init__(self, pages):
        self.pages, self.at = pages, 0

    async def wait_for_selector(self, *a, **k):
        pass

    async def wait_for_timeout(self, ms):
        pass

    async def wait_for_load_state(self, *a, **k):
        pass

    async def evaluate(self, script):
        return self.pages[self.at]


async def next_page(page, sl):
    if page.at + 1 < len(page.pages):
        page.at += 1
        return True
    return False


def row(n, date):
    return {"nid": str(n), "title": f"Rapport {n}", "date": date, "href": ""}


CONFIG = types.SimpleNamespace(max_pages=15, max_articles_per_company=100,
                               euronext_base="https://live.euronext.com")


class OnlyNewArticles(unittest.TestCase):
    def setUp(self):
        self.ns = scraper_functions(_click_next_page=next_page)

    def collect(self, pages, known):
        stats = {}
        page = FakePage(pages)
        rows = asyncio.run(self.ns["collect_all_article_rows"](page, CONFIG, Log(), known, stats))
        return rows, stats, page

    def test_stops_at_the_first_page_that_is_already_saved(self):
        pages = [[row(9, "20 Sep 2026"), row(8, "10 Sep 2026")],
                 [row(7, "01 Sep 2026"), row(6, "20 Aug 2026")],   # already saved
                 [row(5, "01 Aug 2026"), row(4, "20 Jul 2026")]]   # never opened
        known = {("url", "modal://7"), ("url", "modal://6"),
                 ("url", "modal://5"), ("url", "modal://4")}
        rows, stats, page = self.collect(pages, known)
        self.assertEqual([r["nid"] for r in rows], ["9", "8"])
        self.assertEqual(page.at, 1, "page 3 must not be opened")
        self.assertEqual(stats["kjente"], 2)

    def test_a_page_with_old_and_new_rows_keeps_only_the_new_ones(self):
        pages = [[row(9, "20 Sep 2026"), row(7, "01 Sep 2026")],
                 [row(6, "20 Aug 2026")]]
        rows, stats, _ = self.collect(pages, {("url", "modal://7"), ("url", "modal://6")})
        self.assertEqual([r["nid"] for r in rows], ["9"])

    def test_nothing_new_is_up_to_date_not_an_empty_company(self):
        rows, stats, _ = self.collect([[row(7, "01 Sep 2026")]], {("url", "modal://7")})
        self.assertEqual(rows, [])
        self.assertEqual(stats["kjente"], 1)     # scrape_company reads this as up to date

    def test_title_and_date_match_when_the_url_differs(self):
        known = {("tittel", "Rapport 7", "01 Sep 2026")}
        rows, _, _ = self.collect([[row(9, "20 Sep 2026"), row(7, "01 Sep 2026")]], known)
        self.assertEqual([r["nid"] for r in rows], ["9"])

    def test_without_saved_articles_everything_is_fetched_as_before(self):
        pages = [[row(9, "20 Sep 2026")], [row(8, "10 Sep 2026")]]
        rows, stats, _ = self.collect(pages, None)
        self.assertEqual([r["nid"] for r in rows], ["9", "8"])
        self.assertEqual(stats, {})


class SavedArticles(unittest.TestCase):
    def setUp(self):
        self.ns = scraper_functions()
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.config = types.SimpleNamespace(nlp_dir=self.dir)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, rows):
        pd.DataFrame(rows).to_excel(self.dir / name, index=False)

    def test_known_articles_from_every_file_without_duplicates(self):
        a = {"Company": "BSP", "Article_Title": "Q2", "Article_Date": "15 Aug 2026",
             "Article_URL": "modal://1", "Final_Score": 0.1, "Text_Length": 900}
        self.write("NLP_Sentiment_Detail_2026-09-01_FINAL.xlsx", [
            a, {"Company": 2020, "Article_Title": "Q2", "Article_Date": "20 Aug 2026",
                "Article_URL": "modal://2", "Final_Score": 0.2, "Text_Length": 900},
            {"Company": "EAM", "Article_Title": "INGEN ARTIKLER", "Article_Date": "",
             "Article_URL": "", "Final_Score": 0.0, "Text_Length": 0}])
        self.write("NLP_Sentiment_Detail_2026-09-08_FINAL.xlsx", [dict(a, Final_Score=0.3)])
        (self.dir / "~$NLP_Sentiment_Detail_open.xlsx").write_bytes(b"lock")
        known, rows = self.ns["load_known_articles"](self.config)
        self.assertEqual(len(rows), 2)                    # BSP once, 2020 once, no INGEN
        self.assertEqual(sorted(known), ["2020", "BSP"])  # 2020.0 from Excel is 2020
        self.assertIn(("url", "modal://1"), known["BSP"])
        self.assertIn(("tittel", "Q2", "15 Aug 2026"), known["BSP"])
        self.assertEqual(next(r for r in rows if r["Company"] == "BSP")["Final_Score"], 0.3)

    def test_an_unreadable_file_is_skipped(self):
        (self.dir / "NLP_Sentiment_Detail_bad.xlsx").write_bytes(b"not excel")
        self.assertEqual(self.ns["load_known_articles"](self.config), ({}, []))

    def test_the_saved_file_holds_the_old_and_the_new_articles(self):
        old = [{"Company": "BSP", "Article_Title": "Q1", "Article_Date": "15 May 2026",
                "Final_Score": 0.1, "Positive_Score": .5, "Neutral_Score": .1,
                "Negative_Score": .4}]
        new = [dict(old[0], Article_Title="Q2", Article_Date="15 Aug 2026")]
        self.ns["save_results"](old + new, self.config, "2026-09-23", final=True)
        saved = pd.read_excel(self.dir / "NLP_Sentiment_Detail_2026-09-23_FINAL.xlsx")
        self.assertEqual(sorted(saved["Article_Title"]), ["Q1", "Q2"])


class ScraperRunsWhenImported(unittest.TestCase):
    def test_no_main_guard_is_left_in_the_scrapers(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        for name in ("NLP_Euronext_Quarter4_v4", "NLP_Euronext_Quarter4_v41"):
            outer = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                         and n.name == name)
            guards = [n for n in outer.body if isinstance(n, ast.If)
                      and "__name__" in ast.dump(n.test)]
            self.assertEqual(guards, [], f"{name} would do nothing when imported")
            self.assertIn("_kjor_async", ast.dump(outer.body[-1]))

    def test_kjor_async_runs_a_coroutine(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                    and n.name == "_kjor_async")
        ns = {}
        exec(ast.get_source_segment(SOURCE.read_text(encoding="utf-8"), node), ns)

        async def answer():
            return 42
        self.assertEqual(ns["_kjor_async"](answer()), 42)


if __name__ == "__main__":
    unittest.main()
