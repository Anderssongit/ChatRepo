# -*- coding: utf-8 -*-
"""Datastatusblokken øverst i mailen."""
from __future__ import annotations

import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import support                                                       # noqa: E402
import data_status as ds                                             # noqa: E402
import mail_status as mst                                            # noqa: E402

I_DAG = date(2026, 9, 20)


def komponent(navn, siste="2026-09-19", antall=3):
    slutt = date.fromisoformat(siste)
    punkter = [(str(slutt - timedelta(days=n)), 100.0 + n)
               for n in reversed(range(antall))]
    return support.curve(navn, punkter)


def status(endre=None, acquisition=()):
    kurver = [komponent(n) for n in ds.STRATEGIER]
    if endre:
        kurver = endre(kurver)
    return ds.bygg(kurver, as_of=I_DAG, acquisition=acquisition)


class AlleOk(unittest.TestCase):
    def setUp(self):
        self.html = mst.render(status())

    def test_overskriften_sier_at_alt_er_ferskt(self):
        self.assertIn("alle fire strategier har ferske data", self.html)
        self.assertIn(mst.GRONN, self.html)

    def test_hver_strategi_har_sin_linje(self):
        for navn in ds.STRATEGIER:
            self.assertIn(navn, self.html)

    def test_ingen_problemliste_nar_alt_er_ok(self):
        self.assertNotIn("Hva som mangler", self.html)

    def test_rapportdatoen_star_der(self):
        self.assertIn("2026-09-20", self.html)


class NoeMangler(unittest.TestCase):
    def setUp(self):
        def gammel(kurver):
            kurver[2] = komponent("Sentiment Momentum v3.1", siste="2026-08-19")
            return kurver
        self.status = status(gammel)
        self.html = mst.render(self.status)

    def test_overskriften_sier_fra(self):
        self.assertIn("ikke alle strategier har ferske data", self.html)
        self.assertIn(mst.ROD, self.html)

    def test_den_foreldede_navngis_med_grunn(self):
        self.assertIn("Hva som mangler", self.html)
        self.assertIn("Sentiment Momentum v3.1", self.html)
        self.assertIn("2026-08-19", self.html)
        self.assertIn("FORELDET", self.html)

    def test_folgen_for_fellestallene_star_der(self):
        self.assertIn("Utelatt fra samlet portefølje", self.html)
        self.assertIn("erstattes ikke med null avkastning", self.html)
        self.assertIn("videreføres ikke som om den var dagens", self.html)

    def test_de_tre_andre_er_fortsatt_merket_som_med(self):
        self.assertEqual(self.html.count("Inngår i samlet portefølje"), 3)


class Grunnlagsfilene(unittest.TestCase):
    def test_hentetabellen_vises_med_radantall(self):
        html = mst.render(status(acquisition=[
            {"Kilde": "Kursdata", "Handling": "SKREVET",
             "Merknad": "1 234 rader", "Rader": 1234, "Siste": "2026-09-19"}]))
        self.assertIn("Grunnlagsfilene kjøringen bygde", html)
        self.assertIn("lastet ned og skrevet", html)
        self.assertIn("1 234", html)

    def test_feilet_henting_markeres(self):
        html = mst.render(status(acquisition=[
            {"Kilde": "Kursdata", "Handling": "FEIL", "Merknad": "Yahoo nede"}]))
        self.assertIn("feilet", html)
        self.assertIn("Yahoo nede", html)

    def test_uten_henting_vises_ingen_tabell(self):
        self.assertNotIn("Grunnlagsfilene kjøringen bygde", mst.render(status()))


class Robusthet(unittest.TestCase):
    def test_tom_status_gir_lesbar_blokk_ikke_unntak(self):
        self.assertIn("Datastatus", mst.render({}))
        self.assertIn("Datastatus", mst.render({"rows": []}))

    def test_html_escapes(self):
        farlig = ds.bygg([support.curve(ds.STRATEGIER[0], [],
                                        errors=["<script>alert(1)</script>"])],
                         as_of=I_DAG)
        html = mst.render(farlig)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_fremtidsdato_vises_som_frem_i_tid(self):
        def fremtid(kurver):
            kurver[0] = komponent(ds.STRATEGIER[0], siste="2026-10-05")
            return kurver
        self.assertIn("FREM I TID", mst.render(status(fremtid)))

    def test_blokken_krever_ingen_tunge_pakker(self):
        """mail_status skal kunne bygges uten pandas eller pipelinen."""
        import importlib, sys as _sys
        fjernet = {n: _sys.modules.pop(n) for n in
                   ("pandas", "numpy", "innsidehandel_pipeline")
                   if n in _sys.modules}
        try:
            importlib.reload(mst)
            self.assertIn("Datastatus", mst.render(status()))
        finally:
            _sys.modules.update(fjernet)


if __name__ == "__main__":
    unittest.main()
