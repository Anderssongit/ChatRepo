# -*- coding: utf-8 -*-
"""Inngangspunkt for rettelsene 2026-09-20. Ingenting i repoet endres.

    python 2026-09-20/run.py                   full kjøring, sender mail
    python 2026-09-20/run.py --mail-kladd      bygg mailen, ikke send
    python 2026-09-20/run.py --tving-datahent  bygg alle grunnlagsfilene på nytt
    python 2026-09-20/run.py --preflight       hva blokkerer akkurat nå?
    python 2026-09-20/run.py --kostnadstest    ta med kostnadstabellen som opplysning
    python 2026-09-20/run.py --vis-patcher     list patchene, kjør ingenting
    python 2026-09-20/run.py --selvtest        kjør testene i tests/

Alle flagg master.py tar virker her, pluss --ingen-datahent, --tving-datahent og
--kostnadstest som rettelsene legger til.

Patchene påføres modulkilden i minnet ved import, så master.py, Only_260820.py,
portfolio_blend.py, capital_mail.py og insider_selection.py på disk skrives
aldri til. Kjører du master.py direkte får du fortsatt den gamle oppførselen.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import patched_import


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    if "--selvtest" in argv:
        import unittest
        suite = unittest.defaultTestLoader.discover(
            str(HERE / "tests"), top_level_dir=str(HERE / "tests"))
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        return 0 if result.wasSuccessful() else 1

    problems = patched_import.verify()
    if problems:
        print("Rettelsene kan ikke påføres:\n")
        for problem in problems:
            print("  " + problem)
        print("\nIngenting ble kjørt, og ingenting ble endret.")
        return 1

    verbose = "--vis-patcher" in argv
    if verbose:
        argv.remove("--vis-patcher")
        print("Rettelsene 2026-09-20, påført i minnet:")
    patched_import.install(verbose=verbose)
    if verbose and not argv:
        print("\nFilene i rotmappen er urørt.")
        return 0

    # Kostnadstesten er ren opplysning. Den slås på her fordi insider_selection
    # leser miljøet, ikke argparse - og fordi den koster to ekstra fulle
    # backtester per variant.
    if "--kostnadstest" in argv:
        os.environ["AKSJE_KOSTNADSTEST"] = "1"

    if "--preflight" in argv:
        # Vår preflight bruker samme vurdering som datastatusblokken i mailen.
        # Bare flaggene den forstår sendes videre; resten er masterflagg som
        # ikke betyr noe når ingenting skal kjøres.
        import preflight_data
        rest, hent_neste = [], False
        for arg in argv:
            if hent_neste:
                rest.append(arg)
                hent_neste = False
            elif arg in ("--excel-dir", "--mappe"):
                rest.append(arg)
                hent_neste = True
            elif arg == "--json":
                rest.append(arg)
        return preflight_data.main(rest)

    import master
    return master.kjor(argv)


if __name__ == "__main__":
    sys.exit(main())
