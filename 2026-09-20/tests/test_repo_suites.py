# -*- coding: utf-8 -*-
"""Repoets EGNE tester, kjørt mot de PATCHEDE modulene.

Rotfilene er urørt, så `python -m unittest test_portfolio_blend` i roten kjører
fortsatt den gamle koden og passerer som før. Denne fila svarer på det andre
spørsmålet: holder repoets egne tester fortsatt når rettelsene er påført?

Svaret er ja, bortsett fra fem tester i `test_insider_selection` som beskriver
regelen vi med hensikt har erstattet. Fixturen deres oppgir bare
kostnadskolonner (`Train_Moderate_CAGR_Pst`, `Train_Stress_Worst_Half_CAGR_Pst`)
og ingen `Train_CAGR_Pst`. Under nullkostnadsregelen kvalifiserer da ingen
variant, og baselinen beholdes — som er riktig oppførsel for den nye regelen.

De fem er listet ved navn her. Blir listen lengre eller kortere uten at noen
har ment det, feiler denne testen.
"""
from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import support                                                       # noqa: E402
import patched_import as pi                                          # noqa: E402

# Suiter som skal passere uendret mot de patchede modulene.
UENDRET = ("test_portfolio_blend", "test_capital_mail", "test_master")

# Tester som beskriver den ERSTATTEDE kostnadsregelen, og derfor skal feile.
FORVENTET_ERSTATTET = {
    "test_cost_sensitivity_beats_gross_return",
    "test_later_returns_cannot_change_selection",
    "test_manual_override_preserves_automatic_recommendation_in_audit",
    "test_negative_stress_is_explicitly_disclosed",
    "test_tie_uses_lower_training_turnover",
}

PATCHEDE = ("master", "capital_mail", "portfolio_blend", "insider_selection",
            "innsidehandel_pipeline", "Only_260820")


def _kjor(navn):
    """Kjør én av repoets testmoduler mot patchede rotmoduler."""
    lagret = dict(sys.modules)
    for stem in PATCHEDE:
        sys.modules.pop(stem, None)
    sys.modules.pop(navn, None)
    pi.uninstall()
    pi.install()
    try:
        suite = unittest.defaultTestLoader.loadTestsFromName(navn)
        return unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    finally:
        pi.uninstall()
        sys.modules.clear()
        sys.modules.update(lagret)


class RepoetsEgneTester(unittest.TestCase):
    def test_de_tre_suitene_passerer_mot_patchede_moduler(self):
        for navn in UENDRET:
            with self.subTest(suite=navn):
                r = _kjor(navn)
                self.assertGreater(r.testsRun, 0)
                self.assertEqual(
                    [str(t) for t, _ in r.failures + r.errors], [],
                    f"{navn} feilet mot de patchede modulene")

    def test_bare_de_fem_kjente_innsidetestene_feiler(self):
        r = _kjor("test_insider_selection")
        feilet = {t._testMethodName for t, _ in r.failures + r.errors}
        self.assertEqual(feilet, FORVENTET_ERSTATTET)

    def test_de_fem_feiler_fordi_fixturen_mangler_nullkostnadskolonnen(self):
        """Ikke en regresjon: fixturen oppgir ingen Train_CAGR_Pst i det hele tatt."""
        kilde = (support.ROT / "test_insider_selection.py").read_text(encoding="utf-8")
        self.assertNotIn('"Train_CAGR_Pst"', kilde)
        self.assertIn("Train_Stress_Worst_Half_CAGR_Pst", kilde)

    def test_upatchet_insider_selection_passerer_fortsatt(self):
        """Rotfila er urørt, så den gamle regelen og dens tester lever videre."""
        lagret = dict(sys.modules)
        for stem in PATCHEDE:
            sys.modules.pop(stem, None)
        sys.modules.pop("test_insider_selection", None)
        pi.uninstall()
        try:
            suite = unittest.defaultTestLoader.loadTestsFromName("test_insider_selection")
            r = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
            self.assertEqual(r.failures + r.errors, [])
            self.assertGreaterEqual(r.testsRun, 16)
        finally:
            sys.modules.clear()
            sys.modules.update(lagret)


if __name__ == "__main__":
    unittest.main()
