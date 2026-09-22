# -*- coding: utf-8 -*-
"""Patchene treffer, de treffer RIKTIG sted, og rotfilene er urørt."""
from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import support                                                       # noqa: E402
import build_patches as bp                                           # noqa: E402
import patched_import as pi                                          # noqa: E402

FILER = ("master", "capital_mail", "portfolio_blend", "insider_selection",
         "Only_260820")


class Patchene(unittest.TestCase):
    def test_alle_patcher_treffer_urorte_rotfiler(self):
        self.assertEqual(pi.verify(), [])

    def test_hver_blokk_finnes_noyaktig_en_gang(self):
        for stem, patches in pi.load_patches().items():
            raw = bp.read(stem + ".py")
            for patch in patches:
                with self.subTest(patch=patch["name"]):
                    self.assertEqual(raw.count(patch["original_text"]), 1)

    def test_patchet_kilde_parser(self):
        for stem in FILER:
            with self.subTest(fil=stem):
                ast.parse(support.patched_source(stem))

    def test_ankerlinjene_stemmer_fortsatt(self):
        """Frosne ankerlinjer — fanger en blokk som treffer feil sted."""
        anchors = json.loads((support.PAKKE / "anchors.json").read_text(encoding="utf-8"))
        self.assertEqual(len(anchors), len(bp.EDITS))
        cache = {}
        for file, name, _marker, first, _last, _repl in bp.EDITS:
            raw = cache.setdefault(file, bp.read(file))
            faktisk = bp.lines_of(raw)[first - 1].rstrip("\r").strip()
            with self.subTest(patch=name):
                self.assertEqual(anchors[name], faktisk)

    def test_patch_er_idempotent(self):
        for stem in FILER:
            patches = pi.load_patches().get(stem, [])
            once = support.patched_source(stem)
            twice = pi.patch_source(once, patches, stem + ".py")
            with self.subTest(fil=stem):
                self.assertEqual(once, twice)

    def test_markorene_star_ikke_i_rotfilene(self):
        for stem, patches in pi.load_patches().items():
            raw = bp.read(stem + ".py")
            for patch in patches:
                with self.subTest(patch=patch["name"]):
                    self.assertNotIn(patch["marker"], raw)
                    self.assertIn(patch["marker"], patch["replacement_text"])

    def test_bygging_gir_samme_patches_json(self):
        """patches.json er faktisk det build_patches.py lager av dagens rotfiler."""
        patches, problems = bp.build()
        self.assertEqual(problems, [])
        lagret = json.loads((support.PAKKE / "patches.json").read_text(encoding="utf-8"))
        self.assertEqual(patches, lagret)


class BeskyttedeStrategier(unittest.TestCase):
    """PBROE_All3 og SentimentMomentumV31 skal være byte-identiske etter patch."""

    def _funksjonskropp(self, kilde: str, navn: str) -> str:
        tre = ast.parse(kilde)
        for node in tre.body:
            if isinstance(node, ast.FunctionDef) and node.name == navn:
                return ast.dump(node, include_attributes=False)
        self.fail(f"Fant ikke {navn}")

    def test_hashene_er_uendret(self):
        forventet = json.loads(
            (support.ROT / "protected_strategy_hashes.json").read_text(encoding="utf-8"))
        original = bp.read("Only_260820.py")
        patchet = support.patched_source("Only_260820")
        for navn in forventet:
            with self.subTest(funksjon=navn):
                self.assertEqual(self._funksjonskropp(original, navn),
                                 self._funksjonskropp(patchet, navn))

    def test_prisvakten_patches_ikke_lenger(self):
        """Prisvakten er rettet i rotfila; en patch ville satt tilbake den strengere regelen."""
        self.assertNotIn("Only_260820", pi.load_patches())
        self.assertIn("def rett_og_utelat_priser", bp.read("Only_260820.py"))


class RotfileneErUrorte(unittest.TestCase):
    def test_ingen_rotfil_endres_av_a_bygge_og_patche(self):
        før = {f: hashlib.sha256(bp.read(f + ".py").encode("utf-8")).hexdigest()
               for f in FILER}
        for stem in FILER:
            support.patched_source(stem)
        bp.build()
        etter = {f: hashlib.sha256(bp.read(f + ".py").encode("utf-8")).hexdigest()
                 for f in FILER}
        self.assertEqual(før, etter)

    def test_pakken_refererer_til_sin_egen_mappe(self):
        """Patchene må peke på DENNE mappen, ikke en tidligere datert utgave."""
        navn = support.PAKKE.name
        for stem in ("master", "insider_selection", "Only_260820"):
            kilde = support.patched_source(stem)
            for treff in re.findall(r'/ "(\d{4}-\d{2}-\d{2})"', kilde):
                with self.subTest(fil=stem):
                    self.assertEqual(treff, navn)


if __name__ == "__main__":
    unittest.main()
