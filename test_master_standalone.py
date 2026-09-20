# -*- coding: utf-8 -*-
"""Tester for rettelsene som ligger inne i master.py.

Kjører uten pandas, uten numpy og uten nett. Alt som testes her er ren Python
inne i master.py — ingen egen mappe, ingen importkrok.
"""
from __future__ import annotations

import ast
import calendar
import html
import unittest
from datetime import date, timedelta
from pathlib import Path

import master
import innsidehandel_pipeline as IP

ROT = Path(__file__).resolve().parent
I_DAG = date(2026, 9, 20)


def kurve(navn, verdier, start_ar=2025, start_mnd=1, **ekstra):
    """NAV på fortløpende månedsslutter."""
    punkter = []
    for n, verdi in enumerate(verdier):
        y, m = divmod((start_mnd - 1) + n, 12)
        y, m = start_ar + y, m + 1
        punkter.append((f"{y:04d}-{m:02d}-{calendar.monthrange(y, m)[1]:02d}", verdi))
    return dict({"name": navn, "observations": punkter, "valid": True,
                 "errors": [], "frequency": "monthly",
                 "source": {"path": f"/tmp/{navn}.xlsx", "mtime_ns": 1, "size": 1}},
                **ekstra)


FLAT = [100.0] * 8
SOM_OF = date(2025, 9, 15)


class Prisvakten(unittest.TestCase):
    """Rettelse 1 — den som gjør 4 av 4 mulig."""

    def setUp(self):
        with open(ROT / "Only_260820.py", encoding="utf-8", newline="") as f:
            self.kilde = f.read()
        self.ny, self.feil = master._bytt_blokk(
            self.kilde, master._PRISVAKT_GAMMEL, master._PRISVAKT_NY)

    def _kropp(self, kilde, navn):
        tre = ast.parse(kilde)
        return next(ast.dump(x) for x in tre.body
                    if isinstance(x, ast.FunctionDef) and x.name == navn)

    def test_blokken_finnes_noyaktig_en_gang(self):
        self.assertEqual(self.feil, "")
        self.assertNotEqual(self.ny, self.kilde)

    def test_vakten_stanser_ikke_lenger_hele_strategien(self):
        self.assertIn("No backtest or variant", self.kilde)
        self.assertNotIn("No backtest or variant", self.ny)

    def test_den_utelater_tickerne_i_stedet(self):
        self.assertIn("_uten_kurs = sorted(", self.ny)
        self.assertIn("close = close[_beholdt].copy()", self.ny)

    def test_den_stopper_fortsatt_om_halve_universet_forsvinner(self):
        self.assertIn("For faa tickere igjen etter prisvalidering", self.ny)
        self.assertIn("max(10, 0.5 * len(_alle))", self.ny)

    def test_ingen_kurs_klippes_eller_gjettes(self):
        self.assertIn("Ingen kurs klippes", self.ny)

    def test_patchet_kilde_parser(self):
        ast.parse(self.ny)

    def test_de_hash_beskyttede_funksjonene_er_uendret(self):
        for navn in ("PBROE_All3", "SentimentMomentumV31"):
            with self.subTest(funksjon=navn):
                self.assertEqual(self._kropp(self.kilde, navn),
                                 self._kropp(self.ny, navn))

    def test_bare_ledelsesfunksjonen_er_endret(self):
        self.assertNotEqual(self._kropp(self.kilde, "SentimentHendelseLab"),
                            self._kropp(self.ny, "SentimentHendelseLab"))

    def test_fila_pa_disk_roeres_aldri(self):
        for var in ("r+", "w", "a"):
            pass
        with open(ROT / "Only_260820.py", encoding="utf-8", newline="") as f:
            self.assertEqual(f.read(), self.kilde)

    def test_manglende_blokk_gir_beskjed_i_stedet_for_stillhet(self):
        _, feil = master._bytt_blokk("helt annen fil", master._PRISVAKT_GAMMEL,
                                     master._PRISVAKT_NY)
        self.assertIn("ble ikke funnet", feil)


