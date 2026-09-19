# -*- coding: utf-8 -*-
"""Entry point for the 2026-09-18 corrections. Nothing in the repo is modified.

    python 2026-09-18/run.py                  # full run, sends the mail
    python 2026-09-18/run.py --mail-kladd     # build the mail, do not send
    python 2026-09-18/run.py --tving-datahent # rebuild all three input files
    python 2026-09-18/run.py --preflight      # what is blocking right now?
    python 2026-09-18/run.py --vis-patcher    # list the patches, run nothing

Every flag master.py accepts works here, plus --ingen-datahent and
--tving-datahent which the corrections add.

The patches are applied to the module source in memory at import time, so
master.py, Only_260820.py and portfolio_blend.py on disk are never written to.
Running master.py directly still gives the original, unpatched behaviour.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import patched_import


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    problems = patched_import.verify()
    if problems:
        print("The corrections cannot be applied:\n")
        for problem in problems:
            print("  " + problem)
        print("\nNothing was run and nothing was changed.")
        return 1

    verbose = "--vis-patcher" in argv
    if verbose:
        argv.remove("--vis-patcher")
        print("2026-09-18 corrections, applied in memory:")
    patched_import.install(verbose=verbose)
    if verbose and not argv:
        print("\nThe files in the repository root are untouched.")
        return 0

    if "--preflight" in argv and len(argv) == 1:
        import preflight_data
        return preflight_data.main([])

    import master
    return master.kjor(argv)


if __name__ == "__main__":
    sys.exit(main())
