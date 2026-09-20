# -*- coding: utf-8 -*-
"""Delvis er ikke mislykket.

Kjøringen 2026-09-20 hentet 3879 artikler. 197 av 294 selskaper manglet minst
én artikkeltekst, så steg 1 meldte DELVIS — og driveren kastet hele
innsidestrategien: steg 2 til 6 kjørte aldri.

Try/except per selskap fantes allerede og virket. Det var porten OVER den som
gjorde den meningsløs: ett ufullstendig selskap av 294 stanset alt.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import support                                                       # noqa: E402

ip = support.load_patched("innsidehandel_pipeline")


class NaarStanserKjoringen(unittest.TestCase):
    def test_delvis_stanser_ikke(self):
        """Det er hele rettelsen: DELVIS lar steg 2-6 kjøre videre."""
        self.assertFalse(ip.steg_er_fatalt("DELVIS"))

    def test_hoppet_stanser_ikke(self):
        self.assertFalse(ip.steg_er_fatalt("HOPPET"))

    def test_ok_stanser_ikke(self):
        self.assertFalse(ip.steg_er_fatalt("OK"))

    def test_feil_stanser(self):
        """FEIL betyr at ingenting ble hentet. Da er det ingenting å bygge på."""
        self.assertTrue(ip.steg_er_fatalt("FEIL"))

    def test_avbrutt_stanser(self):
        self.assertTrue(ip.steg_er_fatalt("AVBRUTT"))

    def test_ukjent_status_stanser_ikke(self):
        self.assertFalse(ip.steg_er_fatalt("NOE_HELT_ANNET"))
        self.assertFalse(ip.steg_er_fatalt(None))


class StatusForNedlastingen(unittest.TestCase):
    def test_feilfritt_skrap_er_ok(self):
        self.assertEqual(ip.steg1_status(0, 3879), "OK")

    def test_den_faktiske_kjoringen_blir_delvis(self):
        """197 feilede selskaper, 3879 artikler på disk — delvis, ikke fatalt."""
        status = ip.steg1_status(197, 3879)
        self.assertEqual(status, "DELVIS")
        self.assertFalse(ip.steg_er_fatalt(status))

    def test_ett_eneste_feilet_selskap_stanser_ikke_lenger_alt(self):
        """Før: ett av 294 ga DELVIS, og DELVIS stanset steg 2-6."""
        status = ip.steg1_status(1, 3879)
        self.assertEqual(status, "DELVIS")
        self.assertFalse(ip.steg_er_fatalt(status))

    def test_ingenting_pa_disk_er_fatalt(self):
        status = ip.steg1_status(294, 0)
        self.assertEqual(status, "FEIL")
        self.assertTrue(ip.steg_er_fatalt(status))

    def test_null_feil_og_null_artikler_er_fortsatt_ok(self):
        """Ingen nye meldinger i perioden er et gyldig utfall, ikke en feil."""
        self.assertEqual(ip.steg1_status(0, 0), "OK")


class Kilden(unittest.TestCase):
    def setUp(self):
        self.kilde = support.patched_source("innsidehandel_pipeline")

    def test_den_gamle_porten_er_borte(self):
        self.assertNotIn('or (n in (1, 4, 5) and resultater[plass[n]].status != "OK")',
                         self.kilde)

    def test_den_gamle_statusregelen_er_borte(self):
        self.assertNotIn('status = "OK" if feil == 0 else "DELVIS"', self.kilde)

    def test_driveren_bruker_den_nye_regelen(self):
        self.assertIn("_fatalt = steg_er_fatalt(_status)", self.kilde)
        self.assertIn("args.stopp_ved_feil and _fatalt", self.kilde)

    def test_villedende_feilmelding_er_rettet(self):
        """Loggen skyldte på --stopp-ved-feil, som ikke var det som utløste stoppen."""
        self.assertNotIn("--stopp-ved-feil: stanser etter steg", self.kilde)
        self.assertIn("Stanser etter steg {n}: status {_status}", self.kilde)

    def test_delvis_steg_gir_en_synlig_advarsel(self):
        self.assertIn("resultatet bygger på ufullstendige data", self.kilde)

    def test_hjelperne_er_definert_for_de_brukes_ved_kjoretid(self):
        self.assertIn("def steg_er_fatalt", self.kilde)
        self.assertIn("def steg1_status", self.kilde)


class MasterSierFraOmDelvis(unittest.TestCase):
    def test_delvis_innsidekjoring_forklares_pa_norsk(self):
        kilde = support.patched_source("master")
        self.assertIn("Delvis: minst ett steg i innsidepipelinen", kilde)
        self.assertNotIn("Parsing partly classified", kilde)

    def test_delvis_utelukker_ikke_innsidestrategien_fra_blandingen(self):
        """Status blir fortsatt OK, så strategien teller med — den er bare merket."""
        kilde = support.patched_source("master")
        i = kilde.index("Delvis: minst ett steg i innsidepipelinen")
        self.assertIn('status, feil = "OK", (', kilde[max(0, i - 200):i])


if __name__ == "__main__":
    unittest.main()