class DelviseSteg(unittest.TestCase):
    """Rettelse 2 — et steg som hentet noe stanser ikke de neste."""

    def setUp(self):
        self.original = {n: getattr(IP, n) for n in
                         ("steg1_nedlasting", "steg4_kurser", "steg5_merge")}

        def gjenopprett():
            for n, f in self.original.items():
                setattr(IP, n, f)
        self.addCleanup(gjenopprett)

    def test_delvis_blir_ok_og_kjoringen_fortsetter(self):
        IP.steg1_nedlasting = lambda *a, **k: {
            "status": "DELVIS", "artikler": 3879, "detaljer": "197 selskaper feilet"}
        master.tillat_delvise_steg(IP.stillelogger())
        svar = IP.steg1_nedlasting(None, None)
        self.assertEqual(svar["status"], "OK")
        self.assertTrue(svar["delvis"])
        self.assertIn("197 selskaper feilet", svar["detaljer"])
        self.assertIn("DELVIS", svar["detaljer"])

    def test_feil_forblir_feil(self):
        IP.steg1_nedlasting = lambda *a, **k: {"status": "FEIL", "detaljer": "tomt"}
        master.tillat_delvise_steg(IP.stillelogger())
        self.assertEqual(IP.steg1_nedlasting(None, None)["status"], "FEIL")

    def test_ok_forblir_ok(self):
        IP.steg4_kurser = lambda *a, **k: {"status": "OK", "detaljer": "alt"}
        master.tillat_delvise_steg(IP.stillelogger())
        svar = IP.steg4_kurser(None, None)
        self.assertEqual(svar["status"], "OK")
        self.assertNotIn("delvis", svar)

    def test_dobbel_paafoering_pakker_ikke_to_ganger(self):
        IP.steg5_merge = lambda *a, **k: {"status": "DELVIS", "detaljer": "x"}
        logger = IP.stillelogger()
        master.tillat_delvise_steg(logger)
        forste = IP.steg5_merge
        master.tillat_delvise_steg(logger)
        self.assertIs(IP.steg5_merge, forste)

    def test_alle_tre_grunnstegene_pakkes(self):
        master.tillat_delvise_steg(IP.stillelogger())
        for navn in ("steg1_nedlasting", "steg4_kurser", "steg5_merge"):
            with self.subTest(steg=navn):
                self.assertTrue(getattr(getattr(IP, navn), "_delvis_tillatt", False))


class ValgUtenKostnader(unittest.TestCase):
    """Rettelse 3 — motoren handler uten kostnader, og valget gjør det nå også."""

    def rad(self, navn, train, **ekstra):
        return dict({"Variant": navn, "Train_CAGR_Pst": train, "Train_Days": 500,
                     "Train_Entries": 40, "Train_Tickers": 9,
                     "Train_Turnover_Per_Year_Pst": 100.0,
                     "Full_CAGR_Pst": 999.0, "Test_CAGR_Pst": 999.0,
                     "Train_Stress_Worst_Half_CAGR_Pst": -50.0}, **ekstra)

    def test_hoyest_treningsavkastning_vinner(self):
        rader = [self.rad("daglig", 5.0), self.rad("forfall-60", 22.0)]
        self.assertEqual(master.velg_uten_kostnader(rader)[0]["Variant"], "forfall-60")

    def test_kostnadskolonnen_pavirker_ikke_valget(self):
        rader = [self.rad("daglig", 5.0, Train_Stress_Worst_Half_CAGR_Pst=9.0),
                 self.rad("forfall-60", 22.0, Train_Stress_Worst_Half_CAGR_Pst=-40.0)]
        self.assertEqual(master.velg_uten_kostnader(rader)[0]["Variant"], "forfall-60")

    def test_fremtiden_pavirker_ikke_valget(self):
        rader = [self.rad("daglig", 20.0, Test_CAGR_Pst=-90.0, Full_CAGR_Pst=1.0),
                 self.rad("konsentrert", 3.0, Test_CAGR_Pst=99.0, Full_CAGR_Pst=99.0)]
        self.assertEqual(master.velg_uten_kostnader(rader)[0]["Variant"], "daglig")

    def test_for_tynt_grunnlag_diskvalifiserer(self):
        for felt, verdi in (("Train_Days", 100), ("Train_Entries", 3),
                            ("Train_Tickers", 2)):
            with self.subTest(felt=felt):
                rader = [self.rad("daglig", 4.0),
                         self.rad("flaks", 90.0, **{felt: verdi})]
                self.assertEqual(master.velg_uten_kostnader(rader)[0]["Variant"],
                                 "daglig")

    def test_negativ_trening_diskvalifiserer(self):
        rader = [self.rad("daglig", 4.0), self.rad("taper", -1.0)]
        self.assertEqual(master.velg_uten_kostnader(rader)[0]["Variant"], "daglig")

    def test_ingen_kvalifiserte_gir_baseline_med_forbehold(self):
        valgt, grunn = master.velg_uten_kostnader(
            [self.rad("daglig", -5.0), self.rad("b", -2.0)])
        self.assertEqual(valgt["Variant"], "daglig")
        self.assertIn("dokumenterer ingen varig fordel", grunn)

    def test_lavere_omsetning_bryter_likhet(self):
        rader = [self.rad("daglig", 10.0, Train_Turnover_Per_Year_Pst=900.0),
                 self.rad("rolig", 10.0, Train_Turnover_Per_Year_Pst=120.0)]
        self.assertEqual(master.velg_uten_kostnader(rader)[0]["Variant"], "rolig")

    def test_manglende_baseline_er_en_feil(self):
        with self.assertRaises(ValueError):
            master.velg_uten_kostnader([self.rad("forfall-60", 10.0)])


