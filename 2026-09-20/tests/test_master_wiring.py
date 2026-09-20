# -*- coding: utf-8 -*-
"""Masteren: henting, datastatus, og at én strategi får feile alene.

Den patchede master.py kjøres her på ekte — den trenger verken pandas eller
nett for disse veiene.
"""
from __future__ import annotations

import logging
import sys
import types
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import support                                                       # noqa: E402
import data_status as ds                                             # noqa: E402

master = support.load_patched("master")
cm = support.load_patched("capital_mail")

I_DAG = date(2026, 9, 20)


def stillelogger():
    logger = logging.getLogger("test-master")
    logger.handlers = [logging.NullHandler()]
    logger.propagate = False
    return logger


def komponent(navn, siste="2026-09-19", antall=3):
    slutt = date.fromisoformat(siste)
    return support.curve(navn, [(str(slutt - timedelta(days=n)), 100.0 + n)
                                for n in reversed(range(antall))])


class FalskMaster:
    """Akkurat det hent_grunnlagsdata og bygg_datastatus rører."""

    def __init__(self, excel_dir="/tmp/ExcelData", innside_dir="/tmp/data"):
        self.excel_dir = Path(excel_dir)
        self.innside_dir = Path(innside_dir)
        self.startkapital = 1_000_000.0

    def oppsett(self):
        return types.SimpleNamespace(risikofri_pst=3.0)

    def insider_oppsett(self):
        return self.oppsett()


class Hentingen(unittest.TestCase):
    def setUp(self):
        self.m = FalskMaster()
        self.logger = stillelogger()

    def _med_build_all(self, svar):
        modul = types.ModuleType("data_acquisition")
        modul.build_all = lambda *a, **k: svar
        sys.modules["data_acquisition"] = modul
        self.addCleanup(sys.modules.pop, "data_acquisition", None)

    def test_statusradene_baerer_kilde_rader_og_siste_videre(self):
        """Datastatusblokken leser nettopp disse feltene."""
        self._med_build_all([{"Kilde": "Kursdata", "Handling": "SKREVET",
                              "Merknad": "1234 rader", "Rader": 1234,
                              "Siste": "2026-09-19"}])
        rader = master.hent_grunnlagsdata(self.m, self.logger, steg=("prices",))
        self.assertEqual(rader[0]["Kilde"], "Kursdata")
        self.assertEqual(rader[0]["Rader"], 1234)
        self.assertEqual(rader[0]["Siste"], "2026-09-19")
        self.assertEqual(rader[0]["Handling"], "SKREVET")

    def test_henting_som_feiler_velter_ikke_kjoringen(self):
        """Status er OK; Handling bærer utfallet. Filene kan jo være ferske."""
        def sprekker(*a, **k):
            raise RuntimeError("Yahoo nede")
        modul = types.ModuleType("data_acquisition")
        modul.build_all = sprekker
        sys.modules["data_acquisition"] = modul
        self.addCleanup(sys.modules.pop, "data_acquisition", None)

        rader = master.hent_grunnlagsdata(self.m, self.logger, steg=("prices",))
        self.assertEqual(rader[0]["Status"], "OK")
        self.assertEqual(rader[0]["Handling"], "FEIL")
        self.assertIn("Yahoo nede", rader[0]["Feil"])

    def test_step4_som_feiler_stopper_sentmom(self):
        """Uten fersk Step4 leser SentMom den forrige — og da er vi tilbake i 2026-09-18."""
        self._med_build_all([{"Kilde": "Sentimentendringer", "Handling": "FEIL",
                              "Merknad": "ingen artikler", "Rader": None,
                              "Siste": None}])
        with self.assertRaises(RuntimeError):
            master.bygg_sentimentendringer(self.m, self.logger)

    def test_step4_som_lykkes_gir_null(self):
        self._med_build_all([{"Kilde": "Sentimentendringer", "Handling": "SKREVET",
                              "Merknad": "900 artikler", "Rader": 900,
                              "Siste": "2026-09-18"}])
        self.assertEqual(master.bygg_sentimentendringer(self.m, self.logger), 0)


class Datastatusen(unittest.TestCase):
    def setUp(self):
        self.m = FalskMaster()
        self.logger = stillelogger()

    def test_kurvene_gjenbrukes_i_stedet_for_a_leses_pa_nytt(self):
        kurver = [komponent(n) for n in ds.STRATEGIER]
        status = master.bygg_datastatus(self.m, [], None, kurver)
        self.assertTrue(status["all_ok"])
        self.assertEqual(len(status["curves"]), 4)

    def test_hentestatus_plukkes_ut_av_kjoringsloggen(self):
        kjoring = [{"Analyse": "Data: Kursdata", "Status": "OK",
                    "Kilde": "Kursdata", "Handling": "FEIL", "Merknad": "nede"},
                   {"Analyse": "PB-ROE-Momentum", "Status": "OK", "Minutter": 3.0}]
        kurver = [komponent(n) for n in ds.STRATEGIER]
        status = master.bygg_datastatus(self.m, kjoring, None, kurver)
        rad = next(r for r in status["rows"]
                   if r["Strategi"] == "Sentiment Momentum v3.1")
        self.assertTrue(rad["Nedlasting"])

    def test_feil_i_statusbyggingen_velter_ikke_mailen(self):
        """Uten pakken faller masteren tilbake til gammel oppførsel, ikke krasj."""
        status = master.bygg_datastatus(self.m, [], None, [])
        self.assertIsInstance(status, dict)


