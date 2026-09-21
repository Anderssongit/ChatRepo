"""Compatibility entry point: the maintained implementation is in the root."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if "--vis-patcher" in args:
        args.remove("--vis-patcher")
        print("Corrections are integrated in the root source; no import patches are applied.")
        if not args:
            return 0
    import master
    return master.kjor(args)


if __name__ == "__main__":
    raise SystemExit(main())