class Datastatusen(unittest.TestCase):
    """Rettelse 4a — kom dataene ned, per strategi?"""

    def komponent(self, navn, siste="2026-09-19", antall=3, **ekstra):
        slutt = date.fromisoformat(siste)
        punkter = [(str(slutt - timedelta(days=n)), 100.0 + n)
                   for n in reversed(range(antall))]
        return dict({"name": navn, "observations": punkter, "valid": True,
                     "errors": [], "source": {"path": "x.xlsx"}}, **ekstra)

    def test_fersk_er_ok(self):
        rad = master.vurder_strategi("Sentiment Momentum v3.1",
                                     observasjoner=[("2026-09-18", 1.0)],
                                     as_of=I_DAG)
        self.assertEqual(rad["Status"], "OK")
        self.assertTrue(rad["I_Portefolje"])

    def test_manedgammel_er_foreldet(self):
        """Nøyaktig feilen fra 2026-09-18: kursene sluttet 2026-08-19."""
        rad = master.vurder_strategi("Sentiment Momentum v3.1",
                                     observasjoner=[("2026-08-19", 1.0)],
                                     as_of=I_DAG)
        self.assertEqual(rad["Status"], "FORELDET")
        self.assertFalse(rad["I_Portefolje"])
        self.assertIn("32 dager gammel", rad["Begrunnelse"])

    def test_manedlig_pbroe_taler_lengre_hale(self):
        gammel = [("2026-08-19", 1.0)]
        self.assertEqual(master.vurder_strategi(
            "PB-ROE-Momentum", observasjoner=gammel, as_of=I_DAG)["Status"], "OK")
        self.assertEqual(master.vurder_strategi(
            "Sentiment Momentum v3.1", observasjoner=gammel,
            as_of=I_DAG)["Status"], "FORELDET")

    def test_fremtidsdatert_rad_er_ikke_fersk(self):
        rad = master.vurder_strategi("Sentiment Momentum v3.1",
                                     observasjoner=[("2026-10-01", 1.0)],
                                     as_of=I_DAG)
        self.assertEqual(rad["Status"], "FORELDET")
        self.assertIn("merkelapp", rad["Begrunnelse"])

    def test_feil_slar_ferskhet(self):
        rad = master.vurder_strategi("NLP Sentiment — ledelse",
                                     feil=["accounting_version < 2"],
                                     observasjoner=[("2026-09-19", 1.0)],
                                     as_of=I_DAG)
        self.assertEqual(rad["Status"], "FEIL")

    def test_alle_fire_ferske(self):
        status = master.bygg_datastatus(
            [self.komponent(n) for n in master.STRATEGIER], as_of=I_DAG)
        self.assertTrue(status["all_ok"])
        self.assertEqual(len(status["included"]), 4)

    def test_en_foreldet_utelates_og_navngis(self):
        kurver = [self.komponent(n) for n in master.STRATEGIER]
        kurver[2] = self.komponent("Sentiment Momentum v3.1", siste="2026-08-19")
        status = master.bygg_datastatus(kurver, as_of=I_DAG)
        self.assertEqual(status["excluded"], ["Sentiment Momentum v3.1"])
        self.assertEqual(len(status["included"]), 3)
        self.assertIn("33 % kapital til hver", status["summary"])

    def test_analysefeil_teller_med(self):
        kurver = [self.komponent(n) for n in master.STRATEGIER]
        kjoring = [{"Analyse": "Innsidehandel Oslo Børs", "Status": "FEIL",
                    "Feil": "pipelinen stoppet"}]
        status = master.bygg_datastatus(kurver, kjoring, as_of=I_DAG)
        self.assertIn("Innsidehandel — Oslo Børs", status["excluded"])

    def test_manglende_komponent_gir_rad_likevel(self):
        status = master.bygg_datastatus(
            [self.komponent(n) for n in master.STRATEGIER[:3]], as_of=I_DAG)
        self.assertEqual(len(status["rows"]), 4)
        self.assertEqual(status["rows"][-1]["Status"], "FEIL")

    def test_faerre_enn_to_sier_fra(self):
        kurver = [self.komponent(master.STRATEGIER[0])] + [
            self.komponent(n, siste="2026-01-01") for n in master.STRATEGIER[1:]]
        self.assertIn("Færre enn to strategier",
                      master.bygg_datastatus(kurver, as_of=I_DAG)["summary"])


