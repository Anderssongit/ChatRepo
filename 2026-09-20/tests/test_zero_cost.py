# -*- coding: utf-8 -*-
"""Variantvalget: maksimer avkastning uten kostnader, uten å se fremover."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import support                                                       # noqa: E402
import zero_cost as zc                                               # noqa: E402


def rad(navn, train, **extra):
    """En kvalifisert variantrad; overstyr enkeltfelt med nøkkelord."""
    return dict({"Variant": navn, "Train_CAGR_Pst": train,
                 "Train_Days": 500, "Train_Entries": 40, "Train_Tickers": 9,
                 "Train_Worst_Half_CAGR_Pst": train / 2,
                 "Train_Turnover_Per_Year_Pst": 100.0,
                 # Felt som IKKE skal påvirke valget:
                 "Full_CAGR_Pst": 999.0, "Test_CAGR_Pst": 999.0,
                 "Train_Stress_Worst_Half_CAGR_Pst": -50.0}, **extra)


class Kriteriet(unittest.TestCase):
    def test_hoyest_treningsavkastning_vinner(self):
        rader = [rad("daglig", 5.0), rad("forfall-60", 22.0), rad("scorevektet", 13.0)]
        valgt, grunn = zc.select_variant(rader)
        self.assertEqual(valgt["Variant"], "forfall-60")
        self.assertIn("uten handelskostnader", grunn)

    def test_kostnadskolonnene_pavirker_ikke_valget(self):
        """Den gamle regelen ville valgt 'daglig' her. Den nye skal ikke det."""
        rader = [rad("daglig", 5.0, Train_Stress_Worst_Half_CAGR_Pst=9.0),
                 rad("forfall-60", 22.0, Train_Stress_Worst_Half_CAGR_Pst=-40.0)]
        self.assertEqual(zc.select_variant(rader)[0]["Variant"], "forfall-60")

    def test_fullhistorikk_og_testperiode_pavirker_ikke_valget(self):
        rader = [rad("daglig", 20.0, Full_CAGR_Pst=1.0, Test_CAGR_Pst=-90.0),
                 rad("konsentrert", 3.0, Full_CAGR_Pst=99.0, Test_CAGR_Pst=99.0)]
        self.assertEqual(zc.select_variant(rader)[0]["Variant"], "daglig")


class Minstekravene(unittest.TestCase):
    def test_for_kort_historikk_diskvalifiserer(self):
        rader = [rad("daglig", 4.0), rad("kort", 90.0, Train_Days=100)]
        self.assertEqual(zc.select_variant(rader)[0]["Variant"], "daglig")

    def test_for_fa_innganger_diskvalifiserer(self):
        rader = [rad("daglig", 4.0), rad("tynn", 90.0, Train_Entries=3)]
        self.assertEqual(zc.select_variant(rader)[0]["Variant"], "daglig")

    def test_for_fa_aksjer_diskvalifiserer(self):
        rader = [rad("daglig", 4.0), rad("smal", 90.0, Train_Tickers=2)]
        self.assertEqual(zc.select_variant(rader)[0]["Variant"], "daglig")

    def test_negativ_trening_diskvalifiserer(self):
        rader = [rad("daglig", 4.0), rad("taper", -1.0)]
        self.assertEqual(zc.select_variant(rader)[0]["Variant"], "daglig")

    def test_ingen_kvalifiserte_gir_baseline_med_forbehold(self):
        rader = [rad("daglig", -5.0), rad("forfall-60", -2.0)]
        valgt, grunn = zc.select_variant(rader)
        self.assertEqual(valgt["Variant"], "daglig")
        self.assertIn("Daglig baseline beholdes", grunn)
        self.assertIn("dokumenterer ingen varig fordel", grunn)

    def test_manglende_baseline_er_en_feil_ikke_en_gjetning(self):
        with self.assertRaises(ValueError):
            zc.select_variant([rad("forfall-60", 10.0)])


class Likhet(unittest.TestCase):
    def test_beste_svakeste_halvdel_bryter_likhet(self):
        rader = [rad("daglig", 10.0, Train_Worst_Half_CAGR_Pst=1.0),
                 rad("jevn", 10.0, Train_Worst_Half_CAGR_Pst=8.0)]
        self.assertEqual(zc.select_variant(rader)[0]["Variant"], "jevn")

    def test_lavere_omsetning_bryter_neste_likhet(self):
        rader = [rad("daglig", 10.0, Train_Turnover_Per_Year_Pst=900.0),
                 rad("rolig", 10.0, Train_Turnover_Per_Year_Pst=120.0)]
        self.assertEqual(zc.select_variant(rader)[0]["Variant"], "rolig")

    def test_manglende_halvdelstall_vinner_ikke_en_likhet(self):
        rader = [rad("daglig", 10.0, Train_Worst_Half_CAGR_Pst=2.0),
                 rad("ukjent", 10.0, Train_Worst_Half_CAGR_Pst=None)]
        self.assertEqual(zc.select_variant(rader)[0]["Variant"], "daglig")

    def test_full_likhet_folger_fast_variantrekkefolge(self):
        rader = [rad("daglig", 10.0), rad("b", 10.0), rad("a", 10.0)]
        self.assertEqual(zc.select_variant(rader)[0]["Variant"], "daglig")


class Forbeholdet(unittest.TestCase):
    def test_ujevnt_resultat_opplyses(self):
        rader = [rad("daglig", 10.0, Train_Worst_Half_CAGR_Pst=-4.0)]
        _, grunn = zc.select_variant(rader)
        self.assertIn("taper i minst én", grunn)

    def test_jevnt_resultat_far_ikke_forbeholdet(self):
        rader = [rad("daglig", 10.0, Train_Worst_Half_CAGR_Pst=6.0)]
        self.assertNotIn("taper i minst én", zc.select_variant(rader)[1])

    def test_politikken_dokumenterer_nullkostnad_og_horisont(self):
        p = zc.policy("2025-06-30")
        self.assertEqual(p["cost_per_side_pct"], 0.0)
        self.assertEqual(p["selection_cutoff"], "2025-06-30")
        self.assertIn("Ingen", p["lookahead"])

    def test_forbeholdene_sier_at_nullkostnad_er_en_forutsetning(self):
        self.assertIn("forutsetning", zc.LIMITATIONS[0])


class PatchetVelger(unittest.TestCase):
    """Den patchede insider_selection skal faktisk bruke zero_cost."""

    def setUp(self):
        self.mod = support.load_patched("insider_selection")

    def test_policy_version_er_byttet(self):
        self.assertEqual(self.mod.POLICY_VERSION, "insider-zero-cost-v1")
        self.assertEqual(self.mod.POLICY_VERSION, zc.POLICY_VERSION)

    def test_select_robust_variant_gir_samme_svar_som_zero_cost(self):
        rader = [rad("daglig", 5.0), rad("forfall-60", 22.0)]
        self.assertEqual(self.mod.select_robust_variant(rader)[0]["Variant"],
                         zc.select_variant(rader)[0]["Variant"])

    def test_kostnadsreplay_er_av_som_standard(self):
        import os
        os.environ.pop("AKSJE_KOSTNADSTEST", None)
        self.assertEqual(self.mod._kostnadsnivaaer(), ())

    def test_kostnadsreplay_kan_slas_pa(self):
        import os
        os.environ["AKSJE_KOSTNADSTEST"] = "1"
        try:
            self.assertEqual([n for n, _ in self.mod._kostnadsnivaaer()],
                             ["Moderate", "Stress"])
        finally:
            os.environ.pop("AKSJE_KOSTNADSTEST", None)

    def test_manuelt_valg_er_fortsatt_merket_som_overstyring(self):
        rader = [rad("daglig", 5.0), rad("konsentrert", 22.0)]
        valgt, grunn, anbefalt, overstyrt = self.mod.resolve_choice(rader, "daglig")
        self.assertEqual(valgt["Variant"], "daglig")
        self.assertEqual(anbefalt, "konsentrert")
        self.assertTrue(overstyrt)
        self.assertIn("Manuelt valg", grunn)

    def test_ukjent_manuelt_valg_avvises(self):
        with self.assertRaises(ValueError):
            self.mod.resolve_choice([rad("daglig", 5.0)], "finnes-ikke")


if __name__ == "__main__":
    unittest.main()
