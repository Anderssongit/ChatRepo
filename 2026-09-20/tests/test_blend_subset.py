# -*- coding: utf-8 -*-
"""Samlet portefølje med lik vekt til N strategier, ikke alltid fire.

Valget var: en strategi uten ferske data utelates og navngis, og fellestallene
beregnes på de som er igjen. Da må vekten være 100/N — ikke 25 % over tre
delporteføljer, som ville ha vist en portefølje som aldri fantes.
"""
from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import support                                                       # noqa: E402

pb = support.load_patched("portfolio_blend")


def kurve(navn, verdier, start_ar=2025, start_mnd=1):
    """NAV på fortløpende månedsslutter fra (start_ar, start_mnd)."""
    import calendar
    punkter = []
    for n, verdi in enumerate(verdier):
        y, m = divmod((start_mnd - 1) + n, 12)
        y, m = start_ar + y, m + 1
        punkter.append((f"{y:04d}-{m:02d}-{calendar.monthrange(y, m)[1]:02d}", verdi))
    return support.curve(navn, punkter)


FLAT = [100.0] * 8
SOM_OF = date(2025, 9, 15)


class LikVekt(unittest.TestCase):
    def test_fire_kurver_gir_25_prosent_hver(self):
        res = pb.build_capital_portfolio(
            [kurve(f"S{n}", FLAT) for n in range(4)], as_of=SOM_OF)
        self.assertEqual(res["metrics"]["N_Strategier"], 4)
        self.assertAlmostEqual(res["metrics"]["Andel_Per_Strategi_Pst"], 25.0)
        for h in res["holdings"]:
            self.assertAlmostEqual(h["Target_Pst"], 25.0)
            self.assertAlmostEqual(h["Andel_Pst"], 25.0)
        self.assertEqual(res["equity"][0]["Antall_Strategier"], 4)

    def test_tre_kurver_gir_en_tredel_hver(self):
        res = pb.build_capital_portfolio(
            [kurve(f"S{n}", FLAT) for n in range(3)], as_of=SOM_OF)
        self.assertEqual(res["metrics"]["N_Strategier"], 3)
        self.assertAlmostEqual(res["metrics"]["Andel_Per_Strategi_Pst"], 100 / 3)
        self.assertEqual(len(res["holdings"]), 3)
        self.assertAlmostEqual(sum(h["Andel_Pst"] for h in res["holdings"]), 100.0)

    def test_to_kurver_er_nedre_grense(self):
        res = pb.build_capital_portfolio(
            [kurve("A", FLAT), kurve("B", FLAT)], as_of=SOM_OF)
        self.assertEqual(res["metrics"]["N_Strategier"], 2)
        self.assertAlmostEqual(res["metrics"]["Andel_Per_Strategi_Pst"], 50.0)

    def test_en_kurve_avvises(self):
        with self.assertRaises(pb.PortfolioDataError):
            pb.build_capital_portfolio([kurve("A", FLAT)], as_of=SOM_OF)

    def test_duplikate_navn_avvises(self):
        with self.assertRaises(pb.PortfolioDataError):
            pb.build_capital_portfolio(
                [kurve("A", FLAT), kurve("A", FLAT), kurve("B", FLAT)], as_of=SOM_OF)

    def test_startkapitalen_fordeles_fullt_ut(self):
        for antall in (2, 3, 4):
            with self.subTest(antall=antall):
                res = pb.build_capital_portfolio(
                    [kurve(f"S{n}", FLAT) for n in range(antall)],
                    as_of=SOM_OF, start_capital=1_000_000.0)
                self.assertAlmostEqual(res["equity"][0]["Verdi_NOK"], 1_000_000.0)