class Statusblokken(unittest.TestCase):
    """Rettelse 4b — den står ØVERST i mailen."""

    def status(self, foreldet=()):
        kurver = []
        for navn in master.STRATEGIER:
            siste = "2026-01-01" if navn in foreldet else "2026-09-19"
            kurver.append({"name": navn, "observations": [(siste, 100.0)],
                           "valid": True, "errors": [], "source": {}})
        return master.bygg_datastatus(kurver, as_of=I_DAG)

    def test_alle_ok_sier_det(self):
        blokk = master.statusblokk_html(self.status())
        self.assertIn("alle fire strategier har ferske data", blokk)
        self.assertNotIn("Hva som mangler", blokk)

    def test_foreldet_navngis_med_grunn(self):
        blokk = master.statusblokk_html(self.status({"Sentiment Momentum v3.1"}))
        self.assertIn("Hva som mangler", blokk)
        self.assertIn("Sentiment Momentum v3.1", blokk)
        self.assertIn("Utelatt fra samlet portefølje", blokk)

    def test_html_escapes(self):
        status = master.bygg_datastatus(
            [{"name": master.STRATEGIER[0], "observations": [],
              "valid": False, "errors": ["<script>x</script>"]}], as_of=I_DAG)
        blokk = master.statusblokk_html(status)
        self.assertNotIn("<script>", blokk)
        self.assertIn("&lt;script&gt;", blokk)

    def test_tom_status_gir_lesbar_blokk(self):
        self.assertIn("Datastatus", master.statusblokk_html({}))

    def test_merknader_vises(self):
        status = self.status()
        status["notes"] = ["Prisvakten kunne ikke rettes"]
        self.assertIn("Prisvakten kunne ikke rettes",
                      master.statusblokk_html(status))


