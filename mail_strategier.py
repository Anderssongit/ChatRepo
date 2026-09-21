# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  TENTATIVE RESULTATER PÅ MAIL — ALLE TRE STRATEGIER                          ║
║                                                                              ║
║  Én mail som samler siste kjøring av alle tre strategiene i Only_260820.py:   ║
║                                                                              ║
║    1. PB-ROE-Momentum         PBROE_All3()  →  DETAILED_BACKTEST_v3()         ║
║       DataPB_ROE/Backtest/BT_v3_Enhanced_<dato>.xlsx                         ║
║       Ark: Metrics · Parameters · Equity_Curve · Monthly_Holdings ·           ║
║            Trade_Log · Stop_Loss_Log                                         ║
║                                                                              ║
║    2. NLP Sentiment (ledelse) SentimentManagement() → NlpSentimentTrader4()   ║
║       StrategyResults_v4_Sentiment/Sentiment_v4*_SMA<n>_<dato>.xlsx           ║
║       Ark: Equity_Curve · Monthly_Holdings · Trade_Log                        ║
║                                                                              ║
║    3. Sentiment Momentum v3.1 SentimentMomentumV31()                          ║
║       DataNLP/BacktestResults/S5_SentMom31_{Portfolio,Trades,Signals,         ║
║       Funnel}_<tidsstempel>.xlsx                                             ║
║                                                                              ║
║  HVA MAILEN INNEHOLDER                                                        ║
║    • Sammenligning av alle tre, med harmonisert Sharpe (se under)            ║
║    • Per strategi: nøkkeltall, beholdning, siste handler                     ║
║    • Signalfunnel for SentMom31 — den eneste som logger den                  ║
║    • Overlapp: aksjer som går igjen i flere strategier                       ║
║    • Datagrunnlag med filnavn og alder på hver eneste kilde                  ║
║                                                                              ║
║  HVORFOR TO SHARPE-TALL                                                       ║
║    De tre strategiene regner Sharpe ULIKT i sin egen kode:                    ║
║      PB-ROE og NLP-ledelse:  (CAGR − 3 %) / årlig vol,  månedlig kurve       ║
║      SentMom31:              (snitt·252 − 4 %) / (std·√252),  daglig kurve   ║
║    «Rapportert» er strategiens eget tall, så mailen aldri motsier konsollen.  ║
║    «Harmonisert» er alle tre regnet likt: månedlig kurve, (CAGR − 3 %) / vol. ║
║    Bare den harmoniserte kolonnen kan sammenlignes på tvers.                  ║
║                                                                              ║
║  OPPSETT — ingenting. Avsender, app-passord og mottakere står i               ║
║  INNSTILLINGER nedenfor, og koden virker rett ut av boksen.                   ║
║                                                                              ║
║  Kjør:  MailAlleStrategier()                      bygg og send                ║
║         MailAlleStrategier(send=False)            bygg kladd uten å sende     ║
║         MailAlleStrategier(open_in_browser=True)  åpne kopien lokalt          ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""



import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))

