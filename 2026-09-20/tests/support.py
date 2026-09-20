# -*- coding: utf-8 -*-
"""Felles oppsett: gjør de patchede modulene kjørbare uten pandas og uten nett.

Patchene er ren tekst, så en patchet modul kan bygges og kjøres i minnet her.
Det er hele poenget med testene: de kjører koden som faktisk kjører i produksjon,
ikke en avskrift av den.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

TESTS = Path(__file__).resolve().parent
PAKKE = TESTS.parent
ROT = PAKKE.parent

for _sti in (str(PAKKE), str(ROT)):
    if _sti not in sys.path:
        sys.path.insert(0, _sti)

import build_patches as bp                                          # noqa: E402
import patched_import as pi                                         # noqa: E402


def patched_source(stem: str) -> str:
    """Kildekoden til én rotmodul med alle patchene påført, som tekst."""
    return pi.patch_source(bp.read(stem + ".py"), pi.load_patches()[stem],
                           stem + ".py")


def load_patched(stem: str) -> types.ModuleType:
    """Kjør den patchede kilden som en frittstående modul.

    __file__ peker på den ekte rotfila, slik at oppslag som
    Path(__file__).parent / "2026-09-20" finner pakken.
    """
    navn = "patched_" + stem
    module = types.ModuleType(navn)
    module.__file__ = str(ROT / (stem + ".py"))
    # @dataclass slaar opp sys.modules[cls.__module__] under dekorering, saa
    # modulen maa vaere registrert FOER kroppen kjoeres.
    sys.modules[navn] = module
    try:
        exec(compile(patched_source(stem), module.__file__, "exec"), module.__dict__)
    except BaseException:
        sys.modules.pop(navn, None)
        raise
    return module


def curve(name, points, **extra):
    """En komponent slik portfolio_blend.load_production_curves leverer den."""
    return dict({"name": name, "observations": list(points), "valid": True,
                 "errors": [], "frequency": "daily",
                 "source": {"path": f"/tmp/{name}.xlsx", "sheet": None,
                            "mtime_ns": 1, "size": 1}}, **extra)


def month_ends(year, month, count, start=100.0, step=1.0):
    """[(dato, verdi)] på fullførte månedsslutter, som en NAV-eksport."""
    import calendar
    out, value = [], start
    for n in range(count):
        y, m = divmod((month - 1) + n, 12)
        y, m = year + y, m + 1
        out.append((f"{y:04d}-{m:02d}-{calendar.monthrange(y, m)[1]:02d}", value))
        value *= step if step != 1.0 else 1.0
        if step == 1.0:
            value += 1.0
    return out
