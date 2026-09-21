"""Safe management-definition fixtures: no model execution, downloads, or mail."""
from __future__ import annotations
import ast
import logging
import os
import textwrap
from dataclasses import asdict, dataclass
from datetime import datetime
from math import exp, sqrt
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
KILDE = Path(__file__).resolve().parent / "Only_260820.py"

def _hent():
    """
    Alt laben definerer FØR hovedløpet, kjørt i et eget navnerom.

    Grensen er hovedløpet: der slutter definisjonene og der begynner kjøringen,
    som ville lastet ned kurser fra Yahoo.
    """
    src = KILDE.read_text(encoding="utf-8")
    linjer = src.splitlines()
    lab = [n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef)
           and n.name == "SentimentHendelseLab"][0]
    hovedlop = min(n.lineno for n in lab.body
                   if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
                   and "SENTIMENT HENDELSE LAB" in ast.dump(n.value))
    biter = []
    for n in lab.body:
        if n.lineno >= hovedlop:
            break
        # For og AugAssign må med: EXIT_STRATEGIER bygges av en løkke og
        # utvides med «+=», og uten dem blir listen tom i testnavnerommet.
        if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AnnAssign,
                          ast.Assign, ast.For, ast.AugAssign)):
            start = min([n.lineno]
                        + [d.lineno for d in getattr(n, "decorator_list", [])])
            biter.append(textwrap.dedent(
                "\n".join(linjer[start - 1:n.end_lineno])))
    ns = {"np": np, "pd": pd, "dataclass": dataclass, "asdict": asdict,
          "Path": Path, "os": os, "exp": exp, "sqrt": sqrt, "logging": logging,
          "datetime": datetime,
          "Tuple": Tuple, "List": List, "Dict": Dict, "Optional": Optional,
          "log": logging.getLogger("test_hendelse")}
    exec(compile("\n\n".join(biter), "<hendelse>", "exec"), ns)
    return ns

def _md_av(ns, close):
    hoy, lav = close * 1.01, close * 0.99
    forrige = close.shift(1)
    tr = pd.concat([(hoy - lav).abs(), (hoy - forrige).abs(),
                    (lav - forrige).abs()]).groupby(level=0).max()
    atr = tr.rolling(20, min_periods=5).mean()
    daglig = close.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan)
    return ns["MarkedsData"](close, hoy, lav, atr,
                             close.rolling(10).mean(),
                             close.rolling(50).mean(),
                             close.ewm(span=20, adjust=False, min_periods=20).mean(),
                             (1.0 + daglig.mean(axis=1).fillna(0.0)).cumprod())
