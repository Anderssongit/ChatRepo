# -*- coding: utf-8 -*-
"""Bygging av de tre grunnlagsfilene. Radlogikken er ren Python og testes her.

Den viktigste testen i fila er `test_tickerfila_far_navnet_strategiene_leser`:
2026-09-18-utgaven skrev en DATERT tickerfil, men PBROE_All3 leser en fast sti.
Fila ble dermed aldri lest.
"""
from __future__ import annotations

import sys
import unittest
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import support                                                       # noqa: E402
import data_acquisition as da                                        # noqa: E402

ROT = support.ROT


class FastFilnavn(unittest.TestCase):
    def test_tickerfila_far_navnet_strategiene_leser(self):
        """Navnet er ikke en dato — det er en nøkkel inn i hash-beskyttet kode."""
        self.assertEqual(da.TICKER_FILENAME, "AllTickers_OSEBX_TW_260428.xlsx")

    def test_navnet_star_faktisk_i_only_260820(self):
        kilde = (ROT / "Only_260820.py").read_text(encoding="utf-8", errors="replace")
        self.assertIn(da.TICKER_FILENAME, kilde)
        # PBROE_All3 og SentimentManagement: fem faste referanser til samme fil.
        self.assertGreaterEqual(kilde.count(da.TICKER_FILENAME), 2)

    def test_runtime_config_krever_samme_navn(self):
        kilde = (ROT / "runtime_config.py").read_text(encoding="utf-8")
        self.assertIn(da.TICKER_FILENAME, kilde)


class Tickerrader(unittest.TestCase):
    def test_company_er_det_bare_symbolet(self):
        """PB-ROE bygger tradingview.com/symbols/OSL-<Company>/ av feltet."""
        rader = da.ticker_workbook_rows([
            {"Symbol": "EQNR.OL", "Selskap": "Equinor", "ISIN": "NO1", "Marked": "XOSL"}])
        self.assertEqual(rader[0]["Company"], "EQNR")
        self.assertEqual(rader[0]["Ticker"], "EQNR.OL")
        self.assertEqual(rader[0]["Name"], "Equinor")

    def test_duplikater_fjernes_og_rader_sorteres(self):
        rader = da.ticker_workbook_rows([
            {"Symbol": "YAR.OL"}, {"Symbol": "AKER.OL"}, {"Symbol": "YAR"}])
        self.assertEqual([r["Company"] for r in rader], ["AKER", "YAR"])

    def test_tomme_symboler_hoppes_over(self):
        self.assertEqual(da.ticker_workbook_rows([{"Symbol": ""}, {"Ticker": None}]), [])

    def test_navn_faller_tilbake_til_symbolet(self):
        self.assertEqual(da.ticker_workbook_rows([{"Symbol": "XX.OL"}])[0]["Name"], "XX")


class Kursrader(unittest.TestCase):
    def serier(self):
        return {"EQNR.OL": {date(2025, 1, 2): {"close": 300.0, "adjclose": 299.0,
                                               "volum": 1000},
                            date(2025, 1, 3): {"close": 305.0}},
                "^OSEBX": {date(2025, 1, 2): {"close": 1500.0}}}

    def test_indekser_utelates(self):
        rader = da.price_workbook_rows(self.serier())
        self.assertEqual({r["Ticker"] for r in rader}, {"EQNR.OL"})

    def test_company_matcher_step4_navnene(self):
        rader = da.price_workbook_rows(self.serier(), {"EQNR": "Equinor"})
        self.assertEqual(rader[0]["Company"], "Equinor")

    def test_startdato_avkorter(self):
        rader = da.price_workbook_rows(self.serier(), start=date(2025, 1, 3))
        self.assertEqual([r["Date"] for r in rader], [date(2025, 1, 3)])

    def test_ubrukelige_kurser_hoppes_over(self):
        serier = {"X.OL": {date(2025, 1, 2): {"close": 0.0},
                           date(2025, 1, 3): {"close": None},
                           date(2025, 1, 6): {"close": 10.0}}}
        self.assertEqual(len(da.price_workbook_rows(serier)), 1)