class Kapitalberegningen(unittest.TestCase):
    def setUp(self):
        self.m = FalskMaster()

    def _status(self, foreldet=()):
        kurver = []
        for navn in ds.STRATEGIER:
            manedlig = [("2025-01-31", 100.0), ("2025-02-28", 101.0),
                        ("2025-03-31", 102.0), ("2025-04-30", 103.0)]
            if navn in foreldet:
                manedlig = [("2024-01-31", 100.0), ("2024-02-29", 101.0)]
            kurver.append(support.curve(navn, manedlig))
        status = ds.bygg(kurver, as_of=date(2025, 5, 2))
        status["curves"] = kurver
        return status

    def test_alle_fire_er_med_nar_alle_er_ferske(self):
        status = self._status()
        self.assertEqual(status["included"], list(ds.STRATEGIER))
        self.assertEqual(len(ds.included_curves(status)), 4)

    def test_utelatte_strategier_navngis_i_noekkeltallene(self):
        status = self._status(foreldet=("Sentiment Momentum v3.1",))
        self.assertEqual(status["excluded"], ["Sentiment Momentum v3.1"])
        self.assertEqual(len(ds.included_curves(status)), 3)

    def test_faerre_enn_to_gir_lesbar_feil_ikke_stacktrace(self):
        status = self._status(foreldet=ds.STRATEGIER[1:])
        with self.assertRaises(RuntimeError) as boks:
            master.calculate_capital_portfolio(self.m, datastatus=status)
        self.assertIn("Færre enn to strategier", str(boks.exception))


class Mailen(unittest.TestCase):
    def test_statusblokken_kommer_for_alt_annet_i_kroppen(self):
        kilde = support.patched_source("capital_mail")
        kropp = kilde[kilde.index("<body>"):]
        self.assertLess(kropp.index("{data_status_html}"), kropp.index("{status}"))
        self.assertLess(kropp.index("{data_status_html}"), kropp.index("{main}"))

    def test_feilrapporten_leder_med_datastatus(self):
        html = master.failure_report(["noe gikk galt"],
                                     data_status_html="<div>STATUSBLOKK</div>")
        self.assertLess(html.index("STATUSBLOKK"), html.index("No current performance"))

    def test_feilrapporten_virker_fortsatt_uten_statusblokk(self):
        html = master.failure_report(["noe gikk galt"])
        self.assertIn("noe gikk galt", html)

    def test_overskriften_teller_strategiene(self):
        self.assertEqual(cm._overskrift({"metrics": {"N_Strategier": 4}}),
                         "Fire strategier med 25 % kapital hver")
        self.assertEqual(
            cm._overskrift({"metrics": {"N_Strategier": 3,
                                        "Andel_Per_Strategi_Pst": 100 / 3}}),
            "3 strategier med 33 % kapital hver")

    def test_overskriften_taler_tom_portefolje(self):
        self.assertIn("Fire strategier", cm._overskrift(None))


class Kjoreflyten(unittest.TestCase):
    """Struktursjekker på den patchede kilden: rekkefølge og gating."""

    def setUp(self):
        self.kilde = support.patched_source("master")

    def test_manglende_grunnlagsdata_stopper_ikke_analysene(self):
        self.assertNotIn(
            'errors.extend("Required upstream data missing: " + f for f in missing)',
            self.kilde)
        self.assertIn('kjoring.extend(kjor_alle(m, logger))', self.kilde)

    def test_analysefeil_legges_ikke_lenger_rett_i_errors(self):
        self.assertNotIn(
            'errors.extend(r["Analyse"] + ": " + r["Feil"] for r in kjoring',
            self.kilde)

    def test_step4_bygges_etter_skrapingen_og_for_sentmom(self):
        i_skrap = self.kilde.index("NLP-artikler — skraping")
        i_step4 = self.kilde.index('"Sentimentendringer — Step4"')
        i_sentmom = self.kilde.index("O.SentimentMomentumV31")
        self.assertLess(i_skrap, i_step4)
        self.assertLess(i_step4, i_sentmom)

    def test_analyser_tilordnes_bare_en_gang(self):
        """En dobbel tilordning ville ha kastet Step4 ut av lista i stillhet."""
        self.assertEqual(
            sum(1 for l in self.kilde.splitlines()
                if l.strip().startswith("analyser = [")), 1)

    def test_tickerliste_og_kurser_hentes_for_analysene(self):
        i_hent = self.kilde.index('steg=("tickers", "prices")')
        i_kjor = self.kilde.index("kjoring.extend(kjor_alle(m, logger))")
        self.assertLess(i_hent, i_kjor)

    def test_datastatus_bygges_for_kapitalberegningen(self):
        i_status = self.kilde.index("datastatus = bygg_datastatus")
        i_kapital = self.kilde.index("datastatus=datastatus")
        self.assertLess(i_status, i_kapital)

    def test_mail_strategier_finnes_ogsa_flatt_i_roten(self):
        self.assertIn("mappe = SKRIPTMAPPE          #", self.kilde)

    def test_nye_brytere_finnes(self):
        for flagg in ("--ingen-datahent", "--tving-datahent", "--kostnadstest"):
            self.assertIn(flagg, self.kilde)


if __name__ == "__main__":
    unittest.main()