def MailAlleStrategier(send=False, open_in_browser=False, base_dir=None,
                       returner_html=False):
    """
    Bygger strategisammendraget for alle tre strategiene.

    SENDER IKKE AV SEG SELV. Det gjorde den før, og da gikk det to mailer ut
    per kjøring — én herfra og én fra master.py — med hver sitt passord og hver
    sin sannhet om de samme tallene. Nå er master.py eneste avsender: den
    henter denne seksjonen med returner_html=True og limer den inn i sin egen
    mail. Vil du likevel sende denne alene, be om det: send=True, eller
    --send på kommandolinjen.

    Alt funksjonen trenger ligger inni den — importer, innstillinger, lesere og
    HTML. Den kan derfor limes rett inn i Only_260818.py ved siden av
    FullMailScript7(), uten import og uten egen fil.

    Strategier som ikke har kjørt hoppes ikke over i stillhet — de får sitt eget
    kort som sier hvilken fil som mangler og hvilken funksjon som lager den.

    Returnerer stien til HTML-kopien — eller, med returner_html=True, en dict
    med {"sti", "seksjoner", "stil", "emne", "n_aktive", "n_posisjoner"} som
    master.py bygger sin egen mail av. None hvis ingen av de tre har kjørt.
    """

    import os
    import re
    import smtplib
    import webbrowser
    from collections import defaultdict
    from datetime import datetime
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from pathlib import Path
    from typing import Dict, List, Optional, Tuple

    import numpy as np
    import pandas as pd

    # ══════════════════════════════════════════════════════════════════════════
    # INNSTILLINGER
    # ══════════════════════════════════════════════════════════════════════════
    from runtime_config import data_root
    STANDARD_BASE = str(data_root())

    def finn_base_dir():
        """
        Finner ExcelData-mappen i stedet for å anta at én sti stemmer.

        Rekkefølge: eksplisitt argument, miljøvariabel, standardstien, og til
        slutt et søk oppover fra både arbeidsmappen og filen dette kjøres fra.
        Det siste gjør at koden virker enten den kjøres fra MainProcessCode,
        fra PythonKode eller limt inn i en fil et helt tredje sted.
        """
        if base_dir:
            return Path(base_dir), [Path(base_dir)]
        kandidater = []
        if base_dir:
            kandidater.append(Path(base_dir))
        if os.environ.get("AKSJE_BASE_DIR"):
            kandidater.append(Path(os.environ["AKSJE_BASE_DIR"]))
        kandidater.append(Path(STANDARD_BASE))

        start = [Path.cwd()]
        try:
            start.append(Path(__file__).resolve().parent)
        except NameError:
            pass                      # limt inn i et interaktivt miljø
        for s0 in start:
            for opp in [s0] + list(s0.parents)[:5]:
                kandidater.append(opp / "ExcelData")
                kandidater.append(opp / "Python_K4" / "ExcelData")

        sett, unike = set(), []
        for k in kandidater:
            n = str(k)
            if n not in sett:
                sett.add(n)
                unike.append(k)

        # En mappe teller bare som treff hvis den faktisk har innhold vi bruker.
        ventet = ("DataPB_ROE", "DataNLP", "StrategyResults_v4_Sentiment", "Data_BT1")
        for k in unike:
            try:
                if k.is_dir() and any((k / u).is_dir() for u in ventet):
                    return k, unike
            except OSError:
                continue
        for k in unike:                # nest best: mappen finnes, men er tom
            try:
                if k.is_dir():
                    return k, unike
            except OSError:
                continue
        return None, unike

    BASE_DIR, PROVDE_STIER = finn_base_dir()
    if BASE_DIR is None:
        print("\n  Fant ikke ExcelData-mappen. Prøvde:")
        for k in PROVDE_STIER[:12]:
            print(f"    {k}")
        print("\n  Sett riktig sti med enten")
        print("    MailAlleStrategier(base_dir=r'C:/.../ExcelData')")
        print("    eller miljøvariabelen AKSJE_BASE_DIR,")
        print(f"    eller rett STANDARD_BASE i koden (nå: {STANDARD_BASE}).\n")
        return None

    PBROE_BT_DIR     = BASE_DIR / "DataPB_ROE" / "Backtest"
    PBROE_SCORED_DIR = BASE_DIR / "DataPB_ROE" / "MergedData"
    MGMT_DIR         = BASE_DIR / "StrategyResults_v4_Sentiment"
    SENTMOM_DIR      = BASE_DIR / "DataNLP" / "BacktestResults"
    SENTIMENT_DIR    = BASE_DIR / "DataNLP"
    PRICE_DIR        = BASE_DIR / "Data_BT1" / "FinancialData"
    HTML_KOPI_DIR    = SENTMOM_DIR / "MailKopi"

    # Må speile Config i SentimentMomentumV31 — den lagrer ikke parameterne sine,
    # så mailen kan ikke lese dem, bare gjenta dem.
    SENTMOM_START_CAPITAL = 1_000_000
    SENTMOM_RISK_FREE     = 0.04
    # PB-ROE og NLP-ledelse bruker begge denne i sin egen kode.
    RF_HARMONISERT        = 0.03

    MIN_HANDLER_FOR_MENING = 20

    # Under så mange år er en annualisert avkastning ikke et anslag, den er en
    # forstørrelse. NLP-strategien leverte 73 % på åtte måneder og fikk «CAGR
    # 146,7 %» i mailen — ved siden av PB-ROEs 25,4 % fra tre år, i samme
    # tabell, med samme skrift. Samme grense som NlpSentimentTrader4_v4 bruker
    # i sin egen logging, så de to ikke kan si hver sin ting om samme fil.
    MIN_AAR_FOR_CAGR = 2.0

    # Hvor mange handler som vises per strategi i detaljdelen.
    ANTALL_HANDLER = 20

    # Gmail app-passord. Verdien sto hardkodet her; nå leses den samme sted som
    # master.py leser sin — miljøvariabelen eller mail_passord.txt. To kopier av
    # et passord er én kopi for mye: den ene blir utdatert uten at noen merker
    # det, og det var nettopp det som skjedde 8. september.
    EMAIL_USER       = os.environ.get("AKSJE_MAIL_USER", "andyxcx@gmail.com")

    def _finn_passord() -> str:
        try:
            import sys as _sys
            _rot = str(Path(__file__).resolve().parent.parent)
            if _rot not in _sys.path:
                _sys.path.insert(0, _rot)
            from innsidehandel_pipeline import finn_mail_passord
            return finn_mail_passord(BASE_DIR)
        except Exception:
            return os.environ.get("AKSJE_MAIL_APP_PASSWORD", "").strip()

    EMAIL_PASSWORD   = _finn_passord()
    EMAIL_RECIPIENTS = [r.strip() for r in
                        os.environ.get("AKSJE_MAIL_TO", EMAIL_USER).split(",")
                        if r.strip()]
    # EMAIL_RECIPIENTS = ["andyxcx@gmail.com", "lynnvictoria08@gmail.com"]

    KONTANTMERKER = {"CASH — no signal", "CASH — September filter",
                     "CASH", "nan", "", "None"}

    # ══════════════════════════════════════════════════════════════════════════
    # FELLES HJELPERE
    # ══════════════════════════════════════════════════════════════════════════
    def nyeste(mappe: Path, monster: str) -> Optional[Path]:
        try:
            treff = [p for p in mappe.glob(monster)
                     if not p.name.startswith("~$") and "BEFORE_FIX" not in p.name]
            return max(treff, key=lambda p: p.stat().st_mtime) if treff else None
        except OSError:
            return None

    def filalder(p: Optional[Path]) -> str:
        if p is None or not p.exists():
            return "mangler"
        m = datetime.fromtimestamp(p.stat().st_mtime)
        alder = datetime.now() - m
        stempel = m.strftime("%Y-%m-%d %H:%M")
        if alder.days == 0:
            t = alder.seconds // 3600
            return f"{stempel} ({t}t siden)" if t else f"{stempel} ({alder.seconds//60} min siden)"
        if alder.days == 1:
            return f"{stempel} (i går)"
        return f"{stempel} ({alder.days} dager siden)"

    def ferskhet(p: Optional[Path]) -> str:
        if p is None or not p.exists():
            return "stale"
        d = (datetime.now() - datetime.fromtimestamp(p.stat().st_mtime)).days
        return "fresh" if d == 0 else ("moderate" if d <= 3 else "stale")

    def norm_ticker(t) -> str:
        if t is None or (isinstance(t, float) and pd.isna(t)):
            return ""
        s = str(t).strip().upper()
        return s[:-3] if s.endswith(".OL") else s

    def tom_metrikk() -> dict:
        return {k: None for k in (
            "start", "slutt", "total", "cagr", "sharpe", "sortino", "calmar",
            "mdd", "vol", "treffrate", "snitt_handel", "median_handel", "beste",
            "verste", "holdedager", "n_handler", "n_lukket", "gebyrer",
            "exit_miks", "benchmark_cagr", "excess", "periode", "n_ar")}

    # ══════════════════════════════════════════════════════════════════════════
    # METRIKK FRA EN EGENKAPITALKURVE
    # ══════════════════════════════════════════════════════════════════════════
    def kurve_metrikk(ec: pd.Series, per_ar: int, rf: float) -> dict:
        """(CAGR − rf) / vol — konvensjonen PB-ROE og NLP-ledelse bruker."""
        ec = ec.dropna()
        start, slutt = float(ec.iloc[0]), float(ec.iloc[-1])
        n_ar = max((ec.index[-1] - ec.index[0]).days / 365.25, 0.01)
        cagr = (slutt / start) ** (1 / n_ar) - 1
        r = ec.pct_change().dropna()
        vol = float(r.std() * np.sqrt(per_ar)) if len(r) and r.std() > 0 else 0.0
        ned = r[r < 0]
        dv = float(ned.std() * np.sqrt(per_ar)) if len(ned) and ned.std() > 0 else 0.0
        cummax = ec.cummax()
        mdd = float(((ec - cummax) / cummax).min())
        return {
            "start": start, "slutt": slutt, "total": (slutt / start - 1) * 100,
            "cagr": cagr * 100,
            # Under to år er CAGR-en en forstørrelse, ikke et anslag. Tallet
            # blir stående — å skjule det gjør bare at noen regner det ut selv —
            # men flagget følger med, og kortet sier hvorfor.
            "cagr_meningsfull": bool(n_ar >= MIN_AAR_FOR_CAGR),
            "sharpe": (cagr - rf) / vol if vol > 0 else 0.0,
            # 0,00 er en verdi. «Ingen nedside å dele på» er en annen ting, og
            # skal ikke se ut som et målt nulltall ved siden av en ekte Sortino.
            "sortino": (cagr - rf) / dv if dv > 0 else None,
            "calmar": cagr / abs(mdd) if mdd else None,
            "mdd": mdd * 100, "vol": vol * 100, "n_ar": n_ar,
            "n_punkter": int(len(ec)),
            "periode": f"{ec.index[0]:%Y-%m-%d} → {ec.index[-1]:%Y-%m-%d}",
        }

    def sharpe_harmonisert(ec: pd.Series) -> Optional[float]:
        """
        Alle tre målt likt: månedlig kurve, (CAGR − 3 %) / årlig vol.
        Daglige kurver resamples ned, så frekvensen ikke lenger påvirker tallet.
        Dette er den ENESTE Sharpen som kan sammenlignes på tvers av de tre.
        """
        m = ec.dropna().resample("ME").last().dropna()
        if len(m) < 4:
            return None
        r = m.pct_change().dropna()
        if not len(r) or r.std() <= 0:
            return None
        n_ar = max((m.index[-1] - m.index[0]).days / 365.25, 0.01)
        cagr = (float(m.iloc[-1]) / float(m.iloc[0])) ** (1 / n_ar) - 1
        return (cagr - RF_HARMONISERT) / float(r.std() * np.sqrt(12))

    # ══════════════════════════════════════════════════════════════════════════
    # HANDELSSTATISTIKK NÅR LOGGEN IKKE HAR PnL
    # ══════════════════════════════════════════════════════════════════════════
    KJOP = {"BUY", "REBAL_BUY", "KJØP", "KJOP"}
    SALG = {"SELL", "REBAL_SELL", "STOP_LOSS", "SALG"}

    def par_avkastning(tr: pd.DataFrame) -> pd.Series:
        """
        Avkastning per salg, målt mot siste forutgående kjøp i samme ticker.

        Tilnærmet for PB-ROE og NLP-ledelse: begge rebalanserer i brøkdeler av
        aksjer, så et «salg» kan være en nedvekting av en posisjon som fortsatt
        står. Tallet er en indikasjon, ikke en realisert P&L. SentMom31 slipper
        denne tilnærmingen — den skriver PnL selv.
        """
        if tr.empty:
            return pd.Series(dtype=float)
        kjop = tr[tr["Handling"].isin(KJOP)]
        salg = tr[tr["Handling"].isin(SALG)]
        ut = []
        for _, s in salg.iterrows():
            tidligere = kjop[(kjop["Ticker"] == s["Ticker"]) &
                             (kjop["Dato"] < s["Dato"])].sort_values("Dato")
            if tidligere.empty:
                continue
            kp = float(tidligere.iloc[-1]["Kurs"])
            if kp > 0 and pd.notna(s["Kurs"]):
                ut.append((float(s["Kurs"]) / kp - 1) * 100)
        return pd.Series(ut, dtype=float)

    def legg_til_handelsstat(n: dict, avk: pd.Series, n_handler: int,
                             bare_manglende: bool = False) -> None:
        """
        bare_manglende=True fyller kun hull. PB-ROE har et Metrics-ark skrevet av
        backtesten selv; de tallene er fasit og skal ikke overskrives av
        rekonstruksjonen her, som bare er en tilnærming.
        """
        if n["n_handler"] is None or not bare_manglende:
            n["n_handler"] = n_handler
        n["n_lukket"] = int(len(avk))
        if not len(avk):
            return
        for nokkel, verdi in (("treffrate", float((avk > 0).mean()) * 100),
                              ("snitt_handel", float(avk.mean())),
                              ("median_handel", float(avk.median())),
                              ("beste", float(avk.max())),
                              ("verste", float(avk.min()))):
            if n[nokkel] is None or not bare_manglende:
                n[nokkel] = verdi

    # ══════════════════════════════════════════════════════════════════════════
    # LESER 1 — PB-ROE-MOMENTUM
    # ══════════════════════════════════════════════════════════════════════════
    def les_pbroe() -> dict:
        s = {"navn": "PB-ROE-Momentum",
             "beskrivelse": "OSEBX-fundamentaler: lav P/B, høy ROE, momentum, "
                            "Growth-filter og inv-vol-vekting. Månedlig rebalansering.",
             "hvordan": [
                 ("Kjøpsutvalg", "Månedsslutt: inntil 5 aksjer, maks 3 fra samme bransje. "
                  "Krever positiv P/B ≤ 10, ROE ≥ 0 og ikke-negativt 12–1-momentum; "
                  "minst 60 kursobservasjoner. Euronext Growth utelukkes når eksklusjonslisten finnes; "
                  "dette er et markedsplassfilter, ikke et inntjeningsvekstfilter."),
                 ("Rangering", "Persentilscore: 25 % lav P/B + 25 % høy ROE + 20 % 12–1-momentum "
                  "+ 10 % 52-ukersmomentum + 12 % ROE-trend over 4 kvartaler + 8 % ROE-stabilitet."),
                 ("Kapital", "Invers volatilitet over 63 tidligere handledager. Enkeltvekten er maksimalt 25 %; "
                  "kapital som ikke kan fordeles innenfor taket beholdes som kontanter. "
                  "OSEBX over SMA200 gir 100 % investeringsramme, ellers 50 %. "
                  "Manglende benchmark gir ordinær ramme i den eksisterende motoren."),
                 ("Salg", "Vurderes på månedsslutt, ikke intradag: mer enn 20 % fall fra høyeste "
                  "kurs i de siste 126 kursobservasjonene utløser stoppsalg. "
                  "Rangering og vekter rebalanseres ved månedsslutt; septemberraden selger alt til kontanter. "
                  "Det finnes ikke en daglig garantert stoppris i denne simuleringen."),
                 ("Timing og kostnad", "Handler bruker observert sluttkurs på fullført månedsslutt; "
                  "beslutninger bruker tidligere observerte kurser og kjente finansielle versjoner. Kostnad er satt til 0 %. "
                  "Finansielle tall er ikke tilgjengelige før sin registrerte innsamlingsdato."),
             ],
             "lager": "PBROE_All3() → DETAILED_BACKTEST_v3()",
             "kilder": [], "n": tom_metrikk(), "posisjoner": [],
             "handler": pd.DataFrame(), "funnel": None, "kilde_note": "",
             "sharpe_harm": None, "frekvens": "månedlig", "mangler": None}

        bt = nyeste(PBROE_BT_DIR, "BT_v3_Enhanced_*.xlsx")
        s["kilder"].append(("Backtest", bt))
        if bt is None:
            s["mangler"] = (f"Fant ingen BT_v3_Enhanced_*.xlsx i {PBROE_BT_DIR}. "
                            f"Kjør PBROE_All3().")
            return s

        # ── Nøkkeltall: les Metrics-arket backtesten selv skrev ──────────────
        def tall(v):
            if v is None:
                return None
            t = str(v).replace("$", "").replace("%", "").replace(",", "").strip()
            try:
                return float(t)
            except ValueError:
                return None

        try:
            mdf = pd.read_excel(bt, sheet_name="Metrics")
            M = dict(zip(mdf["Metric"].astype(str).str.strip(),
                         mdf["Value"].astype(str).str.strip()))
            s["n"].update({
                "start": tall(M.get("Start Value")), "slutt": tall(M.get("End Value")),
                "total": tall(M.get("Total Return")), "cagr": tall(M.get("CAGR")),
                "sharpe": tall(M.get("Sharpe")), "sortino": tall(M.get("Sortino")),
                "mdd": tall(M.get("Max Drawdown")), "calmar": tall(M.get("Calmar")),
                "vol": tall(M.get("Volatility")),
                "treffrate": tall(M.get("Trade Win Rate")) or tall(M.get("Win Rate")),
                "snitt_handel": tall(M.get("Avg trade return")),
                "median_handel": tall(M.get("Median trade ret")),
                "beste": tall(M.get("Best trade")), "verste": tall(M.get("Worst trade")),
                "n_handler": int(tall(M.get("Total Trades")) or 0),
                "benchmark_cagr": tall(M.get("Benchmark CAGR")),
                "excess": tall(M.get("Excess Return")),
            })
            s["kilde_note"] = "Nøkkeltallene er lest rett fra Metrics-arket."
            n_stop = int(tall(M.get("Stop-loss events")) or 0)
            if n_stop:
                s["n"]["exit_miks"] = f"Stop-loss: {n_stop}"
        except Exception as e:
            s["kilde_note"] = f"Metrics-arket kunne ikke leses ({e})."

        # ── Egenkapitalkurve: periode og harmonisert Sharpe ──────────────────
        try:
            ec_df = pd.read_excel(bt, sheet_name="Equity_Curve")
            ec_df["Date"] = pd.to_datetime(ec_df["Date"], errors="coerce")
            ec_df = ec_df.dropna(subset=["Date"]).sort_values("Date").set_index("Date")
            kol = "Strategy_v3" if "Strategy_v3" in ec_df.columns else ec_df.columns[0]
            ec = ec_df[kol].astype(float)
            today = pd.Timestamp.now().normalize()
            if len(ec) and ec.index.max() > today:
                s["data_advarsel"] = ("PB-ROE-kurven inneholder en fremtidig månedssluttetikett "
                    f"({ec.index.max():%Y-%m-%d}). Rapportdato er {today:%Y-%m-%d}; "
                    "etiketten er ikke dokumentasjon på observerte fremtidige priser. "
                    "Tallene gjengir den uendrede motoren og inkluderer en uferdig måned.")
            k = kurve_metrikk(ec, 12, RF_HARMONISERT)
            s["n"]["periode"], s["n"]["n_ar"] = k["periode"], k["n_ar"]
            for felt in ("start", "slutt", "total", "cagr", "mdd", "vol"):
                if s["n"][felt] is None:
                    s["n"][felt] = k[felt]
            s["sharpe_harm"] = sharpe_harmonisert(ec)
        except Exception as e:
            print(f"  PB-ROE: Equity_Curve kunne ikke leses: {e}")

        # ── Beholdning: siste rad i Monthly_Holdings, beriket fra Scored ─────
        oppslag = {}
        scored = nyeste(PBROE_SCORED_DIR, "Scored_*.xlsx")
        s["kilder"].append(("Scoring", scored))
        if scored is not None:
            try:
                sdf = pd.read_excel(scored)
                for i, r in sdf.iterrows():
                    n = str(r.get("Company Name", r.get("Company",
                             r.get("Ticker", "")))).strip().upper()
                    if n:
                        oppslag[n] = (r, i + 1)
            except Exception as e:
                print(f"  PB-ROE: Scored-fil kunne ikke leses: {e}")

        try:
            mh = pd.read_excel(bt, sheet_name="Monthly_Holdings")
            if not mh.empty:
                siste = mh.iloc[-1]
                tekst = str(siste.get("holdings", "")).strip()
                s["regime"] = str(siste.get("market_regime", "") or "")
                if tekst not in KONTANTMERKER:
                    for rang, tkr in enumerate(
                            [t.strip() for t in tekst.split(",") if t.strip()], 1):
                        p = {"ticker": tkr, "selskap": tkr, "rang": rang}
                        rad = oppslag.get(tkr.upper())
                        if rad is not None:
                            r, fallback_rang = rad
                            def g(kol, d=2):
                                v = r.get(kol)
                                return round(float(v), d) if pd.notna(v) else None
                            p["rang"] = (int(r["Score_Rank"])
                                         if pd.notna(r.get("Score_Rank")) else fallback_rang)
                            p["score"] = g("Combined_score", 3)
                            p["pb"] = g("PB Number")
                            p["roe"] = g("ROE Number")
                            p["momentum"] = g("Momentum_pct", 1)
                            if pd.notna(r.get("Industry")):
                                p["bransje"] = str(r["Industry"]).strip()
                            for navnekol in ("Company Name", "Company"):
                                if pd.notna(r.get(navnekol)):
                                    p["selskap"] = str(r[navnekol]).strip()
                                    break
                        s["posisjoner"].append(p)
                else:
                    s["kontant"] = tekst
        except Exception as e:
            print(f"  PB-ROE: Monthly_Holdings kunne ikke leses: {e}")

        # ── Handler ──────────────────────────────────────────────────────────
        try:
            tl = pd.read_excel(bt, sheet_name="Trade_Log")
            tl["date"] = pd.to_datetime(tl["date"], errors="coerce")
            tl = tl.dropna(subset=["date"])
            tr = pd.DataFrame({
                "Dato": tl["date"], "Ticker": tl["ticker"].astype(str),
                "Selskap": tl["ticker"].astype(str),
                "Handling": tl["action"].astype(str).str.upper(),
                "Antall": tl["shares"], "Kurs": tl["price"], "Beløp": tl["value"],
                "PnL": np.nan, "Dager": np.nan,
                "Årsak": tl.get("industry", pd.Series("", index=tl.index)).astype(str),
            })
            s["handler"] = tr
            # Metrics-arket er fasit — rekonstruksjonen fyller bare hull.
            legg_til_handelsstat(s["n"], par_avkastning(tr), len(tr),
                                 bare_manglende=True)
        except Exception:
            pass  # Trade_Log skrives bare når det finnes handler

        s["kilder"].append(("Parametre", bt))
        try:
            pdf = pd.read_excel(bt, sheet_name="Parameters")
            P = dict(zip(pdf["Parameter"].astype(str).str.strip(),
                         pdf["Value"].astype(str).str.strip()))
            s["parametre"] = P
        except Exception:
            s["parametre"] = {}
        return s

    # ══════════════════════════════════════════════════════════════════════════
    # LESER 2 — NLP SENTIMENT (LEDELSE)
    # ══════════════════════════════════════════════════════════════════════════
    # Ledelses-sentiment har to motorer, og de måler ikke det samme:
    #
    #   v6  SentimentHendelseLab()  én rapport = én hendelse = ett kjøp, på
    #                               første handledag etter artikkelen.
    #   v4  SentimentManagement()   månedlig rebalansering. Den gikk gjennom alle
    #                               selskaper hver månedsslutt og regnet
    #                               bedringen fra forrige rapport på nytt — men
    #                               forrige rapport endrer seg ikke mellom
    #                               rapportene, så samme nyhet ga samme signal
    #                               måned etter måned.
    #
    # Rekkefølgen her er ikke alder, men hvilken motor som er kilden. Leses
    # reserven, sier kortet det: to motorer gir to svar om samme aksje.
    MGMT_HENDELSE = "Sentiment_v6_Hendelse_SMA*.xlsx"
    MGMT_MAANEDLIG = "Sentiment_v4*_SMA*.xlsx"

    def mgmt_hvordan_hendelse(M: Optional[dict]) -> List[Tuple[str, str]]:
        """
        «Slik handler den» lest ut av filen, ikke skrevet i hånden.

        Laben velger én av 60 kombinasjoner, og hvilken er ikke noe mailen kan
        gjette. Sto teksten fast her, ville kortet beskrevet en annen strategi
        enn den som faktisk ble handlet neste gang valget endret seg.
        """
        if M and M.get("selection_method") == "training_cagr":
            from html import escape
            import json
            try:
                rule = json.loads(str(M.get("exit_parameters_json", "{}")))
            except (ValueError, TypeError):
                rule = {}
            threshold = float(M.get("valgt_terskel_pst", 0))
            floor = float(M.get("sentiment_denominator_floor", .05))
            trend = str(M.get("krev_sma50", "")).upper() == "JA"
            hold = M.get("max_hold_sessions", rule.get("maks_dager", "ikke oppgitt"))
            exit_details = escape(str(M.get("exit_beskrivelse", "Ikke oppgitt i resultatfilen")))
            if rule.get("type") == "BREAKEVEN":
                exit_details += (" Aktivering krever en observert sluttkurs minst "
                                 f"{100 * float(rule.get('breakeven_trigger', .05)):.0f} % over kjøpskurs. "
                                 "Først en senere sluttkurs ≤ kjøpskurs utløser salg; "
                                 "fyll skjer neste handledags slutt, så tap kan bli større enn null.")
            if rule.get("replacement"):
                exit_details += (f" Erstatning ved full portefølje krever minst "
                    f"{M.get('replacement_min_age_sessions', 5)} handledagers alder og nytt signals styrke "
                    f"≥ {M.get('replacement_strength_ratio', 1.5)} × svakeste gamle styrke, "
                    f"der gammel styrke avtar som exp(−alder/{M.get('replacement_decay_sessions', 10)}).")
            return [
                ("Signal og terskel", "FinBERT-sentiment i innleste Euronext-artikler. "
                 "Hver ny artikkel sammenlignes med selskapets forrige artikkel: "
                 f"100 × (ny score − forrige score) / maks(|forrige score|, {floor:g}). "
                 f"Kjøp krever minst <strong>{threshold:g} % bedring</strong>. "
                 "Dette er prosentvis endring i sentimentscore, ikke forventet kursavkastning. "
                 "Innlest materiale kan også omfatte meldinger utover kvartalsrapporter."),
                ("Kjøpstidspunkt", "Første handledag strengt etter artikkeldato, til sluttkurs; "
                 "minst 120 tidligere kursobservasjoner. " +
                 ("Forrige handledags sluttkurs må ligge over sin SMA50." if trend
                  else "Denne inngangsvarianten har ikke SMA50-filter.")),
                ("Portefølje", f"{M.get('max_positions', 10)} separate kapitalplasser med lik startkapital. "
                 "Hver plass gjeninvesterer sin egen saldo; den rebalanseres ikke tilbake til lik vekt. "
                 "Senere artikler kan gi flere kjøpspartier i samme aksje. Mailen summerer dem per ticker. "
                 "Ledige plasser står i kontanter. Kostnad er 0 %."),
                ("Valgt salg", f"<strong>{escape(str(M.get('valgt_exit', '')))}</strong>: " + exit_details),
                ("Holdetid og utførelse", f"Senest {hold} handledager etter kjøp. "
                 "Prisbaserte stoppsignaler vurderes på foregående sluttkurs og utføres til neste "
                 "tilgjengelige sluttkurs; stopprosenten garanterer ikke salgspris. Nyhetsbasert exit "
                 "utføres tidligst første handledag etter artikkeldato. Manglende salgskurs utsetter utførelsen."),
                ("Variantvalg", escape(str(M.get("valgt_strategi", ""))) + ". " +
                 escape(str(M.get("valg_grunn", ""))) + " Baseline: " +
                 escape(str(M.get("baseline_variant", "")))),
                ("Trening / senere test", f"Trening til {escape(str(M.get('selection_cutoff', '')))}: "
                 f"{M.get('train_cagr_pst')} % CAGR. Senere periode: {M.get('test_cagr_pst')} % CAGR. "
                 "Senere testavkastning brukes ikke til å velge variant. Hovedtall inkluderer trening; "
                 "de er derfor ikke en ren test utenfor treningsperioden."),
                ("Regnskap", "Samme daglige simulering brukes for kurve, nøkkeltall, handler og "
                 "åpne posisjoner. Hver aksje verdsettes én gang som antall × siste observerte kurs. "
                 "Uavklarte kursbrudd eller langvarig manglende kurs blokkerer publisering."),
            ]
        terskel = exit_tekst = port = ""
        if M:
            t = M.get("valgt_terskel_pst")
            sma = str(M.get("krev_sma50", "")).strip().upper() == "JA"
            if t not in (None, ""):
                terskel = (f"Kjøper når bedringen er minst "
                           f"<strong>{float(t):.0f} %</strong>"
                           + (", og kursen ligger over SMA50 på kjøpsdagen"
                              if sma else "") + ".")
            exit_tekst = (f"<strong>{M.get('valgt_exit', '')}</strong> — "
                          f"{M.get('exit_beskrivelse', '')}")
            bestod = str(M.get("robusthetsport_bestod", "")).strip().upper()
            if bestod.startswith("IKKE VURDERT"):
                port = ("Kombinasjonen er valgt for hånd (AKSJE_SENT_VALG) og "
                        "aldri vurdert mot robusthetsporten. Det er ikke det "
                        "samme som å ha strøket på den — det er at ingen har "
                        "spurt.")
            elif bestod == "NEI":
                port = ("Ingen av de 60 kombinasjonene bestod robusthetsporten "
                        "(positiv alpha totalt, etter cutoff, og uten de største "
                        "vinnerne). Den valgte er den med mest data, ikke den med "
                        "best resultat — les tallene som en måling av at signalet "
                        "ikke virker, ikke som en strategi.")
            elif bestod == "JA":
                port = (f"Valgt blant de {M.get('kombinasjoner_bestod', '?')} av "
                        f"{M.get('kombinasjoner_testet', 60)} kombinasjoner som "
                        f"bestod robusthetsporten: positiv alpha totalt, positiv "
                        f"etter cutoff, og positiv når de største vinnerne er "
                        f"fjernet. Innenfor porten rangeres alpha etter cutoff "
                        f"først og CAGR sist — CAGR er tallet én ekstrem vinner "
                        f"kan kjøpe.")
        return [r for r in [
            ("Signal", "Kvartals- og årsrapporter hentes fra Euronext og settes "
                       "gjennom FinBERT setning for setning. Scoren er hvor "
                       "positivt <em>ledelsen selv</em> omtaler driften — ikke "
                       "hva markedet mener om den."),
            ("Hendelsen", "Det som utløser et kjøp er <em>endringen</em> fra "
                          "selskapets FORRIGE rapport, ikke nivået. En sjef som "
                          "alltid er optimistisk sier ingenting nytt; en som "
                          "plutselig er det, gjør det. Hver rapport er én "
                          "hendelse — samme nyhet kan ikke kjøpes to ganger."),
            ("Timing", "Kjøp på første handledag <em>strikt etter</em> "
                       "artikkeldatoen. Artiklene har mistet klokkeslettet, så "
                       "samme dags slutt kan være en kurs man ikke kunne "
                       "handlet: en rapport etter børsstengning har ingen "
                       "handlebar kurs den dagen."),
            ("Terskel", terskel),
            ("Exit", exit_tekst),
            ("Utvalg", port),
        ] if r[1]]

    MGMT_HVORDAN_MAANEDLIG = [
        ("Signal", "Kvartals- og årsrapporter hentes fra Euronext og "
                   "settes gjennom FinBERT setning for setning. "
                   "Scoren er hvor positivt <em>ledelsen selv</em> "
                   "omtaler driften — ikke hva markedet mener om den."),
        ("Ferskhet", "Hver artikkel forfaller 2 % per dag, så en "
                     "rapport er nesten uten vekt etter et halvt år. "
                     "Artikler eldre enn 365 dager teller ikke."),
        ("Filtre", "Trendfilter: kursen må ligge over SMA15 på "
                   "handledagen. En ledelse kan være optimistisk hele "
                   "veien ned. Norskspråklige artikler kastes, siden "
                   "FinBERT bare er trent på engelsk."),
        ("Exit", "Månedlig rebalansering til de 5 best scorede over "
                 "SMA, likevektet. Ingen kandidater over filteret "
                 "betyr kontanter, ikke nest best."),
    ]

    def summer_kjopspartier(pn: pd.DataFrame) -> pd.DataFrame:
        """Group lots with real share/cost bases; never average returns blindly."""
        if pn.empty or "ticker" not in pn or "shares" not in pn or "capital" not in pn:
            return pn
        rows = []
        for ticker, group in pn.groupby("ticker", sort=False):
            row = group.iloc[0].to_dict()
            shares = pd.to_numeric(group["shares"], errors="coerce")
            capital = pd.to_numeric(group["capital"], errors="coerce")
            marks = pd.to_numeric(group["market_value"], errors="coerce")
            if shares.isna().any() or capital.isna().any() or marks.isna().any() or shares.sum() <= 0:
                rows.extend(group.to_dict("records"))
                continue
            row.update(shares=float(shares.sum()), capital=float(capital.sum()),
                       market_value=float(marks.sum()), lots=len(group),
                       entry_price=float(capital.sum() / shares.sum()),
                       kurs_na=float(marks.sum() / shares.sum()),
                       avk_pst=float((marks.sum() / capital.sum() - 1) * 100))
            if len(group) > 1:
                # Entry events are different; a synthetic averaged sentiment would
                # imply a signal that never occurred. Keep those details in the lots sheet.
                row.update(bedring_pst=None, forrige_score=None, ny_score=None,
                           inn_dato=" / ".join(sorted(set(group["inn_dato"].astype(str)))), dager=None)
            rows.append(row)
        return pd.DataFrame(rows)

    def les_sentiment_mgmt() -> dict:
        s = {"navn": "NLP Sentiment — ledelse",
             "beskrivelse": "Euronext kvartals- og årsrapporter gjennom FinBERT. "
                            "Kjøper på endringen fra forrige rapport, dagen "
                            "etter at rapporten kom.",
             "hvordan": mgmt_hvordan_hendelse(None),
             "lager": "SentimentHendelseLab()",
             "kilder": [], "n": tom_metrikk(), "posisjoner": [],
             "handler": pd.DataFrame(), "funnel": None, "kilde_note": "",
             "sharpe_harm": None, "frekvens": "hendelsesdrevet", "mangler": None}

        f = nyeste(MGMT_DIR, MGMT_HENDELSE)
        hendelse = f is not None
        if f is None:
            # Reserven. Bedre enn et tomt kort, men det er en annen motor, og
            # kortet skal si hvilken — ellers leses tallene som om de kom fra
            # den som er kilden nå.
            f = nyeste(MGMT_DIR, MGMT_MAANEDLIG)
            s["beskrivelse"] = ("Euronext kvartals- og årsrapporter gjennom "
                                "FinBERT. Månedlig rebalansering med SMA-filter.")
            s["hvordan"] = MGMT_HVORDAN_MAANEDLIG
            s["lager"] = "SentimentManagement() → NlpSentimentTrader4_v4()"
            s["frekvens"] = "månedlig"
        s["kilder"].append(("Backtest", f))
        if f is None:
            s["mangler"] = (f"Fant verken {MGMT_HENDELSE} eller "
                            f"{MGMT_MAANEDLIG} i {MGMT_DIR}. "
                            f"Kjør SentimentHendelseLab().")
            return s

        # Nyere filer har et Metrics-ark: strategiens EGNE tall, skrevet av den
        # som regnet dem ut. Det arket vinner. Uten det regner vi fra kurven —
        # og da kan to lesere av samme fil komme fram til to svar, som er
        # nøyaktig det som skjedde 8. september.
        metrics: Optional[dict] = None
        try:
            ec_df = pd.read_excel(f, sheet_name="Equity_Curve")
            ec_df["Date"] = pd.to_datetime(ec_df["Date"], errors="coerce")
            ec_df = ec_df.dropna(subset=["Date"]).sort_values("Date").set_index("Date")
            ec = ec_df["Strategy"].astype(float)
            # Daily NAV supplies period and drawdown. Management risk statistics
            # use monthly observations, matching the engine's _maal_kurve.
            fallback = kurve_metrikk(ec, 252 if hendelse else 12, RF_HARMONISERT)
            if hendelse:
                monthly_returns = ec.resample("ME").last().dropna().pct_change().dropna()
                vol = float(monthly_returns.std() * np.sqrt(12)) if len(monthly_returns) > 1 else 0.0
                negative = monthly_returns[monthly_returns < 0]
                downside = float(negative.std() * np.sqrt(12)) if len(negative) > 1 else 0.0
                fallback.update(vol=vol * 100,
                    sharpe=(fallback["cagr"] / 100 - RF_HARMONISERT) / vol if vol > 0 else None,
                    sortino=(fallback["cagr"] / 100 - RF_HARMONISERT) / downside if downside > 0 else None)
            s["n"].update(fallback)
            s["sharpe_harm"] = sharpe_harmonisert(ec)
            s["kilde_note"] = ("Beregnet fra Equity_Curve — filen har ikke noe "
                               "Metrics-ark. Samme formel som strategien logger.")
            try:
                mdf = pd.read_excel(f, sheet_name="Metrics")
            except Exception:
                mdf = None
            if hendelse and (mdf is None or mdf.empty):
                s["mangler"] = "Ledelsessentiment må kjøres på nytt: Metrics med validert regnskap mangler."
                return s
            if mdf is not None and not mdf.empty:
                M = metrics = mdf.iloc[0].to_dict()
                if hendelse and (int(M.get("accounting_version", 0) or 0) < 2
                                  or str(M.get("data_valid", "")).lower() not in ("true", "1", "1.0", "ja")):
                    s["mangler"] = ("Ledelsessentiment må kjøres på nytt: denne filen mangler "
                        "validert regnskap versjon 2. Den eldre motoren verdsatte åpne posisjoner "
                        "med kursforholdet to ganger. Historisk CAGR og drawdown fra denne filen "
                        "vises derfor ikke som gyldige resultater.")
                    return s
                if str(M.get("cagr_meningsfull", "")).strip().upper() == "NEI":
                    s["n"]["cagr_meningsfull"] = False
                # CAGR og total må være med. Uten dem viste mailen 157,37 %
                # mens loggen viste 146,68 % for den samme filen — halve
                # poenget med arket var å gjøre det umulig.
                for nokkel, felt, skala in (("cagr", "cagr", 100),
                                            ("total_avkastning", "total", 100),
                                            ("sharpe", "sharpe", 1),
                                            ("sortino", "sortino", 1),
                                            ("max_drawdown", "mdd", 100),
                                            ("calmar", "calmar", 1),
                                            ("volatilitet", "vol", 100),
                                            ("snitt_hold_dager", "holdedager", 1),
                                            ("benchmark_cagr", "benchmark_cagr", 100),
                                            # Handelsstatistikken må med i samme
                                            # slengen. Uten den regnet mailen
                                            # snittet på nytt fra loggen, og
                                            # gjettet paringen feil når samme
                                            # aksje sto i to plasser: 2,90 % der
                                            # strategien målte 3,47 %.
                                            ("treffrate", "treffrate", 100),
                                            ("snitt_handel_pst", "snitt_handel", 1),
                                            ("median_handel_pst", "median_handel", 1),
                                            ("beste_handel_pst", "beste", 1),
                                            ("verste_handel_pst", "verste", 1)):
                    if nokkel in M:
                        v = M[nokkel]
                        s["n"][felt] = (None if v is None or pd.isna(v)
                                        else float(v) * skala)
                s["kilde_note"] = (
                    f"Fra arket Metrics — strategiens egne tall"
                    + (f", {M['maanedspunkter']} månedspunkter"
                       if "maanedspunkter" in M else "")
                    + (f". Drawdown målt på {M['drawdown_grunnlag']}."
                       if "drawdown_grunnlag" in M else "."))
                if hendelse:
                    # «Slik handler den» leses ut av filen. Laben velger én av
                    # 60 kombinasjoner, og hvilken kan ikke gjettes herfra.
                    s["hvordan"] = mgmt_hvordan_hendelse(M)
                    # Tallene over er labens egne, uregnet — si hvor de kommer
                    # fra, og at posisjonslisten kommer et annet sted fra.
                    if "maalt_paa" in M:
                        s["kilde_note"] += f" Målt på: {M['maalt_paa']}."
                    if "apne_na" in M:
                        s["kilde_note"] += (f" Åpne kjøpspartier: {M['apne_na']}; "
                            "samme simulering og sluttdato som nøkkeltallene.")
                    valgt = str(M.get("valgt_strategi", "")).strip()
                    kode = str(M.get("valgt_exit", "")).strip()
                    if valgt and kode:
                        s["lager"] = f"SentimentHendelseLab() → {valgt} + {kode}"
                    port_status = str(M.get("robusthetsport_bestod", "")).strip().upper()
                    if port_status == "NEI":
                        s["advarsel"] = str(M.get("valg_grunn", "")).strip()
                    elif port_status.startswith("IKKE VURDERT"):
                        s["advarsel"] = (
                            "Kombinasjonen er valgt for hånd og aldri målt mot "
                            "robusthetsporten: "
                            + str(M.get("valg_grunn", "")).strip())
                    if "benchmark_grunnlag" in M:
                        s["kilde_note"] += (f" Benchmark: "
                                            f"{M['benchmark_grunnlag']}.")
                else:
                    s["kilde_note"] += (
                        " NB: dette er den MÅNEDLIGE motoren. Den hendelsesdrevne "
                        "har ikke skrevet en fil, så tallene er ikke de samme som "
                        "de andre kortene viser for denne strategien.")
            if "Benchmark" in ec_df.columns:
                bn = ec_df["Benchmark"].dropna().astype(float)
                if len(bn) >= 2 and float(bn.iloc[0]) > 0 and s["n"]["n_ar"]:
                    saved_benchmark = metrics.get("benchmark_cagr") if metrics else None
                    bc = (float(saved_benchmark) if saved_benchmark is not None and pd.notna(saved_benchmark)
                          else (float(bn.iloc[-1]) / float(bn.iloc[0])) ** (1 / s["n"]["n_ar"]) - 1)
                    s["n"]["benchmark_cagr"] = bc * 100
                    # CAGR kan mangle med vilje: hendelseslaben rapporterer
                    # ingen CAGR når perioden er under et halvt år, og skriver
                    # null i Metrics. Da finnes det ingen meravkastning å regne,
                    # og å trekke fra på None veltet hele kortet — «Equity_Curve
                    # kunne ikke leses», for en strategi som hadde lest fint.
                    if s["n"]["cagr"] is not None:
                        s["n"]["excess"] = s["n"]["cagr"] - bc * 100
        except Exception as e:
            s["mangler"] = f"Equity_Curve kunne ikke leses: {e}"
            return s

        # Arket «Posisjoner_Na» bærer det som UTLØSTE hvert kjøp: 0,20 → 0,82,
        # 310 % bedring. Monthly_Holdings har bare en komma-separert streng, og
        # en posisjonsliste uten endringen sier ikke hvorfor aksjen er der.
        try:
            pn = pd.read_excel(f, sheet_name="Posisjoner_Na")
        except Exception:
            pn = None
        if pn is not None and not pn.empty:
            pn = summer_kjopspartier(pn)
            for i, r in enumerate(pn.to_dict("records"), 1):
                s["posisjoner"].append({
                    "ticker": str(r.get("ticker", "")),
                    "selskap": str(r.get("selskap", "") or r.get("ticker", "")),
                    "rang": i,
                    "bedring": r.get("bedring_pst"),
                    "skifte": (f"{float(r['forrige_score']):+.2f} → "
                               f"{float(r['ny_score']):+.2f}"
                               if pd.notna(r.get("forrige_score"))
                               and pd.notna(r.get("ny_score")) else ""),
                    "inn_dato_str": str(r.get("inn_dato", "")),
                    "dager": r.get("dager"),
                    "inn_kurs": r.get("entry_price"),
                    "siste_kurs": r.get("kurs_na"),
                    "avk_pct": r.get("avk_pst"),
                    "partier": r.get("lots", 1),
                    "antall": r.get("shares"),
                    "verdi_na": r.get("market_value"),
                })
            s["pos_kolonner"] = [
                ("#", "_i", "int"), ("Ticker", "ticker", "fet"),
                ("Selskap", "selskap", "tekst"), ("Bedring", "bedring", "t1p"),
                ("Partier", "partier", "int"), ("Antall", "antall", "nok"),
                ("Sentiment", "skifte", "tekst"),
                ("Kjøpt", "inn_dato_str", "tekst"), ("Dager", "dager", "int"),
                ("Inngang", "inn_kurs", "t2"), ("Siste", "siste_kurs", "t2"),
                ("Avk.", "avk_pct", "farge1")]
        else:
            try:
                mh = pd.read_excel(f, sheet_name="Monthly_Holdings")
                if not mh.empty:
                    tekst = str(mh.iloc[-1].get("holdings", "")).strip()
                    if tekst not in KONTANTMERKER:
                        for i, tkr in enumerate(
                                [x.strip() for x in tekst.split(",") if x.strip()], 1):
                            s["posisjoner"].append({"ticker": tkr, "selskap": tkr,
                                                    "rang": i})
                    else:
                        s["kontant"] = tekst
            except Exception as e:
                print(f"  NLP-ledelse: Monthly_Holdings kunne ikke leses: {e}")

        try:
            tl = pd.read_excel(f, sheet_name="Trade_Log")
            tl["date"] = pd.to_datetime(tl["date"], errors="coerce")
            tl = tl.dropna(subset=["date"])
            tr = pd.DataFrame({
                "Dato": tl["date"], "Ticker": tl["ticker"].astype(str),
                "Selskap": tl["ticker"].astype(str),
                "Handling": tl["action"].astype(str).str.upper(),
                "Antall": tl["shares"], "Kurs": tl["price"], "Beløp": tl["value"],
                # Har loggen P&L, slutter mailen å gjette hvilket kjøp et salg
                # hører til — og den gjetningen var feil når strategien eide
                # samme aksje i to plasser samtidig.
                "PnL": (pd.to_numeric(tl["pnl"], errors="coerce")
                        if "pnl" in tl.columns else np.nan),
                "Dager": (pd.to_numeric(tl["dager"], errors="coerce")
                          if "dager" in tl.columns else np.nan),
                # Hele poenget med de fem exitene er HVILKEN regel som fyrte.
                # Kolonnen sto tom mens loggen bar «sentiment_reversering» og
                # «alpha_horisont» — skrevet av strategien, kastet av mailen.
                "Årsak": (tl["reason"].astype(str) if "reason" in tl.columns
                          else pd.Series("", index=tl.index)),
            })
            s["handler"] = tr
            # bare_manglende når strategien selv har talt: da fyller
            # rekonstruksjonen bare det Metrics ikke har (n_lukket), og
            # overskriver ikke tall strategien alt har målt riktig.
            legg_til_handelsstat(
                s["n"], par_avkastning(tr), len(tr),
                bare_manglende=bool(metrics
                                    and metrics.get("snitt_handel_pst") is not None))
            # legg_til_handelsstat teller LOGGRADER, og en handel er to rader:
            # ett kjøp og ett salg. 92 handler ble 184 i kortet, ved siden av
            # «92» i Metrics-arket i samme fil. Har strategien selv talt dem,
            # er det tallet som gjelder.
            if metrics and metrics.get("handler") is not None:
                try:
                    s["n"]["n_handler"] = int(metrics["handler"])
                except (TypeError, ValueError):
                    pass
        except Exception:
            pass
        return s

    # ══════════════════════════════════════════════════════════════════════════
    # LESER 3 — SENTIMENT MOMENTUM v3.1
    # ══════════════════════════════════════════════════════════════════════════
    TS_MONSTER = re.compile(r"S5_SentMom31_Portfolio_(\d{8}_\d{6})\.xlsx$")

    def les_sentmom31() -> dict:
        s = {"navn": "Sentiment Momentum v3.1",
             "beskrivelse": "Nyhetssentiment som primærsignal, pris kun som mykt "
                            "veto. Daglig evaluering, inv-vol-vekting.",
             "hvordan": [
                 ("Nyhetsgrunnlag", "Bare artikler datert før handledagen, siste 150 kalenderdager; "
                  "minst 1 artikkel per selskap. Vekten halveres hver 30. dag. "
                  "Akselerasjon sammenligner 0–21 med 22–63 dager; oppmerksomhet måles over 45 dager."),
                 ("Kjøp", "Daglig score = 45 % z-drift + 20 % z-akselerasjon + 20 % z-oppmerksomhet "
                  "+ 15 % z-konsensus. Med minst 25 selskaper fjernes scorer over 99-persentilen. "
                  "Score må være minst −0,25 og kurs over SMA200; relativ styrke-filteret er av. "
                  "De inntil 5 høyest rangerte med kurs kan kjøpes."),
                 ("Vekting og regime", "Invers 20-dagers volatilitet; rammen skaleres med antall kandidater / 5. "
                  "Vektgulv er 10 % × fyllingsgrad, tak 30 %. Nye kjøp halveres i RISK_OFF "
                  "(benchmark under SMA200). Eksisterende posisjoner rebalanseres ikke bare fordi "
                  "regimet eller vekten endres; ubrukte plasser er kontanter."),
                 ("Salg i rekkefølge", "Daglig: (1) kurs ≤ 82 % av kjøpskurs, (2) etter at kursen "
                  "har vært minst +5 %: fall ≥ 18 % fra høyeste observerte kurs, (3) minst 45 "
                  "kalenderdager siden kjøp. Deretter selges navn som er ute av dagens toppliste "
                  "når en ikke-tom ny kandidatliste utløser rebalansering. Tomt signalutvalg "
                  "gir ikke automatisk salg; risikostopp og tidsgrense gjelder fortsatt."),
                 ("Timing og kostnad", "Prisbaserte beslutninger bruker forrige observerte sluttkurs og utføres ved neste tilgjengelige sluttkurs, "
                  "med prisfiltre basert på tidligere observasjoner. Et solgt navn kan kjøpes igjen samme dag "
                  "hvis det fortsatt kvalifiserer. Kostnad 0 %; risikofri rente i Sharpe er 4 %. "
                  "Signaler må være kjent før handelsdagen; lange hull i beholdningens priser blokkerer resultatet."),
             ],
             "lager": "SentimentMomentumV31()",
             "kilder": [], "n": tom_metrikk(), "posisjoner": [],
             "handler": pd.DataFrame(), "funnel": None, "kilde_note": "",
             "sharpe_harm": None, "frekvens": "daglig", "mangler": None}

        # Alle fire filene får samme tidsstempel fra Config.__init__. Vi parer på
        # det, ikke på filtidspunkt: trades- og signalfilen skrives bare når de
        # har innhold, så en kjøring uten handler etterlater forrige kjørings
        # filer som «nyeste» på disk.
        kandidater = []
        if SENTMOM_DIR.exists():
            for p in SENTMOM_DIR.glob("S5_SentMom31_Portfolio_*.xlsx"):
                if p.name.startswith("~$"):
                    continue
                m = TS_MONSTER.search(p.name)
                if m:
                    kandidater.append((m.group(1), p))
        if not kandidater:
            s["kilder"].append(("Portefølje", None))
            s["mangler"] = (f"Fant ingen S5_SentMom31_Portfolio_*.xlsx i "
                            f"{SENTMOM_DIR}. Kjør SentimentMomentumV31() med "
                            f"DIAGNOSE_ONLY = False.")
            return s

        ts, portefolje = max(kandidater, key=lambda x: x[0])
        s["tidsstempel"] = ts

        def sosken(navn):
            p = SENTMOM_DIR / f"S5_SentMom31_{navn}_{ts}.xlsx"
            return p if p.exists() else None

        f_trades, f_signals, f_funnel = (sosken("Trades"), sosken("Signals"),
                                         sosken("Funnel"))
        s["kilder"] += [("Portefølje", portefolje), ("Handler", f_trades),
                        ("Signaler", f_signals), ("Funnel", f_funnel)]

        hist = pd.read_excel(portefolje)
        hist["Date"] = pd.to_datetime(hist["Date"], errors="coerce")
        hist = hist.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)
        if hist.empty:
            s["mangler"] = "Porteføljefilen er tom."
            return s

        # Nøyaktig samme regnestykke som SentimentMomentumV31._save(), slik at
        # mail og konsoll ikke kan rapportere ulike tall for samme kjøring.
        start = float(SENTMOM_START_CAPITAL)
        slutt = float(hist["Portfolio_Value"].iloc[-1])
        n_dager = max((hist["Date"].iloc[-1] - hist["Date"].iloc[0]).days, 1)
        rets = hist["Portfolio_Value"].pct_change().dropna()
        std = float(rets.std()) if len(rets) else 0.0
        ned = rets[rets < 0]
        ned_std = float(ned.std()) if len(ned) else 0.0
        cummax = hist["Portfolio_Value"].cummax()
        mdd = float(((hist["Portfolio_Value"] - cummax) / cummax).min()) * 100
        cagr = ((slutt / start) ** (365.25 / n_dager) - 1) * 100

        s["n"].update({
            "start": start, "slutt": slutt, "total": (slutt / start - 1) * 100,
            "cagr": cagr, "n_ar": n_dager / 365.25,
            "sharpe": ((rets.mean() * 252 - SENTMOM_RISK_FREE) /
                       (std * np.sqrt(252))) if std > 0 else 0.0,
            "sortino": ((rets.mean() * 252 - SENTMOM_RISK_FREE) /
                        (ned_std * np.sqrt(252))) if ned_std > 0 else 0.0,
            "mdd": mdd, "calmar": cagr / abs(mdd) if mdd else 0.0,
            "vol": std * np.sqrt(252) * 100 if std > 0 else 0.0,
            "periode": f"{hist['Date'].iloc[0]:%Y-%m-%d} → {hist['Date'].iloc[-1]:%Y-%m-%d}",
        })
        quote_age = (pd.Timestamp.now().normalize() - hist["Date"].iloc[-1].normalize()).days
        if quote_age > 5:
            s["data_advarsel"] = (f"Sentiment Momentum bruker kurser til {hist['Date'].iloc[-1]:%Y-%m-%d} "
                f"({quote_age} kalenderdager før rapporten). Dette er et historisk resultat; "
                "posisjonene er fra denne datoen, ikke bekreftede posisjoner i dag. "
                "At resultatfilen nylig ble skrevet oppdaterer ikke kildedataene.")
        s["kilde_note"] = (f"Regnet som _save() gjør det — risikofri rente "
                           f"{SENTMOM_RISK_FREE:.0%}, startkapital "
                           f"{SENTMOM_START_CAPITAL:,.0f}".replace(",", " ") + " kr.")
        s["investert"] = float((hist["Position_Value"] / hist["Portfolio_Value"]).mean()) * 100
        s["risk_off"] = (float((hist["Regime"] == "RISK_OFF").mean()) * 100
                         if "Regime" in hist.columns else None)
        s["handelsdager"] = int(len(hist))
        s["sharpe_harm"] = sharpe_harmonisert(
            hist.set_index("Date")["Portfolio_Value"].astype(float))

        trades = pd.DataFrame()
        if f_trades:
            t = pd.read_excel(f_trades)
            t["Date"] = pd.to_datetime(t["Date"], errors="coerce")
            t = t.dropna(subset=["Date"])
            trades = pd.DataFrame({
                "Dato": t["Date"], "Ticker": t["Ticker"].astype(str),
                "Selskap": t["Company"].astype(str),
                "Handling": t["Action"].astype(str).str.upper(),
                "Antall": t["Shares"], "Kurs": t["Price"], "Beløp": t["Value"],
                "PnL": t["PnL"],
                "Dager": t["Days_Held"] if "Days_Held" in t.columns else np.nan,
                "Årsak": t["Reason"].astype(str) if "Reason" in t.columns else "",
            })
            s["handler"] = trades

            # Denne strategien skriver PnL selv — ingen rekonstruksjon.
            salg = trades[(trades["Handling"] == "SELL") & trades["PnL"].notna()]
            s["n"]["n_handler"] = int(len(trades))
            s["n"]["n_lukket"] = int(len(salg))
            if len(salg):
                grunnlag = salg["Antall"] * salg["Kurs"] - salg["PnL"]
                avk = (salg["PnL"] / grunnlag.replace(0, np.nan) * 100).dropna()
                s["n"].update({
                    "treffrate": float((salg["PnL"] > 0).mean()) * 100,
                    "snitt_handel": float(avk.mean()) if len(avk) else None,
                    "median_handel": float(avk.median()) if len(avk) else None,
                    "beste": float(avk.max()) if len(avk) else None,
                    "verste": float(avk.min()) if len(avk) else None,
                    "holdedager": (float(salg["Dager"].mean())
                                   if salg["Dager"].notna().any() else None),
                })
                if "Årsak" in salg.columns:
                    k = salg["Årsak"].astype(str).str.split().str[0].value_counts()
                    s["n"]["exit_miks"] = " · ".join(f"{a}: {b}" for a, b in k.items())
            if "Fee" in t.columns:
                s["n"]["gebyrer"] = float(t["Fee"].fillna(0).sum())

        signals = pd.DataFrame()
        if f_signals:
            signals = pd.read_excel(f_signals)
            signals["Date"] = pd.to_datetime(signals["Date"], errors="coerce")

        s["posisjoner"] = sentmom_posisjoner(trades, signals, hist["Date"].iloc[-1])

        if f_funnel:
            s["funnel"] = funnel_sammendrag(pd.read_excel(f_funnel))
        return s

    def sluttkurser() -> Dict[str, float]:
        p = nyeste(PRICE_DIR, "Stock_Prices_*.xlsx")
        if p is None:
            return {}
        try:
            df = pd.read_excel(p)
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            df = df.dropna(subset=["Date", "Close", "Ticker"]).sort_values("Date")
            return {str(t): float(g["Close"].iloc[-1]) for t, g in df.groupby("Ticker")}
        except Exception as e:
            print(f"  Merk: prisfil kunne ikke leses: {e}")
            return {}

    def sentmom_posisjoner(trades, signals, siste_dato) -> List[dict]:
        if trades.empty:
            return []
        kurser = sluttkurser()
        sig = {}
        if not signals.empty:
            for _, r in signals.iterrows():
                sig[(r["Date"], str(r["Ticker"]))] = r

        apen: Dict[str, dict] = {}
        for _, r in trades.sort_values("Dato").iterrows():
            t = str(r["Ticker"]).strip()
            if r["Handling"] == "BUY":
                apen[t] = {"ticker": t, "selskap": str(r["Selskap"]),
                           "inn_dato": r["Dato"],
                           "inn_kurs": float(r["Kurs"]) if pd.notna(r["Kurs"]) else None,
                           "antall": int(r["Antall"]) if pd.notna(r["Antall"]) else None}
            elif r["Handling"] == "SELL":
                apen.pop(t, None)

        ut = []
        for t, p in apen.items():
            rad = dict(p)
            rad["dager"] = (siste_dato - p["inn_dato"]).days
            rad["inn_dato_str"] = f"{p['inn_dato']:%Y-%m-%d}"
            k = kurser.get(t)
            if k and p.get("inn_kurs"):
                rad["siste_kurs"] = k
                rad["avk_pct"] = (k / p["inn_kurs"] - 1) * 100
                if p.get("antall"):
                    rad["verdi_na"] = k * p["antall"]
            r = sig.get((p["inn_dato"], t))
            if r is not None:
                rad.update({"composite": r.get("Composite"), "z_drift": r.get("zDrift"),
                            "n_artikler": r.get("NArticles"), "vekt": r.get("Weight_pct")})
            ut.append(rad)
        ut.sort(key=lambda r: r["inn_dato"], reverse=True)
        return ut

    STEG = ["selskaper_i_vindu", "etter_min_artikler", "etter_ekstremkutt",
            "etter_z_gulv", "etter_prisfilter", "valgt"]
    STEG_NAVN = {"selskaper_i_vindu": "Selskaper i vinduet",
                 "etter_min_artikler": "Etter min. artikler",
                 "etter_ekstremkutt": "Etter ekstremkutt",
                 "etter_z_gulv": "Etter z-gulv",
                 "etter_prisfilter": "Etter prisveto", "valgt": "Valgt"}

    def funnel_sammendrag(funnel: pd.DataFrame):
        if funnel.empty:
            return None
        dager = max(len(funnel), 1)
        rader, forrige, verst = [], None, None
        for steg in STEG:
            if steg not in funnel.columns:
                continue
            sum_ = float(funnel[steg].sum())
            nz = int((funnel[steg] > 0).sum())
            rader.append({"steg": STEG_NAVN[steg], "snitt": sum_ / dager,
                          "dager": nz, "pct": nz / dager * 100})
            if forrige and forrige[1] > 0:
                fall = 1 - sum_ / forrige[1]
                if verst is None or fall > verst[1]:
                    verst = (f"{STEG_NAVN[forrige[0]]} → {STEG_NAVN[steg]}", fall)
            forrige = (steg, sum_)
        return rader, (f"Største fall: {verst[0]} — {verst[1]*100:.0f} % kuttet"
                       if verst else None)

    # ══════════════════════════════════════════════════════════════════════════
    # OVERLAPP
    # ══════════════════════════════════════════════════════════════════════════
    def finn_overlapp(strategier: List[dict]) -> Dict[str, List[str]]:
        kart = defaultdict(set)
        for s in strategier:
            for p in s["posisjoner"]:
                t = norm_ticker(p.get("ticker"))
                if t:
                    kart[t].add(s["navn"])
        return {t: sorted(navn) for t, navn in kart.items() if len(navn) >= 2}

    # ══════════════════════════════════════════════════════════════════════════
    # FORMATERING
    # ══════════════════════════════════════════════════════════════════════════
    TOM = '<span style="color:#bbb;">—</span>'

    def f_t(x, d=2, sfx="", fortegn=False):
        if x is None or (isinstance(x, float) and pd.isna(x)):
            return TOM
        return (f"{{:+.{d}f}}" if fortegn else f"{{:.{d}f}}").format(x) + sfx

    def f_c(x, d=2, sfx="%", fortegn=True):
        if x is None or (isinstance(x, float) and pd.isna(x)):
            return TOM
        c = "#2e7d32" if x > 0 else ("#c62828" if x < 0 else "#555")
        v = (f"{{:+.{d}f}}" if fortegn else f"{{:.{d}f}}").format(x)
        return f'<span style="color:{c};font-weight:600;">{v}{sfx}</span>'

    def f_n(x, d=0):
        if x is None or (isinstance(x, float) and pd.isna(x)):
            return TOM
        return f"{x:,.{d}f}".replace(",", " ")

    def celle(lab, verdi, farge="#333", stor=True):
        px = 18 if stor else 15
        return (f'<td style="text-align:center;padding:8px 6px;border:none;">'
                f'<div style="font-size:10px;color:#888;text-transform:uppercase;'
                f'letter-spacing:.5px;">{lab}</div><div style="font-size:{px}px;'
                f'font-weight:bold;color:{farge};margin-top:2px;">{verdi}</div></td>')

    def metrikk_rad(tittel, celler):
        if not celler:
            return ""
        return (f'<tr><td colspan="99" style="font-size:10px;color:#666;'
                f'text-transform:uppercase;letter-spacing:.5px;padding:8px 6px 0;'
                f'font-weight:600;">{tittel}</td></tr><tr>{"".join(celler)}</tr>')

    # ══════════════════════════════════════════════════════════════════════════
    # HTML — SAMMENLIGNING
    # ══════════════════════════════════════════════════════════════════════════
    def bygg_sammenligning(strategier: List[dict]) -> str:
        aktive = [s for s in strategier if s["mangler"] is None]
        if len(aktive) < 2:
            return ""
        rader = ""
        for s in aktive:
            n = s["n"]
            rader += f"""    <tr>
        <td><strong>{s['navn']}</strong><br>
            <span style="font-size:10px;color:#999;">{n.get('periode') or '—'}
            · {s['frekvens']}</span></td>
        <td style="text-align:right;">{f_c(n.get('cagr'), 1)}</td>
        <td style="text-align:right;">{f_t(n.get('sharpe'))}</td>
        <td style="text-align:right;background:#f3f6ff;">
            <strong>{f_t(s.get('sharpe_harm'))}</strong></td>
        <td style="text-align:right;">{f_c(n.get('mdd'), 1, fortegn=False)}</td>
        <td style="text-align:right;">{f_t(n.get('treffrate'), 1, ' %')}</td>
        <td style="text-align:right;">{n.get('n_handler') if n.get('n_handler') is not None else '—'}</td>
        <td style="text-align:right;">{n.get('n_lukket') if n.get('n_lukket') is not None else '—'}</td>
        <td style="text-align:right;">{len(s['posisjoner'])}</td>
    </tr>\n"""
        return f"""
<div class="card">
    <h2>Sammenligning</h2>
    <p class="sub">Alle tre strategiene side om side. Les den grå kolonnen, ikke den hvite.</p>
    <table>
        <tr><th>Strategi</th><th>CAGR</th><th>Sharpe<br>
            <span style="font-weight:400;font-size:10px;">rapportert</span></th>
            <th style="background:#e8edff;">Sharpe<br>
            <span style="font-weight:400;font-size:10px;">harmonisert</span></th>
            <th>Max DD</th><th>Treffrate</th><th>Handler</th><th>Lukket</th>
            <th>Åpne</th></tr>
{rader}    </table>
    <div style="background:#fff8e1;border:1px solid #ffe082;border-radius:6px;
                padding:10px 12px;margin-top:12px;font-size:11.5px;color:#5d4037;
                line-height:1.55;">
        <strong>Tallene er ikke uten videre sammenlignbare.</strong>
        De tre strategiene regner Sharpe ulikt i sin egen kode: PB-ROE og
        NLP-ledelse bruker (CAGR&nbsp;&minus;&nbsp;3&nbsp;%)&nbsp;/&nbsp;vol på en
        <em>månedlig</em> kurve, SentMom31 bruker
        (snitt&middot;252&nbsp;&minus;&nbsp;4&nbsp;%)&nbsp;/&nbsp;(std&middot;&radic;252)
        på en <em>daglig</em> kurve. Kolonnen «rapportert» gjengir hver strategis
        eget tall, så mailen aldri motsier konsollen. Kolonnen «harmonisert»
        måler alle tre likt — månedlig kurve, (CAGR&nbsp;&minus;&nbsp;3&nbsp;%)&nbsp;/&nbsp;vol.
        Periodene er dessuten ulike, og ingen av backtestene trekker fra
        transaksjonskostnader.
    </div>
</div>
"""

    # ══════════════════════════════════════════════════════════════════════════
    # HTML — PER STRATEGI
    # ══════════════════════════════════════════════════════════════════════════
    def bygg_nokkeltall(s: dict) -> str:
        n, grønn, rød = s["n"], "#2e7d32", "#c62828"
        avk = [c for c in [
            celle("Start", f_n(n["start"]) + " kr") if n["start"] else None,
            celle("Slutt", f_n(n["slutt"]) + " kr") if n["slutt"] else None,
            celle("Total", f_t(n["total"], 2, " %", True),
                  grønn if (n["total"] or 0) > 0 else rød) if n["total"] is not None else None,
            # Er perioden for kort, står tallet fortsatt der — men det heter
            # noe annet og er oransje, ikke grønt. Et grønt «+146,68 %» ved
            # siden av et grønt «+25,40 %» leses som «bedre», og det er det
            # ikke: det ene er tre år, det andre er åtte måneder.
            (celle("CAGR", f_t(n["cagr"], 2, " %", True),
                   grønn if (n["cagr"] or 0) > 0 else rød)
             if n.get("cagr_meningsfull", True)
             else celle("CAGR ⚠ for kort", f_t(n["cagr"], 2, " %", True), "#e65100")
             ) if n["cagr"] is not None else None,
        ] if c]
        risiko = [c for c in [
            celle("Sharpe", f_t(n["sharpe"]), stor=False) if n["sharpe"] is not None else None,
            celle("Sortino", f_t(n["sortino"]), stor=False) if n["sortino"] is not None else None,
            celle("Calmar", f_t(n["calmar"]), stor=False) if n["calmar"] is not None else None,
            celle("Volatilitet", f_t(n["vol"], 1, " %"), stor=False) if n["vol"] is not None else None,
            celle("Max drawdown", f_t(n["mdd"], 2, " %"), rød, stor=False) if n["mdd"] is not None else None,
        ] if c]
        handel = [c for c in [
            celle("Handler", str(n["n_handler"]), stor=False) if n["n_handler"] is not None else None,
            celle("Lukkede", str(n["n_lukket"]), stor=False) if n["n_lukket"] is not None else None,
            celle("Treffrate", f_t(n["treffrate"], 1, " %"), "#1565c0", stor=False) if n["treffrate"] is not None else None,
            celle("Snitt handel", f_t(n["snitt_handel"], 2, " %", True),
                  grønn if (n["snitt_handel"] or 0) > 0 else rød, stor=False) if n["snitt_handel"] is not None else None,
            celle("Median handel", f_t(n["median_handel"], 2, " %", True),
                  grønn if (n["median_handel"] or 0) > 0 else rød, stor=False) if n["median_handel"] is not None else None,
        ] if c]
        ekstra = [c for c in [
            celle("Beste", f_t(n["beste"], 2, " %", True), grønn, stor=False) if n["beste"] is not None else None,
            celle("Verste", f_t(n["verste"], 2, " %", True), rød, stor=False) if n["verste"] is not None else None,
            celle("Snitt holdedager", f_t(n["holdedager"], 1), stor=False) if n["holdedager"] is not None else None,
            celle("Snitt investert", f_t(s.get("investert"), 1, " %"), stor=False) if s.get("investert") is not None else None,
            celle("Benchmark CAGR", f_t(n["benchmark_cagr"], 1, " %"), stor=False) if n["benchmark_cagr"] is not None else None,
            celle("Meravkastning", f_t(n["excess"], 1, " %", True),
                  grønn if (n["excess"] or 0) > 0 else rød, stor=False) if n["excess"] is not None else None,
        ] if c]

        under = []
        if n["exit_miks"]:
            under.append(f"<strong>Exit-fordeling:</strong> {n['exit_miks']}")
        if s.get("regime"):
            under.append(f"<strong>Regime:</strong> {s['regime']}")
        if s.get("risk_off") is not None:
            under.append(f"RISK_OFF {s['risk_off']:.0f} % av tiden")
        under_html = (f'<div style="font-size:11px;color:#666;padding:6px 8px 0;">'
                      f'{" &nbsp;·&nbsp; ".join(under)}</div>' if under else "")

        return f"""
<div style="background:#f8f9fa;border:1px solid #e0e0e0;border-radius:8px;padding:10px;margin:10px 0;">
    <table style="width:100%;border-collapse:collapse;">
        {metrikk_rad("Avkastning", avk)}
        {metrikk_rad("Risiko", risiko)}
        {metrikk_rad("Handel", handel)}
        {metrikk_rad("Ytterpunkter", ekstra)}
    </table>
    {under_html}
    <div style="text-align:right;font-size:10px;color:#aaa;margin-top:6px;">
        Periode: {n.get('periode') or '—'} · {s['kilde_note']}
    </div>
</div>
"""

    def bygg_advarsel(s: dict) -> str:
        """
        Tre grunner til forbehold, og de er ikke de samme.

        Få handler gjør Sharpe og treffrate til støy. Kort periode gjør
        ANNUALISERINGEN til en forstørrelse — 73 % på åtte måneder blir til
        «146,7 % i året» ved siden av tre år med 25,4 %. Og en strategi valgt
        blant mange uten å bestå en robusthetstest er ikke en strategi, den er
        den heldigste raden i tabellen. En strategi kan ha én av de tre feilene
        uten de andre, så alle tre skal kunne stå.
        """
        n = s["n"]
        n_lukket = n.get("n_lukket")
        n_ar = n.get("n_ar")
        for_faa = n_lukket is not None and n_lukket < MIN_HANDLER_FOR_MENING
        for_kort = (n_ar is not None and not pd.isna(n_ar)
                    and not n.get("cagr_meningsfull", True))
        ikke_robust = str(s.get("advarsel", "")).strip()
        data_advarsel = str(s.get("data_advarsel", "")).strip()
        if not (for_faa or for_kort or ikke_robust or data_advarsel):
            return ""

        if data_advarsel:
            tittel = "DATAGRUNNLAG — periode og ferskhet"
        elif ikke_robust:
            tittel = "ROBUSTHET — les utvalg og senere test"
        elif for_faa and for_kort:
            tittel = (f"TENTATIVT — {n_ar:.1f} år og {n_lukket} avsluttede handler")
        elif for_kort:
            tittel = f"TENTATIVT — bare {n_ar:.1f} år med data"
        else:
            tittel = f"TENTATIVT — {n_lukket} avsluttede handler"

        deler = [data_advarsel] if data_advarsel else []
        if ikke_robust:
            deler.append(ikke_robust)
        if for_kort:
            punkter = n.get("n_punkter")
            deler.append(
                f"CAGR er totalavkastningen opphøyd i 1/{n_ar:.2f} — en god "
                f"periode blir til et årstall den ikke har dekning for. Bruk "
                f"<strong>Total</strong>, ikke CAGR"
                + (f", og husk at kurven har {punkter} punkter" if punkter else "")
                + ". Max drawdown og Sharpe måles på de samme punktene, så de "
                  "er like tynne.")
        if for_faa:
            deler.append(
                f"Under {MIN_HANDLER_FOR_MENING} lukkede handler er Sharpe, "
                f"treffrate og snittavkastning støy, ikke edge. Bruk tallene "
                f"til å feilsøke logikken — ikke til å vurdere om strategien "
                f"virker.")
        return f"""
<div style="background:#fff3e0;border:1px solid #ffb74d;border-left:5px solid #e65100;
            border-radius:8px;padding:12px 14px;margin:10px 0;">
    <div style="font-size:13px;font-weight:700;color:#e65100;margin-bottom:3px;">
        {tittel}
    </div>
    <div style="font-size:12px;color:#5d4037;line-height:1.5;">
        {" ".join(deler)}
    </div>
</div>
"""

    # Kolonneoppsett per strategi: (overskrift, nøkkel, format)
    POS_KOLONNER = {
        "PB-ROE-Momentum": [
            ("#", "_i", "int"), ("Ticker", "ticker", "fet"), ("Selskap", "selskap", "tekst"),
            ("Rang", "rang", "int"), ("Score", "score", "t3"), ("P/B", "pb", "t2"),
            ("ROE", "roe", "t2"), ("Mom %", "momentum", "t1"), ("Bransje", "bransje", "tekst")],
        "NLP Sentiment — ledelse": [
            ("#", "_i", "int"), ("Ticker", "ticker", "fet"), ("Selskap", "selskap", "tekst")],
        "Sentiment Momentum v3.1": [
            ("#", "_i", "int"), ("Ticker", "ticker", "fet"), ("Selskap", "selskap", "tekst"),
            ("Antall", "antall", "nok"), ("Inngang", "inn_kurs", "t2"),
            ("Siste", "siste_kurs", "t2"), ("Avk.", "avk_pct", "farge1"),
            ("Kjøpt", "inn_dato_str", "tekst"), ("Dager", "dager", "int"),
            ("Composite", "composite", "t2f"), ("zDrift", "z_drift", "t2f"),
            ("Art.", "n_artikler", "int"), ("Vekt", "vekt", "t1p")],
    }

    def form(verdi, typ):
        if typ == "int":
            return str(int(verdi)) if isinstance(verdi, (int, float)) and pd.notna(verdi) else "—"
        if typ == "fet":
            return f"<strong>{verdi}</strong>"
        if typ == "tekst":
            return str(verdi) if verdi not in (None, "") and pd.notna(verdi) else "—"
        if typ == "nok":
            return f_n(verdi)
        if typ == "t1":
            return f_t(verdi, 1)
        if typ == "t2":
            return f_t(verdi, 2)
        if typ == "t3":
            return f_t(verdi, 3)
        if typ == "t2f":
            return f_t(verdi, 2, fortegn=True)
        if typ == "t1p":
            return f_t(verdi, 1, " %")
        if typ == "farge1":
            return f_c(verdi, 1)
        return str(verdi)

    def bygg_posisjoner(s: dict) -> str:
        if not s["posisjoner"]:
            merke = s.get("kontant")
            forklaring = (f" ({merke})" if merke and merke not in ("CASH", "") else "")
            return ('<p style="color:#999;font-style:italic;padding:10px 0;">'
                    f'Ingen åpne posisjoner — strategien står i kontanter{forklaring}.</p>')
        # Leseren kan sende med sitt eget oppsett når filen bærer mer enn
        # tickeren. Samme kort, to datagrunnlag: hendelsesmotoren vet hva som
        # utløste kjøpet, den månedlige gjør det ikke.
        kols = (s.get("pos_kolonner")
                or POS_KOLONNER.get(s["navn"],
                                    POS_KOLONNER["NLP Sentiment — ledelse"]))
        hoder = "".join(f"<th>{h}</th>" for h, _, _ in kols)
        rader, sum_na = "", 0.0
        for i, p in enumerate(s["posisjoner"], 1):
            if isinstance(p.get("verdi_na"), (int, float)):
                sum_na += p["verdi_na"]
            celler = ""
            for _, nokkel, typ in kols:
                v = i if nokkel == "_i" else p.get(nokkel)
                just = "left" if typ in ("fet", "tekst") else "right"
                celler += f'<td style="text-align:{just};">{form(v, typ)}</td>'
            rader += f"    <tr>{celler}</tr>\n"
        sum_rad = ""
        if sum_na > 0:
            sum_rad = (f'    <tr style="background:#e8f5e9;font-weight:bold;">'
                       f'<td colspan="{len(kols)}" style="text-align:right;">'
                       f'Verdi nå: {f_n(sum_na)} kr</td></tr>\n')
        return f"<table>\n    <tr>{hoder}</tr>\n{rader}{sum_rad}</table>\n"

    def bygg_handler(s: dict, antall: int = ANTALL_HANDLER) -> str:
        tr = s["handler"]
        if tr.empty:
            return ('<p style="color:#999;font-style:italic;padding:10px 0;">'
                    'Ingen handler i denne kjøringen.</p>')
        har_pnl = tr["PnL"].notna().any()
        siste = tr.sort_values("Dato").tail(antall).iloc[::-1]

        # Avkastning per salg rekonstrueres bare når loggen ikke har PnL.
        avk_kart = {}
        if not har_pnl:
            kjop = tr[tr["Handling"].isin(KJOP)]
            for idx, r in siste.iterrows():
                if r["Handling"] in SALG:
                    f = kjop[(kjop["Ticker"] == r["Ticker"]) &
                             (kjop["Dato"] < r["Dato"])].sort_values("Dato")
                    if not f.empty and float(f.iloc[-1]["Kurs"]) > 0:
                        avk_kart[idx] = (float(r["Kurs"]) / float(f.iloc[-1]["Kurs"]) - 1) * 100

        rader = ""
        for idx, r in siste.iterrows():
            er_kjop = r["Handling"] in KJOP
            farge = "#2e7d32" if er_kjop else "#c62828"
            merke = f'<span style="color:{farge};font-weight:700;">{r["Handling"]}</span>'
            if har_pnl and pd.notna(r["PnL"]):
                grunnlag = r["Antall"] * r["Kurs"] - r["PnL"]
                avk = r["PnL"] / grunnlag * 100 if grunnlag else None
            else:
                avk = avk_kart.get(idx)
            rader += f"""    <tr>
        <td>{r['Dato']:%Y-%m-%d}</td><td>{merke}</td>
        <td><strong>{r['Ticker']}</strong></td>
        <td style="text-align:right;">{f_n(r['Antall'], 0 if float(r['Antall'] or 0) >= 10 else 2)}</td>
        <td style="text-align:right;">{f_t(r['Kurs'])}</td>
        <td style="text-align:right;">{f_n(r['Beløp'])}</td>
        <td style="text-align:right;">{f_c(r['PnL'], 0, ' kr') if pd.notna(r['PnL']) else TOM}</td>
        <td style="text-align:right;">{f_c(avk, 1)}</td>
        <td style="text-align:right;">{int(r['Dager']) if pd.notna(r['Dager']) else '—'}</td>
        <td style="font-size:11px;color:#666;">{r['Årsak'] if pd.notna(r['Årsak']) else ''}</td>
    </tr>\n"""
        note = ""
        if not har_pnl:
            note = ('<p style="font-size:11px;color:#999;margin:6px 0 0;">'
                    'Loggen har ingen P&amp;L-kolonne. Avkastningen er målt mot siste '
                    'forutgående kjøp i samme ticker — en tilnærming, siden begge disse '
                    'strategiene rebalanserer i brøkdeler av aksjer, så et salg kan være '
                    'en nedvekting av en posisjon som fortsatt står.</p>')
        return f"""<table>
    <tr><th>Dato</th><th>Type</th><th>Ticker</th><th>Antall</th><th>Kurs</th>
        <th>Beløp</th><th>P&amp;L</th><th>Avk.</th><th>Dager</th><th>Merknad</th></tr>
{rader}</table>
{note}
"""

    def bygg_funnel(s: dict) -> str:
        if not s.get("funnel"):
            return ""
        rader, verst = s["funnel"]
        tr = "".join(f"""    <tr><td>{r['steg']}</td>
        <td style="text-align:right;">{r['snitt']:.2f}</td>
        <td style="text-align:right;">{r['dager']}</td>
        <td style="text-align:right;">{r['pct']:.1f} %</td></tr>\n""" for r in rader)
        verst_html = (f'<div style="font-size:12px;color:#e65100;font-weight:600;'
                      f'margin-top:8px;">{verst}</div>' if verst else "")
        return f"""
    <h3 style="margin:18px 0 2px;color:#1a237e;font-size:14px;">Signalfunnel</h3>
    <p class="sub">Hvor mange selskaper overlever hvert filtersteg, snitt per handelsdag.</p>
    <table>
        <tr><th>Steg</th><th>Snitt per dag</th><th>Dager &gt; 0</th><th>% av dager</th></tr>
{tr}    </table>
    {verst_html}
"""

    def bygg_hvordan(s: dict) -> str:
        """
        Hvordan strategien faktisk handler — signal, filtre, vekting, exit.

        Én linje med «lav P/B, høy ROE» sier hva den ser etter, ikke hvordan
        den oppfører seg. Skal du vurdere om en portefølje er rimelig, må du
        vite hva som utløser et kjøp OG hva som får den ut igjen.
        """
        rader = s.get("hvordan") or []
        if not rader:
            return ""
        celler = "".join(
            f'<tr><td style="width:96px;vertical-align:top;padding:5px 10px 5px 0;'
            f'font-weight:600;color:#1a237e;white-space:nowrap;">{lab}</td>'
            f'<td style="padding:5px 0;color:#444;line-height:1.55;">{tekst}</td></tr>'
            for lab, tekst in rader)
        return (f'<h3 style="margin:18px 0 2px;color:#1a237e;font-size:14px;">'
                f'Slik handler den</h3>'
                f'<table style="font-size:12.5px;margin-top:4px;">{celler}</table>')

    def bygg_strategikort(s: dict) -> str:
        if s["mangler"]:
            return f"""
<div class="card">
    <div class="tittel"><h2>{s['navn']}</h2>
        <span class="badge" style="background:#ffebee;color:#c62828;">ikke kjørt</span></div>
    <p class="sub">{s['beskrivelse']}</p>
    <div style="background:#fafafa;border:1px dashed #ccc;border-radius:6px;
                padding:14px;color:#777;font-size:12.5px;line-height:1.6;">
        {s['mangler']}
    </div>
</div>
"""
        return f"""
<div class="card">
    <div class="tittel"><h2>{s['navn']}</h2>
        <span class="badge">{len(s['posisjoner'])} posisjon{'er' if len(s['posisjoner']) != 1 else ''}</span></div>
    <p class="sub">{s['beskrivelse']} <span style="color:#aaa;">· {s['lager']}</span></p>
    {bygg_advarsel(s)}
    {bygg_nokkeltall(s)}
    {bygg_hvordan(s)}
    <h3 style="margin:18px 0 2px;color:#1a237e;font-size:14px;">Alle valgte aksjer</h3>
    {bygg_posisjoner(s)}
    <h3 style="margin:18px 0 2px;color:#1a237e;font-size:14px;">Siste {ANTALL_HANDLER} handler</h3>
    {bygg_handler(s)}
    {bygg_funnel(s)}
</div>
"""

    def bygg_overlapp(overlapp: Dict[str, List[str]]) -> str:
        if not overlapp:
            return """
<div class="card">
    <h2>Overlapp</h2>
    <div style="background:#e8f5e9;border:1px solid #a5d6a7;border-radius:8px;
                padding:14px;color:#2e7d32;font-size:13px;">
        Ingen aksjer går igjen i flere strategier. Full spredning.
    </div>
</div>
"""
        kort = ""
        for t, navn in sorted(overlapp.items(), key=lambda x: -len(x[1])):
            kort += f"""
    <div style="background:linear-gradient(135deg,#fff8e1 0%,#fff3e0 100%);
                border:1px solid #ffcc02;border-radius:8px;padding:13px;margin:9px 0;">
        <span style="font-size:17px;font-weight:bold;color:#e65100;">{t}</span>
        <span style="background:#ff6f00;color:#fff;padding:2px 8px;border-radius:10px;
                     font-size:11px;font-weight:bold;margin-left:8px;">{len(navn)} strategier</span>
        <div style="color:#555;font-size:12.5px;margin-top:5px;">{" &bull; ".join(navn)}</div>
    </div>
"""
        return f"""
<div class="card">
    <h2>Overlapp</h2>
    <p class="sub">Aksjer som går igjen i flere strategier. Høyere overbevisning —
       men også konsentrert risiko, siden posisjonene ikke er uavhengige.</p>
{kort}
</div>
"""

    def bygg_datagrunnlag(strategier: List[dict], sent_fil) -> str:
        rader = ""
        for s in strategier:
            rader += (f'<tr><td colspan="3" style="padding:10px 0 3px;font-weight:600;'
                      f'color:#1a237e;font-size:12px;">{s["navn"]}</td></tr>')
            for label, p in s["kilder"]:
                rader += (f'<tr><td style="padding:3px 10px 3px 14px;color:#666;">{label}</td>'
                          f'<td style="padding:3px 10px 3px 0;font-family:monospace;'
                          f'font-size:11px;">{p.name if p else "— ikke skrevet —"}</td>'
                          f'<td class="{ferskhet(p)}" style="padding:3px 0;font-size:11px;">'
                          f'{filalder(p)}</td></tr>')
        if sent_fil is not None:
            rader += (f'<tr><td colspan="3" style="padding:10px 0 3px;font-weight:600;'
                      f'color:#1a237e;font-size:12px;">Felles</td></tr>'
                      f'<tr><td style="padding:3px 10px 3px 14px;color:#666;">Sentiment</td>'
                      f'<td style="padding:3px 10px 3px 0;font-family:monospace;'
                      f'font-size:11px;">{sent_fil.name}</td>'
                      f'<td class="{ferskhet(sent_fil)}" style="padding:3px 0;font-size:11px;">'
                      f'{filalder(sent_fil)}</td></tr>')
        return f"""
<div class="card">
    <h2>Datagrunnlag</h2>
    <p class="sub">Hver eneste kilde med filnavn og alder. Grønn = i dag,
       oransje = under fire dager, rød = eldre.</p>
    <table style="font-size:12px;">{rader}</table>
</div>
"""

    # Stilen ligger som en mal med et {p}-prefiks foran hver selektor. Grunnen
    # er at master.py limer seksjonene inn i SIN mail, som har sin egen .sub og
    # sine egne tabeller. Uten prefiks ville den siste <style>-blokken vinne, og
    # to sett regler ville dratt i hverandres tabeller. Med prefiks gjelder
    # reglene her bare inne i <div class="strategier">.
    STIL_MAL = """
{p}.card {{ background:#fff; padding:22px 25px; border-bottom:1px solid #e8e8e8; }}
{p}.card:last-of-type {{ border-bottom:none; border-radius:0 0 12px 12px; }}
{p}.card h2 {{ margin:0 0 4px; color:#1a237e; font-size:17px; }}
{p}.tittel {{ display:flex; align-items:center; gap:10px; }}
{p}.badge {{ background:#e8eaf6; color:#283593; padding:3px 10px; border-radius:12px; font-size:11px; font-weight:600; }}
{p}p.sub {{ color:#666; font-size:12px; margin:0 0 10px; }}
{p}table {{ border-collapse:collapse; width:100%; margin-top:8px; font-size:12.5px; }}
{p}th {{ background:#f5f5f5; color:#333; padding:9px 10px; text-align:left; font-weight:600; border-bottom:2px solid #e0e0e0; white-space:nowrap; }}
{p}td {{ padding:7px 10px; border-bottom:1px solid #f0f0f0; }}
{p}.fresh {{ color:#2e7d32; font-weight:600; }}
{p}.moderate {{ color:#e65100; font-weight:600; }}
{p}.stale {{ color:#c62828; font-weight:600; }}
"""

    def stil(prefiks: str = "") -> str:
        """CSS-en, enten frittstående («») eller scopet («.strategier »)."""
        return STIL_MAL.replace("{{", "\x00").replace("}}", "\x01") \
                       .replace("{p}", prefiks) \
                       .replace("\x00", "{").replace("\x01", "}")

    def bygg_seksjoner(strategier: List[dict], overlapp, sent_fil) -> str:
        """Bare kortene — det master.py limer inn i sin egen mail."""
        return (bygg_sammenligning(strategier)
                + "".join(bygg_strategikort(s) for s in strategier)
                + bygg_overlapp(overlapp)
                + bygg_datagrunnlag(strategier, sent_fil))

    def bygg_mail(strategier: List[dict], overlapp, sent_fil) -> str:
        na = datetime.now().strftime("%Y-%m-%d %H:%M")
        aktive = [s for s in strategier if s["mangler"] is None]
        n_pos = sum(len(s["posisjoner"]) for s in aktive)
        n_unike = len({norm_ticker(p["ticker"]) for s in aktive
                       for p in s["posisjoner"] if norm_ticker(p.get("ticker"))})

        return f"""<html><head><style>
body {{ font-family:'Segoe UI',Arial,sans-serif; margin:0; padding:20px; background:#f0f2f5; color:#222; }}
.container {{ max-width:1060px; margin:0 auto; }}
.header {{ background:linear-gradient(135deg,#1a237e 0%,#283593 100%); color:#fff; padding:28px 30px; border-radius:12px 12px 0 0; }}
.header h1 {{ margin:0; font-size:22px; }}
.header p {{ margin:6px 0 0; opacity:.85; font-size:13px; }}
{stil()}
tr:hover {{ background:#fafafa; }}
.footer {{ text-align:center; color:#999; font-size:11px; padding:18px 0; }}
</style></head><body><div class="container">

<div class="header">
    <h1>Strategisammendrag — tentative resultater</h1>
    <p>{len(aktive)} av {len(strategier)} strategier har kjørt · bygget {na}</p>
</div>

{bygg_seksjoner(strategier, overlapp, sent_fil)}

<div class="footer">
    <p>{n_pos} posisjoner totalt ({n_unike} unike aksjer) på tvers av {len(aktive)} strategier</p>
    <p>Alt over er backtester, ikke live porteføljer — {datetime.now():%Y-%m-%d %H:%M:%S}</p>
</div>

</div></body></html>"""

    # ══════════════════════════════════════════════════════════════════════════
    # SENDING
    # ══════════════════════════════════════════════════════════════════════════
    def send_mail(html: str, emne: str) -> bool:
        if not EMAIL_PASSWORD:
            print("\n  App-passordet er tomt. Mailen ble IKKE sendt.")
            print("  Fyll inn EMAIL_PASSWORD i INNSTILLINGER, eller sett")
            print('     setx AKSJE_MAIL_APP_PASSWORD "xxxx xxxx xxxx xxxx"')
            return False
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = emne
            msg["From"] = EMAIL_USER
            msg["To"] = ", ".join(EMAIL_RECIPIENTS)
            msg.attach(MIMEText(html, "html", "utf-8"))
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
                server.starttls()
                server.login(EMAIL_USER, EMAIL_PASSWORD)
                server.send_message(msg)
            print(f"\n  Mail sendt til {len(EMAIL_RECIPIENTS)} mottaker(e).")
            print(f"  Emne: {emne}")
            return True
        except Exception as e:
            print(f"\n  Sending feilet: {e}")
            import traceback
            traceback.print_exc()
            return False

    # ══════════════════════════════════════════════════════════════════════════
    # HOVEDLØP
    # ══════════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 74)
    print("  STRATEGISAMMENDRAG — ALLE TRE STRATEGIER")
    print("=" * 74)
    print(f"\n  Datamappe: {BASE_DIR}")

    strategier = []
    for navn, leser in (("PB-ROE-Momentum", les_pbroe),
                        ("NLP Sentiment — ledelse", les_sentiment_mgmt),
                        ("Sentiment Momentum v3.1", les_sentmom31)):
        print(f"\n  {navn}")
        try:
            s = leser()
        except Exception as e:
            print(f"    feilet: {e}")
            s = {"navn": navn, "beskrivelse": "", "lager": "", "kilder": [],
                 "n": tom_metrikk(), "posisjoner": [], "handler": pd.DataFrame(),
                 "funnel": None, "kilde_note": "", "sharpe_harm": None,
                 "frekvens": "—", "mangler": f"Lesing feilet: {e}"}
        if s["mangler"]:
            print(f"    {s['mangler']}")
        else:
            n = s["n"]
            # Samme forbehold i konsollen som i mailen. Leser du bare loggen,
            # skal du ikke få et penere tall enn den som leser mailen.
            kort = ("" if n.get("cagr_meningsfull", True)
                    else f"  ⚠ bare {n.get('n_ar') or 0:.1f} år — bruk Total "
                         f"({f_t(n['total'], 1)} %)")
            print(f"    CAGR {f_t(n['cagr'], 2)} % | Sharpe {f_t(n['sharpe'])} "
                  f"(harm. {f_t(s['sharpe_harm'])}) | MaxDD {f_t(n['mdd'], 2)} % | "
                  f"{n['n_lukket']} lukkede | {len(s['posisjoner'])} åpne{kort}"
                  .replace('<span style="color:#bbb;">—</span>', "—"))
        strategier.append(s)

    aktive = [s for s in strategier if s["mangler"] is None]
    if not aktive:
        print("\n  Ingen av de tre strategiene har skrevet resultatfiler.")
        print("  Kjør minst én av dem først.\n")
        return None

    overlapp = finn_overlapp(aktive)
    if overlapp:
        print(f"\n  Overlapp: {len(overlapp)} aksje(r) i flere strategier")
        for t, navn in sorted(overlapp.items(), key=lambda x: -len(x[1])):
            print(f"    {t} → {', '.join(navn)}")
    else:
        print("\n  Ingen overlapp mellom strategiene.")

    sent_fil = nyeste(SENTIMENT_DIR, "Step4_Sentiment_Changes_*.xlsx")
    html = bygg_mail(strategier, overlapp, sent_fil)

    HTML_KOPI_DIR.mkdir(parents=True, exist_ok=True)
    kopi = HTML_KOPI_DIR / f"Strategier_Mail_{datetime.now():%Y%m%d_%H%M%S}.html"
    kopi.write_text(html, encoding="utf-8")
    print(f"\n  HTML-kopi: {kopi}")

    n_pos = sum(len(s["posisjoner"]) for s in aktive)
    emne = (f"[TENTATIV] Strategisammendrag — {len(aktive)}/3 strategier | "
            f"{n_pos} posisjoner"
            + (f" | {len(overlapp)} overlapp" if overlapp else "")
            + f" — {datetime.now():%Y-%m-%d}")

    if send:
        send_mail(html, emne)
    else:
        print("\n  Bygget, ikke sendt — master.py er eneste avsender.")
        print("  Vil du sende akkurat denne alene: MailAlleStrategier(send=True)")

    if open_in_browser:
        webbrowser.open(kopi.as_uri())

    print("\n" + "=" * 74)
    print("  FERDIG")
    print("=" * 74 + "\n")

    if returner_html:
        # Master bygger sitt eget sammendrag på tvers av FIRE strategier —
        # innsidehandelen kommer fra pipelinen og er ikke med her. Derfor
        # leverer vi rådataene ved siden av den ferdige HTML-en: master kan
        # ikke lage en sammenligningstabell av en ferdig tabell.
        return {
            "sti": kopi,
            "seksjoner": bygg_seksjoner(strategier, overlapp, sent_fil),
            "kort": {s["navn"]: bygg_strategikort(s) for s in strategier},
            "strategier": strategier,
            "stil": stil(".strategier "),
            "emne": emne,
            "n_aktive": len(aktive),
            "n_strategier": len(strategier),
            "n_posisjoner": n_pos,
            "overlapp": overlapp,
            "overlapp_html": bygg_overlapp(overlapp),
            "datagrunnlag_html": bygg_datagrunnlag(strategier, sent_fil),
        }
    return kopi


