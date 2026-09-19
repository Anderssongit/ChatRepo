# -*- coding: utf-8 -*-
"""The import hook must patch correctly and never touch a file on disk."""
import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import patched_import as pi

ROOT = pi.ROOT
TARGETS = ("master.py", "Only_260820.py", "portfolio_blend.py")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class PatchesStillMatch(unittest.TestCase):
    def test_every_block_matches_the_untouched_root_files(self):
        self.assertEqual(pi.verify(), [])

    def test_all_three_files_are_covered(self):
        self.assertEqual(sorted(pi.load_patches()), 
                         ["Only_260820", "master", "portfolio_blend"])


class NeverWritesToDisk(unittest.TestCase):
    def test_importing_patched_modules_leaves_the_files_byte_identical(self):
        before = {name: digest(ROOT / name) for name in TARGETS}
        pi.install()
        import master, portfolio_blend           # noqa: F401
        after = {name: digest(ROOT / name) for name in TARGETS}
        self.assertEqual(before, after)

    def test_no_bytecode_is_cached_for_a_patched_module(self):
        pi.install()
        import portfolio_blend
        cache = ROOT / "__pycache__"
        if cache.is_dir():
            names = [p.name for p in cache.glob("portfolio_blend.*.pyc")]
            self.assertEqual(names, [], "a .pyc of patched source would be "
                                        "served to a later unpatched import")


class MarkerHandling(unittest.TestCase):
    """One patch's replacement may contain another patch's marker."""

    def setUp(self):
        self.source = pi._read(ROOT / "master.py")
        self.patches = pi.load_patches()["master"]

    def test_all_master_patches_apply_to_the_original(self):
        patched = pi.patch_source(self.source, self.patches, "master.py")
        for patch in self.patches:
            self.assertIn(patch["marker"], patched, patch["name"])

    def test_the_flag_patch_is_not_swallowed_by_an_earlier_helper_text(self):
        # foreldede_grunnlagsdata mentions --ingen-datahent in a message, so a
        # marker test against the accumulating text skips the argparse patch.
        patched = pi.patch_source(self.source, self.patches, "master.py")
        self.assertIn('p.add_argument("--ingen-datahent"', patched)
        self.assertIn('p.add_argument("--tving-datahent"', patched)

    def test_patching_is_idempotent(self):
        once = pi.patch_source(self.source, self.patches, "master.py")
        twice = pi.patch_source(once, self.patches, "master.py")
        self.assertEqual(once, twice)


class FailsLoudly(unittest.TestCase):
    def test_a_changed_file_raises_rather_than_half_patching(self):
        patches = [{"name": "x", "marker": "@@never@@",
                    "original": ["this line is not in any file"],
                    "replacement": ["nor is this"]}]
        with self.assertRaises(pi.PatchError) as caught:
            pi.patch_source("some unrelated source", patches, "fake.py")
        self.assertIn("refusing to run a half-patched module", str(caught.exception))


class LineNumbersAreHonest(unittest.TestCase):
    def test_inspect_shows_the_source_that_actually_runs(self):
        pi.install()
        import inspect
        import portfolio_blend
        source = inspect.getsource(portfolio_blend.build_capital_portfolio)
        self.assertIn("binding_component", source)


if __name__ == "__main__":
    unittest.main()
