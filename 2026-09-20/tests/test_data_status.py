# -*- coding: utf-8 -*-
"""Datastatus per strategi — og hvem som får være med i fellestallene.

Testene her beskriver nøyaktig feilen fra 2026-09-18: Sentiment Momentum sto
som `OK` mens den kjørte på kurser som sluttet tretti dager tidligere.
"""
from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import support                                                       # noqa: E402
import data_status as ds                                             # noqa: E402

I_DAG = date(2026, 9, 20)
FIRE = ds.STRATEGIER
SENTMOM = "Sentiment Momentum v3.1"
PBROE = "PB-ROE-Momentum"


def obs(*datoer):
    return [(d, 100.0 + n) for n, d in enumerate(datoer)]


def komponent(navn, siste="2026-09-19", antall=3, **extra):
    """En eksport som slutter på `siste`."""
    from datetime import timedelta
    slutt = date.fromisoformat(siste)
    datoer = [str(slutt - timedelta(days=n)) for n in reversed(range(antall))]
    return dict(support.curve(navn, obs(*datoer)), **extra)


class Klassifiseringen(unittest.TestCase):
    def test_fersk_eksport_er_ok(self):
        rad = ds.klassifiser(SENTMOM, observations=obs("2026-09-18"), as_of=I_DAG)
        self.assertEqual(rad["Status"], ds.OK)
        self.assertTrue(rad["I_Portefolje"])
        self.assertEqual(rad["Alder_Dager"], 2)

    def test_manedgamle_kurser_er_foreldet(self):
        """Nøyaktig 2026-09-18-feilen: siste observasjon 2026-08-19."""
        rad = ds.klassifiser(SENTMOM, observations=obs("2026-08-19"), as_of=I_DAG)
        self.assertEqual(rad["Status"], ds.FORELDET)
        self.assertFalse(rad["I_Portefolje"])
        self.assertIn("32 dager gammel", rad["Begrunnelse"])
        self.assertIn("gjør ikke kildekursene ferskere", rad["Begrunnelse"])

    def test_manedlig_pbroe_taler_lengre_hale(self):
        """Samme alder, annen strategi: PB-ROE eksporterer månedsverdier."""
        gammel = obs("2026-08-19")
        self.assertEqual(ds.klassifiser(SENTMOM, observations=gammel,
                                        as_of=I_DAG)["Status"], ds.FORELDET)
        self.assertEqual(ds.klassifiser(PBROE, observations=gammel,
                                        as_of=I_DAG)["Status"], ds.OK)

    def test_fremtidsdatert_rad_er_ikke_fersk(self):
        rad = ds.klassifiser(SENTMOM, observations=obs("2026-10-01"), as_of=I_DAG)
        self.assertEqual(rad["Status"], ds.FORELDET)
        self.assertIn("merkelapp", rad["Begrunnelse"])

    def test_tom_eksport_mangler(self):
        rad = ds.klassifiser(SENTMOM, observations=[], as_of=I_DAG)
        self.assertEqual(rad["Status"], ds.MANGLER)

    def test_feil_slar_ferskhet(self):
        """En ugyldig eksport er FEIL selv om datoen ser perfekt ut."""
        rad = ds.klassifiser(SENTMOM, errors=["accounting_version < 2"],
                             observations=obs("2026-09-19"), as_of=I_DAG)
        self.assertEqual(rad["Status"], ds.FEIL)
        self.assertIn("accounting_version", rad["Begrunnelse"])

    def test_analysefeil_teller_som_feil(self):
        rad = ds.klassifiser(SENTMOM, observations=obs("2026-09-19"), as_of=I_DAG,
                             analysis_errors=["Sentiment Momentum v3.1 feilet: X"])
        self.assertEqual(rad["Status"], ds.FEIL)

    def test_ugyldige_datoer_hoppes_over_uten_a_kaste(self):
        span = ds.observation_span([("ikke-en-dato", 1.0), ("2026-09-19", 2.0),
                                    (None, 3.0), "kort"])
        self.assertEqual(span["antall"], 1)
        self.assertEqual(span["siste"], date(2026, 9, 19))


class Hentestatusen(unittest.TestCase):
    def test_skrevet_og_gjenbrukt_er_ikke_problemer(self):
        rader = [{"Kilde": "Kursdata", "Handling": "SKREVET", "Merknad": "ok"},
                 {"Kilde": "PB-ROE tickerliste", "Handling": "GJENBRUKT", "Merknad": "1 d"}]
        self.assertEqual(ds.input_problems(rader), {})

    def test_feilet_henting_tilskrives_riktig_strategi(self):
        rader = [{"Kilde": "Kursdata", "Handling": "FEIL", "Merknad": "Yahoo nede"}]
        per = ds.input_problems(rader)
        self.assertIn(SENTMOM, per)
        self.assertNotIn(PBROE, per)
        self.assertIn("Yahoo nede", per[SENTMOM][0])

    def test_degradert_fil_regnes_som_problem(self):
        rader = [{"Kilde": "Kursdata", "Handling": "DEGRADERT", "Merknad": "halv fil"}]
        self.assertIn(SENTMOM, ds.input_problems(rader))

    def test_tickerlista_treffer_bade_pbroe_og_ledelse(self):
        rader = [{"Kilde": "PB-ROE tickerliste", "Handling": "FEIL", "Merknad": "x"}]
        per = ds.input_problems(rader)
        self.assertEqual(sorted(per), sorted([PBROE, "NLP Sentiment — ledelse"]))

    def test_analysefeil_oversettes_fra_kjoringsnavn(self):
        rader = [{"Analyse": "Innsidehandel Oslo Børs", "Status": "FEIL", "Feil": "nede"}]
        per = ds.analysis_problems(rader)
        self.assertIn("Innsidehandel — Oslo Børs", per)


