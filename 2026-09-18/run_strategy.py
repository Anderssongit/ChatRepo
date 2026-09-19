"""Explicit standalone entry point; importing models never starts a run."""
from __future__ import annotations
import argparse
import importlib.util
import os
from pathlib import Path
from runtime_config import data_root, configure_paths, protected_input_errors


def preflight(base):
    required = ["numpy", "pandas", "openpyxl", "xlsxwriter", "matplotlib",
                "yfinance", "playwright", "requests", "bs4", "torch",
                "transformers", "nltk", "langdetect", "pdfplumber"]
    missing = [p for p in required if importlib.util.find_spec(p) is None]
    inputs = protected_input_errors(base)
    print("ExcelData:", base)
    if missing:
        print("Missing Python packages:", ", ".join(missing))
        print("Run SETUP.cmd with your Python 3.12 installation.")
    if inputs:
        print("Required existing upstream files:")
        for item in inputs:
            print(" -", item)
    print("Mail: existing code settings are retained; place mail_passord.txt beside master.py.")
    return 2 if missing or inputs else 0


def main(argv=None):
    from runtime_config import configure_console
    configure_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strategy", choices=["all", "pbroe", "sentmom", "management", "insider"], default="all")
    parser.add_argument("--excel-dir")
    parser.add_argument("--mappe")
    parser.add_argument("--mail-kladd", action="store_true")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--ingen-nlp-hent", action="store_true")
    a, rest = parser.parse_known_args(argv)
    base = data_root(a.excel_dir)
    os.environ["AKSJE_BASE_DIR"] = str(base)
    if a.preflight:
        return preflight(base)
    if a.strategy == "all":
        import master
        args = ["--excel-dir", str(base)] + rest
        if a.mappe: args += ["--mappe", a.mappe]
        if a.mail_kladd: args += ["--mail-kladd"]
        if a.ingen_nlp_hent: args += ["--ingen-nlp-hent"]
        return master.kjor(args)
    if a.strategy == "insider":
        import innsidehandel_pipeline as ip
        args = ["--steg", "1-6", "--stopp-ved-feil"] + rest
        if a.mappe: args += ["--mappe", a.mappe]
        if a.mail_kladd: args += ["--mail-kladd"]
        return ip.main(args)
    import Only_260820 as models
    configure_paths(models.__dict__, base)
    if a.strategy == "management":
        if not a.ingen_nlp_hent:
            os.environ["AKSJE_NLP_HENT"] = "1"
            os.environ["AKSJE_NLP_ONLY_DOWNLOAD"] = "1"
            models.SentimentManagement()
        models.SentimentHendelseLab()
    else:
        {"pbroe": models.PBROE_All3, "sentmom": models.SentimentMomentumV31}[a.strategy]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
