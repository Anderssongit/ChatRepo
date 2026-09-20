# -*- coding: utf-8 -*-
"""Apply the 2026-09-20 patches at import time, leaving the files on disk alone.

WHY
---
The fixes change three files that were already in the repository:

    master.py           builds the upstream workbooks instead of only checking
    Only_260820.py      the management price guard repairs unit artifacts
    portfolio_blend.py  reports which strategy caps the joint window

Nothing in this folder may modify them. So instead of editing the files, this
installs an import hook: when one of those modules is imported, its source is
read from the repository root, the patches in patches.json are applied to the
TEXT IN MEMORY, and the result is compiled and executed as the module.

The file on disk is never opened for writing and never changes. Run anything
through run.py and you get the corrected behaviour; run master.py directly and
you get exactly what was there before.

Two properties this buys over copying the files into this folder:

  * no duplication - Only_260820.py is 628 KB to change 30 lines;
  * no drift - the patch is applied to whatever the root file currently says,
    so a later edit there is picked up, or the patch fails loudly because its
    block no longer matches. A stale copy would silently ignore both.

No .pyc is written for a patched module. A cached bytecode file keyed to the
original source would otherwise be served to a plain, unpatched import later.
"""
from __future__ import annotations

import importlib
import importlib.abc
import importlib.util
import json
import linecache
import sys
from pathlib import Path
from typing import Dict, List, Optional

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PATCHES = HERE / "patches.json"


class PatchError(RuntimeError):
    """A patch block no longer matches the file it was written against."""


def _read(path: Path) -> str:
    with path.open(encoding="utf-8", newline="") as handle:
        return handle.read()


def _needle(patch: dict) -> str:
    """Den eksakte teksten patchen erstatter.

    Blokken er hentet byte for byte ut av rotfila da patchen ble bygget, saa
    den baerer filas egne linjeskift. Det er noedvendig: Only_260820.py blander
    12373 CRLF-linjer med 151 rene LF, og insider_selection.py 269 mot 37. Aa
    sette blokken sammen igjen med EN konvensjon ville ikke ha truffet.
    """
    needle = patch.get("original_text")
    if needle is None:
        raise PatchError(
            f"{patch.get('name', 'ukjent patch')}: mangler original_text. "
            "patches.json er fra et eldre format; bygg den paa nytt med "
            "build_patches.py.")
    return needle


def load_patches() -> Dict[str, List[dict]]:
    grouped: Dict[str, List[dict]] = {}
    for patch in json.loads(PATCHES.read_text(encoding="utf-8")):
        grouped.setdefault(Path(patch["file"]).stem, []).append(patch)
    return grouped


def patch_source(text: str, patches: List[dict], filename: str) -> str:
    """Apply every patch, or raise. A partially patched module is never run.

    "Already applied" is decided against the ORIGINAL text, once, before
    anything is replaced. Testing the accumulating text instead lets one
    patch's replacement contain another's marker - the helper functions
    mention --ingen-datahent in a message - and the second patch is then
    silently skipped, so the flag it adds never exists.
    """
    present = {patch["name"] for patch in patches if patch["marker"] in text}
    for patch in patches:
        if patch["name"] in present:
            continue                      # already present on disk
        needle = _needle(patch)
        found = text.count(needle)
        if found != 1:
            where = "" if not patch.get("lines") else (
                f" (line {patch['lines'][0]}-{patch['lines'][1]} when the patch "
                "was built)")
            raise PatchError(
                f"{filename}: the block for '{patch['name']}' was found {found} "
                f"times{where}, expected exactly once. The file differs from the "
                "version this patch was written against; refusing to run a "
                "half-patched module.")
        text = text.replace(needle, patch["replacement_text"], 1)
    return text


class _Loader(importlib.abc.Loader):
    def __init__(self, fullname: str, origin: Path, patches: List[dict]):
        self.fullname, self.origin, self.patches = fullname, origin, patches

    def create_module(self, spec):
        return None                        # default module creation

    def exec_module(self, module):
        source = patch_source(_read(self.origin), self.patches, self.origin.name)
        # compile() with the real path keeps tracebacks, __file__ and any
        # Path(__file__).parent lookups pointing at the repository root.
        code = compile(source, str(self.origin), "exec")
        # Without this, a traceback or inspect.getsource() would read the
        # UNPATCHED file from disk and show lines that are not the ones running.
        # Seeding linecache makes the executed source the one you are shown.
        linecache.cache[str(self.origin)] = (
            len(source), None, source.splitlines(True), str(self.origin))
        module.__file__ = str(self.origin)
        exec(code, module.__dict__)


class PatchedFinder(importlib.abc.MetaPathFinder):
    def __init__(self, patches: Dict[str, List[dict]], root: Path):
        self.patches, self.root = patches, root

    def find_spec(self, fullname, path=None, target=None):
        if fullname not in self.patches:
            return None
        origin = self.root / (fullname + ".py")
        if not origin.is_file():
            return None
        return importlib.util.spec_from_loader(
            fullname, _Loader(fullname, origin, self.patches[fullname]),
            origin=str(origin), is_package=False)


_installed: Optional[PatchedFinder] = None


def install(*, verbose: bool = False) -> PatchedFinder:
    """Put the hook in front of the normal import machinery. Idempotent."""
    global _installed
    if _installed is not None:
        return _installed
    patches = load_patches()
    already = [name for name in patches if name in sys.modules]
    if already:
        # An unpatched copy is already live; replacing it would leave two
        # versions of the same module in one process.
        raise PatchError(
            "Import these before anything else: " + ", ".join(sorted(already))
            + " was already imported unpatched. Call install() first, or start "
              "from run.py.")
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))      # so data_acquisition et al. resolve
    if str(ROOT) not in sys.path:
        sys.path.append(str(ROOT))
    _installed = PatchedFinder(patches, ROOT)
    sys.meta_path.insert(0, _installed)
    if verbose:
        for name, items in sorted(patches.items()):
            print(f"  patched on import: {name} ({len(items)} block(s))")
    return _installed


def uninstall() -> None:
    global _installed
    if _installed is not None:
        sys.meta_path.remove(_installed)
        for name in _installed.patches:
            sys.modules.pop(name, None)
            linecache.cache.pop(str(_installed.root / (name + ".py")), None)
        _installed = None


def verify() -> List[str]:
    """Check every patch still matches, without importing anything."""
    problems = []
    for name, patches in sorted(load_patches().items()):
        origin = ROOT / (name + ".py")
        if not origin.is_file():
            problems.append(f"{origin.name}: not found in {ROOT}")
            continue
        try:
            patch_source(_read(origin), patches, origin.name)
        except PatchError as exc:
            problems.append(str(exc))
    return problems