class Byggingen(unittest.TestCase):
    def _alle_ferske(self):
        return [komponent(navn) for navn in FIRE]

    def test_alle_fire_ferske(self):
        status = ds.bygg(self._alle_ferske(), as_of=I_DAG)
        self.assertTrue(status["all_ok"])
        self.assertEqual(len(status["included"]), 4)
        self.assertEqual(status["excluded"], [])
        self.assertIn("Alle 4 strategiene har ferske data", status["summary"])

    def test_en_foreldet_utelates_og_navngis(self):
        kurver = self._alle_ferske()
        kurver[2] = komponent(SENTMOM, siste="2026-08-19")
        status = ds.bygg(kurver, as_of=I_DAG)
        self.assertFalse(status["all_ok"])
        self.assertEqual(status["excluded"], [SENTMOM])
        self.assertEqual(len(status["included"]), 3)
        self.assertIn("33 % kapital til hver", status["summary"])
        self.assertIn(SENTMOM, status["summary"])

    def test_faerre_enn_to_sier_at_ingen_portefolje_kan_bygges(self):
        kurver = [komponent(FIRE[0])] + [komponent(n, siste="2026-01-01")
                                         for n in FIRE[1:]]
        status = ds.bygg(kurver, as_of=I_DAG)
        self.assertIn("Færre enn to strategier", status["summary"])

    def test_manglende_komponent_gir_en_rad_likevel(self):
        status = ds.bygg([komponent(n) for n in FIRE[:3]], as_of=I_DAG)
        self.assertEqual(len(status["rows"]), 4)
        siste = status["rows"][-1]
        self.assertEqual(siste["Strategi"], FIRE[3])
        self.assertEqual(siste["Status"], ds.FEIL)

    def test_radene_kommer_i_fast_rekkefolge(self):
        status = ds.bygg([komponent(n) for n in reversed(FIRE)], as_of=I_DAG)
        self.assertEqual([r["Strategi"] for r in status["rows"]], list(FIRE))

    def test_komponentfeil_utenfra_tas_med(self):
        status = ds.bygg(self._alle_ferske(), as_of=I_DAG,
                         component_errors={PBROE: ["output was not refreshed"]})
        rad = next(r for r in status["rows"] if r["Strategi"] == PBROE)
        self.assertEqual(rad["Status"], ds.FEIL)
        self.assertIn("not refreshed", rad["Begrunnelse"])

    def test_included_curves_gir_bare_de_ferske_i_rekkefolge(self):
        kurver = self._alle_ferske()
        kurver[1] = komponent(FIRE[1], siste="2026-01-01")
        status = dict(ds.bygg(kurver, as_of=I_DAG), curves=kurver)
        valgte = ds.included_curves(status)
        self.assertEqual([c["name"] for c in valgte],
                         [FIRE[0], FIRE[2], FIRE[3]])

    def test_filsti_og_variant_baeres_videre(self):
        kurver = self._alle_ferske()
        kurver[0]["variant"] = "S1|TP10"
        status = ds.bygg(kurver, as_of=I_DAG)
        self.assertTrue(status["rows"][0]["Fil"].endswith(".xlsx"))
        self.assertEqual(status["rows"][0]["Variant"], "S1|TP10")


class Robusthet(unittest.TestCase):
    def test_uten_pandas_gir_lesbar_status_ikke_unntak(self):
        """hent() skal ikke kaste når eksportene ikke kan leses i det hele tatt."""
        status = ds.hent("/finnes/ikke", "/finnes/heller/ikke", as_of=I_DAG)
        self.assertEqual(len(status["rows"]), 4)
        self.assertFalse(status["all_ok"])
        for rad in status["rows"]:
            self.assertEqual(rad["Status"], ds.FEIL)

    def test_datoformater_tolereres(self):
        from datetime import datetime
        for verdi in ("2026-09-19", "2026-09-19 00:00:00", date(2026, 9, 19),
                      datetime(2026, 9, 19, 12)):
            with self.subTest(verdi=verdi):
                self.assertEqual(ds.to_date(verdi), date(2026, 9, 19))


if __name__ == "__main__":
    unittest.main()