class Sentimentendringer(unittest.TestCase):
    def artikler(self):
        return [
            {"Company": "Equinor", "Article_Date": "2025-01-10",
             "Article_Title": "Q4", "Final_Score": 0.20},
            {"Company": "Equinor", "Article_Date": "2025-04-10",
             "Article_Title": "Q1", "Final_Score": 0.50},
            {"Company": "Yara", "Article_Date": "2025-02-01",
             "Article_Title": "Q4", "Final_Score": -0.10},
        ]

    def test_forste_artikkel_per_selskap_har_ingen_endring(self):
        rader = da.sentiment_change_rows(self.artikler())
        forste = next(r for r in rader if r["Company"] == "Equinor"
                      and r["Report_Index"] == 1)
        self.assertEqual(forste["Sentiment_Change"], 0.0)
        self.assertIsNone(forste["Previous_Score"])

    def test_endringen_er_fra_forrige_rapport(self):
        rader = da.sentiment_change_rows(self.artikler())
        andre = next(r for r in rader if r["Company"] == "Equinor"
                     and r["Report_Index"] == 2)
        self.assertAlmostEqual(andre["Sentiment_Change"], 0.30)
        self.assertAlmostEqual(andre["Previous_Score"], 0.20)

    def test_selskapene_blandes_ikke(self):
        rader = da.sentiment_change_rows(self.artikler())
        yara = next(r for r in rader if r["Company"] == "Yara")
        self.assertEqual(yara["Sentiment_Change"], 0.0)

    def test_plassholdere_forkastes(self):
        rader = da.sentiment_change_rows([
            {"Company": "X", "Article_Date": "2025-01-01",
             "Article_Title": da.PLACEHOLDER_TITLE, "Final_Score": 0.0}])
        self.assertEqual(rader, [])

    def test_uleselige_rader_hoppes_over(self):
        rader = da.sentiment_change_rows([
            {"Company": "", "Article_Date": "2025-01-01", "Final_Score": 1},
            {"Company": "X", "Article_Date": "rot", "Final_Score": 1},
            {"Company": "X", "Article_Date": "2025-01-01", "Final_Score": None}])
        self.assertEqual(rader, [])

    def test_radene_kommer_i_kronologisk_rekkefolge(self):
        rader = da.sentiment_change_rows(self.artikler())
        self.assertEqual([r["Article_Date"] for r in rader],
                         sorted(r["Article_Date"] for r in rader))

    def test_ticker_kobles_pa_nar_den_finnes(self):
        rader = da.sentiment_change_rows(self.artikler(),
                                         tickers={"Equinor": "EQNR"})
        self.assertEqual({r["Ticker"] for r in rader if r["Company"] == "Equinor"},
                         {"EQNR.OL"})


class DarligFilFarIkkeOverskriveGod(unittest.TestCase):
    def test_tom_ny_fil_avvises(self):
        ok, hvorfor = da.replacement_is_safe(0, None, 500, None)
        self.assertFalse(ok)
        self.assertIn("tom", hvorfor)

    def test_halvferdig_nedlasting_avvises(self):
        ok, hvorfor = da.replacement_is_safe(100, date(2026, 9, 19), 1000, date(2026, 9, 12))
        self.assertFalse(ok)
        self.assertIn("halvferdig", hvorfor)

    def test_kortere_historikk_avvises(self):
        ok, hvorfor = da.replacement_is_safe(1000, date(2026, 8, 1), 1000, date(2026, 9, 12))
        self.assertFalse(ok)
        self.assertIn("dekker mindre historikk", hvorfor)

    def test_normal_oppdatering_slipper_gjennom(self):
        ok, _ = da.replacement_is_safe(1010, date(2026, 9, 19), 1000, date(2026, 9, 12))
        self.assertTrue(ok)

    def test_ingen_tidligere_fil_slipper_gjennom(self):
        ok, hvorfor = da.replacement_is_safe(10, date(2026, 9, 19), None, None)
        self.assertTrue(ok)
        self.assertIn("ingen tidligere fil", hvorfor)

    def test_liten_nedgang_innenfor_grensen_godtas(self):
        ok, _ = da.replacement_is_safe(850, date(2026, 9, 19), 1000, date(2026, 9, 12))
        self.assertTrue(ok)


class Gjenforsok(unittest.TestCase):
    def test_lykkes_pa_andre_forsok(self):
        forsok = {"n": 0}

        def flaky():
            forsok["n"] += 1
            if forsok["n"] < 2:
                raise OSError("midlertidig")
            return "ok"

        self.assertEqual(da.retry(flaky, forsok=3, sov=lambda s: None), "ok")
        self.assertEqual(forsok["n"], 2)

    def test_siste_feil_kastes_videre(self):
        def alltid():
            raise RuntimeError("Yahoo nede")

        with self.assertRaises(RuntimeError):
            da.retry(alltid, forsok=3, sov=lambda s: None)

    def test_pausen_dobles(self):
        pauser = []
        with self.assertRaises(RuntimeError):
            da.retry(lambda: (_ for _ in ()).throw(RuntimeError("x")),
                     forsok=4, pause=2.0, sov=pauser.append)
        self.assertEqual(pauser, [2.0, 4.0, 8.0])

    def test_tastaturavbrudd_gjenforsokes_ikke(self):
        def avbrutt():
            raise KeyboardInterrupt

        with self.assertRaises(KeyboardInterrupt):
            da.retry(avbrutt, forsok=5, sov=lambda s: None)


class Alder(unittest.TestCase):
    def test_manglende_fil_ma_bygges(self):
        må, hvorfor = da.needs_refresh(None, date(2026, 9, 20), 7)
        self.assertTrue(må)
        self.assertEqual(hvorfor, "mangler")

    def test_ukjente_steg_avvises_for_noe_lastes_ned(self):
        with self.assertRaises(ValueError):
            da.build_all(Path("/tmp"), None, None, steps=("tullesteg",))

    def test_datotolkningen_tar_de_vanlige_formene(self):
        for verdi in ("2025-01-02", "02.01.2025", "02/01/2025", "2025/01/02",
                      datetime(2025, 1, 2, 9), date(2025, 1, 2)):
            with self.subTest(verdi=verdi):
                self.assertEqual(da.parse_date(verdi), date(2025, 1, 2))
        self.assertIsNone(da.parse_date("tullball"))


if __name__ == "__main__":
    unittest.main()