# ══════════════════════════════════════════════════════════════════════════════
#  SLUTT PÅ FUNKSJONEN
#
#  Alt under denne linjen gjelder BARE når filen kjøres som eget script.
#  Limer du funksjonen inn i Only_260818.py: stopp her, ikke ta med resten.
#  Skriv i stedet nederst i filen, slik du gjør med FullMailScript7():
#
#      MailAlleStrategier()
#
#  Normalt trenger du ikke kjøre denne i det hele tatt: master.py henter
#  seksjonene herfra og sender dem i sin egen mail.
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from runtime_config import configure_console
    configure_console()
    import argparse
    from pathlib import Path

    p = argparse.ArgumentParser(
        description="Bygger tentative resultater for alle tre strategiene. "
                    "Sender ikke med mindre du ber om det — master.py er "
                    "eneste avsender.")
    p.add_argument("--send", action="store_true",
                   help="send denne mailen alene (gir to mailer om master "
                        "også kjører)")
    p.add_argument("--apne", action="store_true", help="åpne HTML-kopien lokalt")
    p.add_argument("--base-dir", type=Path, default=None, help="overstyr ExcelData-mappen")
    a = p.parse_args()

    MailAlleStrategier(send=a.send, open_in_browser=a.apne, base_dir=a.base_dir)