class Avkastningen(unittest.TestCase):
    def test_like_kurver_gir_kurvens_egen_avkastning(self):
        """Uansett antall: N kopier av samme kurve skal gi kurvens avkastning."""
        serie = [100.0, 110.0, 121.0, 133.1, 146.41, 161.051]
        for antall in (2, 3, 4):
            res = pb.build_capital_portfolio(
                [kurve(f"S{n}", serie) for n in range(antall)],
                as_of=SOM_OF, start_capital=1_000.0)
            with self.subTest(antall=antall):
                self.assertAlmostEqual(res["equity"][-1]["Verdi_NOK"],
                                       1_000.0 * serie[-1] / serie[0], places=6)

    def test_manedsavkastningen_er_gjennomsnittet(self):
        """En som stiger 10 %, en flat: samlet måned må bli nøyaktig 5 %."""
        opp = kurve("Opp", [100.0, 110.0, 110.0])
        flat = kurve("Flat", [100.0, 100.0, 100.0])
        res = pb.build_capital_portfolio([opp, flat], as_of=SOM_OF,
                                         start_capital=1_000_000.0)
        self.assertAlmostEqual(res["equity"][1]["Verdi_NOK"], 1_050_000.0, places=6)

    def test_rebalanseringen_stiller_tilbake_til_lik_vekt(self):
        opp = kurve("Opp", [100.0, 110.0, 110.0])
        flat = kurve("Flat", [100.0, 100.0, 100.0])
        res = pb.build_capital_portfolio([opp, flat], as_of=SOM_OF,
                                         start_capital=1_000_000.0)
        # Etter måned 2 er begge stilt tilbake til 50 %; ingen videre drift.
        self.assertAlmostEqual(res["equity"][2]["Verdi_NOK"], 1_050_000.0, places=6)
        for h in res["holdings"]:
            self.assertAlmostEqual(h["Andel_Pst"], 50.0)


class Forbeholdene(unittest.TestCase):
    def test_tre_strategier_sier_det_i_klartekst(self):
        res = pb.build_capital_portfolio(
            [kurve(f"S{n}", FLAT) for n in range(3)], as_of=SOM_OF)
        tekst = " ".join(res["warnings"])
        self.assertIn("split equally between 3 strategies", tekst)
        self.assertIn("33% each", tekst)

    def test_fire_strategier_sier_ikke_noe_om_utelatelse(self):
        res = pb.build_capital_portfolio(
            [kurve(f"S{n}", FLAT) for n in range(4)], as_of=SOM_OF)
        self.assertNotIn("not four", " ".join(res["warnings"]))

    def test_strategiene_navngis_i_resultatet(self):
        res = pb.build_capital_portfolio(
            [kurve("A", FLAT), kurve("B", FLAT), kurve("C", FLAT)], as_of=SOM_OF)
        self.assertEqual(res["strategies"], ["A", "B", "C"])
        self.assertIn("Only these strategies are in the blend: A, B, C",
                      " ".join(res["warnings"]))

    def test_nullkostnad_star_i_forbeholdene(self):
        res = pb.build_capital_portfolio(
            [kurve(f"S{n}", FLAT) for n in range(4)], as_of=SOM_OF)
        tekst = " ".join(res["warnings"]) + res["metrics"]["Cost_Basis"]
        self.assertIn("No trading costs are modelled", tekst)
        self.assertIn("without trading costs", res["metrics"]["Cost_Basis"])


class Dekningen(unittest.TestCase):
    def test_bindende_strategi_navngis(self):
        kort = kurve("Kort", FLAT[:4])
        lang = kurve("Lang", FLAT)
        res = pb.build_capital_portfolio([kort, lang], as_of=SOM_OF)
        self.assertEqual(res["binding_component"], "Kort")
        self.assertIn("Kort", " ".join(res["warnings"]))

    def test_manglende_fellesmaned_avvises_i_stedet_for_a_oppfinnes(self):
        import calendar
        hull = support.curve("Hull", [
            ("2025-01-31", 100.0), ("2025-02-28", 101.0), ("2025-04-30", 102.0)])
        hel = kurve("Hel", FLAT[:4])
        with self.assertRaises(pb.PortfolioDataError) as boks:
            pb.build_capital_portfolio([hull, hel], as_of=SOM_OF)
        self.assertIn("refusing to invent", str(boks.exception))


if __name__ == "__main__":
    unittest.main()