class Blandingen(unittest.TestCase):
    """Rettelse 4c — lik vekt til de som faktisk har ferske data."""

    def test_fire_gir_25_prosent(self):
        res = master.bland_likevektet([kurve(f"S{n}", FLAT) for n in range(4)],
                                      as_of=SOM_OF)
        self.assertEqual(res["metrics"]["N_Strategier"], 4)
        self.assertAlmostEqual(res["metrics"]["Andel_Per_Strategi_Pst"], 25.0)

    def test_tre_gir_en_tredel(self):
        res = master.bland_likevektet([kurve(f"S{n}", FLAT) for n in range(3)],
                                      as_of=SOM_OF)
        self.assertEqual(res["metrics"]["N_Strategier"], 3)
        self.assertAlmostEqual(res["metrics"]["Andel_Per_Strategi_Pst"], 100 / 3)
        self.assertAlmostEqual(sum(h["Andel_Pst"] for h in res["holdings"]), 100.0)

    def test_to_er_nedre_grense(self):
        res = master.bland_likevektet([kurve("A", FLAT), kurve("B", FLAT)],
                                      as_of=SOM_OF)
        self.assertAlmostEqual(res["metrics"]["Andel_Per_Strategi_Pst"], 50.0)

    def test_en_avvises_med_lesbar_beskjed(self):
        with self.assertRaises(RuntimeError) as boks:
            master.bland_likevektet([kurve("A", FLAT)], as_of=SOM_OF)
        self.assertIn("Færre enn to strategier", str(boks.exception))

    def test_startkapitalen_fordeles_fullt_ut(self):
        for antall in (2, 3, 4):
            with self.subTest(antall=antall):
                res = master.bland_likevektet(
                    [kurve(f"S{n}", FLAT) for n in range(antall)],
                    as_of=SOM_OF, startkapital=1_000_000.0)
                self.assertAlmostEqual(res["equity"][0]["Verdi_NOK"], 1_000_000.0)

    def test_like_kurver_gir_kurvens_avkastning(self):
        serie = [100.0, 110.0, 121.0, 133.1, 146.41]
        for antall in (2, 3, 4):
            res = master.bland_likevektet(
                [kurve(f"S{n}", serie) for n in range(antall)],
                as_of=SOM_OF, startkapital=1_000.0)
            with self.subTest(antall=antall):
                self.assertAlmostEqual(res["equity"][-1]["Verdi_NOK"],
                                       1_000.0 * serie[-1] / serie[0], places=6)

    def test_manedsavkastningen_er_gjennomsnittet(self):
        res = master.bland_likevektet(
            [kurve("Opp", [100.0, 110.0, 110.0]), kurve("Flat", [100.0] * 3)],
            as_of=SOM_OF, startkapital=1_000_000.0)
        self.assertAlmostEqual(res["equity"][1]["Verdi_NOK"], 1_050_000.0, places=6)

    def test_rebalanseringen_stiller_tilbake_til_lik_vekt(self):
        res = master.bland_likevektet(
            [kurve("Opp", [100.0, 110.0, 110.0]), kurve("Flat", [100.0] * 3)],
            as_of=SOM_OF, startkapital=1_000_000.0)
        for h in res["holdings"]:
            self.assertAlmostEqual(h["Andel_Pst"], 50.0)

    def test_manglende_fellesmaned_oppfinnes_ikke(self):
        hull = {"name": "Hull", "valid": True, "errors": [], "observations": [
            ("2025-01-31", 100.0), ("2025-02-28", 101.0), ("2025-04-30", 102.0)]}
        with self.assertRaises(RuntimeError) as boks:
            master.bland_likevektet([hull, kurve("Hel", FLAT[:4])], as_of=SOM_OF)
        self.assertIn("nekter å finne opp", str(boks.exception))

    def test_bindende_strategi_navngis(self):
        res = master.bland_likevektet(
            [kurve("Kort", FLAT[:4]), kurve("Lang", FLAT)], as_of=SOM_OF)
        self.assertEqual(res["binding_component"], "Kort")

    def test_fremtidsdaterte_rader_utelates(self):
        res = master.bland_likevektet(
            [kurve("A", FLAT, start_ar=2025), kurve("B", FLAT, start_ar=2025)],
            as_of=date(2025, 4, 15))
        self.assertLessEqual(res["common_period"]["end"], "2025-03-31")

    def test_nullkostnad_star_i_forbeholdene(self):
        res = master.bland_likevektet([kurve(f"S{n}", FLAT) for n in range(4)],
                                      as_of=SOM_OF)
        self.assertIn("Ingen handelskostnader er modellert",
                      " ".join(res["warnings"]))

    def test_tre_strategier_navngir_de_utelatte(self):
        res = master.bland_likevektet([kurve(f"S{n}", FLAT) for n in range(3)],
                                      as_of=SOM_OF, utelatte=["Borte"])
        self.assertIn("Borte", " ".join(res["warnings"]))
        self.assertEqual(res["metrics"]["Utelatte_Strategier"], ["Borte"])

    def test_valggrensen_flytter_startpunktet(self):
        med_grense = kurve("A", FLAT, selection={"Selection_Cutoff": "2025-03-31"})
        res = master.bland_likevektet([med_grense, kurve("B", FLAT)], as_of=SOM_OF)
        self.assertGreaterEqual(res["common_period"]["start"], "2025-03-31")


class Kjoreflyten(unittest.TestCase):
    """At delene faktisk er koblet sammen i master.py."""

    def setUp(self):
        with open(ROT / "master.py", encoding="utf-8", newline="") as f:
            self.kilde = f.read()

    def test_en_strategi_som_feiler_stopper_ikke_de_andre(self):
        self.assertNotIn(
            'errors.extend("Required upstream data missing: " + f for f in missing)',
            self.kilde)
        self.assertNotIn(
            'errors.extend(r["Analyse"] + ": " + r["Feil"] for r in kjoring',
            self.kilde)

    def test_statusblokken_settes_inn_forst_i_mailen(self):
        self.assertIn('html.replace("<body>", "<body>" + statusblokk, 1)',
                      self.kilde)

    def test_blandingen_bruker_datastatusen(self):
        self.assertIn("calculate_capital_portfolio(\n                    m, datastatus",
                      self.kilde.replace("\r\n", "\n"))

    def test_only_lastes_med_rettelsen(self):
        self.assertIn("O, _merknad = last_only_med_rettelser(logger)", self.kilde)
        self.assertNotIn("import Only_260820 as O", self.kilde)

    def test_delvise_steg_slas_pa_for_pipelinen_kjores(self):
        ren = self.kilde.replace("\r\n", "\n")
        self.assertLess(ren.index("tillat_delvise_steg(logger)"),
                        ren.index('kjor("Innsidehandel Oslo Børs"'))

    def test_nullkostnadsvalget_slas_pa(self):
        self.assertIn("bruk_nullkostnadsvalg(logger)", self.kilde)

    def test_mail_strategier_finnes_ogsa_flatt_i_roten(self):
        self.assertIn("mappe = SKRIPTMAPPE\n", self.kilde.replace("\r\n", "\n"))

    def test_master_er_selvstendig(self):
        """Ingen import fra, og ingen sti inn i, en egen rettelsesmappe."""
        for forbudt in ("patched_import", "import data_status",
                        "import mail_status", "import zero_cost",
                        "import price_repair", 'SKRIPTMAPPE / "2026-',
                        "2026-09-20/", "2026-09-20\\\\"):
            with self.subTest(navn=forbudt):
                self.assertNotIn(forbudt, self.kilde)

    def test_master_importerer_bare_det_repoet_allerede_har(self):
        """Alle toppnivaa-importer skal finnes ved siden av master.py."""
        import ast as _ast
        egne = {p.stem for p in ROT.glob("*.py")}
        tre = _ast.parse(self.kilde)
        for node in _ast.walk(tre):
            navn = []
            if isinstance(node, _ast.Import):
                navn = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, _ast.ImportFrom) and node.level == 0 and node.module:
                navn = [node.module.split(".")[0]]
            for n in navn:
                if n in egne or n in ("Only_260820",):
                    continue
                with self.subTest(modul=n):
                    __import__(n)          # stdlib eller installert pakke

    def test_feilrapporten_leder_med_datastatus(self):
        h = master.failure_report(["noe gikk galt"], "<div>STATUSBLOKK</div>")
        self.assertLess(h.index("STATUSBLOKK"), h.index("No current performance"))

    def test_feilrapporten_virker_uten_statusblokk(self):
        self.assertIn("noe gikk galt", master.failure_report(["noe gikk galt"]))

    def test_validate_sources_gir_fire_verdier(self):
        import inspect
        kilde = inspect.getsource(master.validate_sources)
        self.assertIn("return errors, files, per_strategi, kurver", kilde)


if __name__ == "__main__":
    unittest.main()
