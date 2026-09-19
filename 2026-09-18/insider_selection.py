"""Training-only robustness selection and an honest historical top-three ranking.

The rules below are fixed heuristics, not a claim that a moat has been proved.
They compare the five existing strategies without changing their definitions.
No fetching, mail, or file writes occur on import.
"""
from __future__ import annotations

import copy
import json
import math
import os
from datetime import date
from pathlib import Path

POLICY_VERSION = "insider-robustness-v1"
BASELINE = "daglig"
MODERATE_ONE_WAY_PCT = 0.15
STRESS_ONE_WAY_PCT = 0.80
MIN_TRAIN_DAYS = 252
MIN_ENTRIES = 20
MIN_TICKERS = 5


def _number(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (ValueError, TypeError):
        return None


def _cagr(rows):
    if len(rows) < 2:
        return None
    days = (date.fromisoformat(str(rows[-1]["Dato"])[:10])
            - date.fromisoformat(str(rows[0]["Dato"])[:10])).days
    first, last = float(rows[0]["Verdi_NOK"]), float(rows[-1]["Verdi_NOK"])
    if days <= 0 or first <= 0 or last < 0:
        return None
    return 100.0 * ((last / first) ** (365.25 / days) - 1.0)


def _split(curve, cutoff):
    train = [r for r in curve if str(r["Dato"])[:10] <= cutoff]
    test = train[-1:] + [r for r in curve if str(r["Dato"])[:10] > cutoff]
    midpoint = len(train) // 2
    # Shared boundary includes every return exactly once between the halves.
    first = train[:midpoint + 1]
    second = train[midpoint:]
    return train, test, first, second


def _entry_counts(trades, cutoff):
    active, tickers, entries = set(), set(), 0
    for h in sorted(trades, key=lambda r: str(r.get("Dato", ""))):
        if str(h.get("Dato", ""))[:10] > cutoff:
            continue
        ticker, kind = str(h.get("Ticker", "")), h.get("Type")
        if kind in ("SELG", "UTLØPT", "STOPP", "NEDSKREVET"):
            active.discard(ticker)
        elif kind == "KJØP" and ticker:
            tickers.add(ticker)
            if ticker not in active:
                entries += 1
                active.add(ticker)
    return entries, len(tickers)


def select_robust_variant(rows, baseline=BASELINE):
    """Pure selector. Neither full-history nor heldout columns are read here."""
    base = next((r for r in rows if r["Variant"] == baseline), None)
    if base is None:
        raise ValueError("Baseline insider variant is missing; cannot select safely.")
    eligible = []
    for row in rows:
        moderate = _number(row.get("Train_Moderate_CAGR_Pst"))
        worst = _number(row.get("Train_Stress_Worst_Half_CAGR_Pst"))
        turnover = _number(row.get("Train_Turnover_Per_Year_Pst"))
        if (int(row.get("Train_Days", 0)) >= MIN_TRAIN_DAYS
                and int(row.get("Train_Entries", 0)) >= MIN_ENTRIES
                and int(row.get("Train_Tickers", 0)) >= MIN_TICKERS
                and moderate is not None and moderate > 0
                and worst is not None and turnover is not None):
            eligible.append(row)
    if not eligible:
        return base, ("Daglig baseline beholdes: ingen variant har både tilstrekkelig "
                      "treningshistorikk og positiv treningsavkastning ved 0,15 % "
                      "kostnad per handelsside. Dette dokumenterer ingen varig fordel.")
    # Input order is the predefined VARIANTER order; used only for exact ties.
    order = {row["Variant"]: n for n, row in enumerate(rows)}
    selected = min(eligible, key=lambda row: (
        -float(row["Train_Stress_Worst_Half_CAGR_Pst"]),
        float(row["Train_Turnover_Per_Year_Pst"]), order[row["Variant"]]))
    reason = ("Valgt på tidligere treningsdata: høyest CAGR i den svakeste av "
              "to treningshalvdeler etter 0,80 % kostnad per handelsside, blant "
              "varianter med positiv samlet trenings-CAGR ved 0,15 %. Ved likhet "
              "vinner lavere treningsomsetning, deretter fast variantrekkefølge. "
              "Fullhistorikk og senere testresultater påvirker ikke valget.")
    if float(selected["Train_Stress_Worst_Half_CAGR_Pst"]) <= 0:
        reason += (" Den valgte varianten taper i minst én treningshalvdel under "
                   "kostnadsstress: ingen nettofordel er dokumentert under dette stresset.")
    return selected, reason


def resolve_choice(rows, manual=""):
    """An explicit override stays visible and never masquerades as the model choice."""
    recommended, reason = select_robust_variant(rows)
    manual = str(manual or "").strip()
    if not manual:
        return recommended, reason, recommended["Variant"], False
    selected = next((row for row in rows if row["Variant"] == manual), None)
    if selected is None:
        raise ValueError("Unknown AKSJE_INNSIDE_VALG variant: " + manual)
    reason = (f"Manuelt valg: {manual}. Den automatiske robusthetsregelen anbefalte "
              f"{recommended['Variant']}; det manuelle valget er ikke resultat av "
              "denne regelen og dokumenterer ingen MOAT. "
              "Sammenligningen og kostnadsstresset vises fortsatt uendret.")
    if (_number(selected.get("Train_Stress_Worst_Half_CAGR_Pst")) is None
            or float(selected["Train_Stress_Worst_Half_CAGR_Pst"]) <= 0):
        reason += " Ingen positiv nettofordel er dokumentert i begge treningshalvdeler under kostnadsstress."
    return selected, reason, recommended["Variant"], True


def strategy_rules(strategy, opp):
    """Describe actual engine rules, including its event-strategy refill rule."""
    maximum = strategy.maks_navn or opp.maks_navn
    minimum = strategy.min_navn or opp.min_navn_portefolje
    window = strategy.vindu_dager or opp.signal_vindu_dager
    threshold = opp.min_score_portefolje if strategy.min_score < 0 else strategy.min_score
    liquidity = opp.min_omsetning_nok if strategy.min_omsetning < 0 else strategy.min_omsetning
    cluster = "Bare første melding i hver klynge." if opp.kun_primaer else "Alle kjente meldinger i klyngen."
    ranking = (f"Høyeste gyldige score per ticker fra signaler yngre enn {window} "
               f"kalenderdager; score ≥ {threshold:g}, tidligere gjennomsnittlig "
               f"dagsomsetning ≥ {liquidity:,.0f} NOK. Topp {maximum}, ticker bryter likhet.")
    if strategy.halveringstid:
        ranking += (f" Før rangering: score × 0,5^(børsdager siden signal/{strategy.halveringstid}); "
                    "grensen gjelder den reduserte scoren. Halveringen bruker børsdager.")
    weighting = ("Vekt proporsjonal med max(1, score − 50)." if strategy.vekting == "score"
                 else "Lik vekt mellom valgte aksjer.")
    weighting += (f" Høyst {maximum} navn; færre enn {minimum} kvalifiserte navn gir "
                  f"100 % kontanter. Tak {100 / minimum:g} % per navn ved rebalansering."
                  if minimum > 0 else f" Høyst {maximum} navn; ingen minstegrense.")
    if strategy.vekting == "score" and minimum > 0:
        weighting += " Vekt som kuttes av taket blir kontanter; den fordeles ikke på nytt."
    entry = (f"Kjøp til sluttkurs på Handelsdag_0: meldinger før {opp.stengetid} Oslo-tid kan "
             f"handles samme børsdag; etter {opp.stengetid} eller uten klokkeslett tidligst neste "
             "børsdag. Ingen avkastning før inngangskursen tilskrives signalet.")
    if strategy.hold_dager:
        exit_rule = (f"Selg ved {strategy.hold_dager} børsdager siden første inngang. "
                     "Behold øvrige posisjoner; legg til nye kvalifiserte signaler. "
                     f"Hvis færre enn {minimum} navn: fyll med eldre fortsatt gyldige "
                     "signaler, ellers selg alt. Et utløpt navn kan derfor kjøpes igjen "
                     "samme dag ved slik etterfylling. Rebalanser ved endret navnesett "
                     "eller exit, ikke ved hver prisendring. Vekter kan drive over taket mellom handler.")
    else:
        exit_rule = ("Vurder og rebalanser hver børsdag, også når navnesettet er uendret. "
                     "Selg når signalet utløper, redusert score faller under grensen, "
                     "navnet faller utenfor topplisten, eller porteføljen har for få navn.")
    exit_rule += " Ingen stop-loss i disse fem variantene. Manglende pris utover tillatt fyll skrives ned til null."
    return {
        "Signal": ("Meldepliktige kjøp med høy/middels tolkingstillit; kjent beløp minst "
                   f"{opp.min_verdi_nok:,.0f} NOK (ukjent beløp beholdes). " + cluster
                   + " Score bygger på rolle, beholdningsøkning, beløp og kun samtidige/tidligere kjente kjøp."),
        "Entry": entry, "Ranking": ranking, "Weighting": weighting, "Exit": exit_rule,
        "Structural_Rationale": {
            "daglig": "Enkel respons på offentlig kjent innsideinformasjon; ingen ekstra forfallsparameter, men hyppige handler.",
            "hendelse-20": "Fast holdeperiode kan redusere unødvendige daglige omvektinger, men etterfylling og gjenkjøp påvirker faktisk holdetid.",
            "forfall-60": "Ferske signaler prioriteres og lik vekting begrenser avhengighet av presis scorekalibrering.",
            "scorevektet": "Mer kapital til sterkere signaler, med posisjonstak; avhenger av at styrken i scoren betyr noe og tåler kostnader.",
            "konsentrert": "Færre navn øker eksponering mot topprangerte signaler, men også enkeltselskapsrisiko og utskifting."
        }.get(strategy.navn, strategy.hvorfor),
    }


def variant_rules(name, opp):
    """Stable mail API: Norwegian (label, exact rule) pairs for any variant."""
    import innsidehandel_pipeline as ip
    strategy = next((st for st in ip.VARIANTER if st.navn == name), None)
    if strategy is None:
        raise ValueError("Unknown insider variant: " + str(name))
    rules = strategy_rules(strategy, opp)
    labels = {"Signal": "Signal", "Entry": "Inngang", "Ranking": "Rangering",
              "Weighting": "Vekting", "Exit": "Utgang", "Structural_Rationale": "Mulig strukturell fordel"}
    return [(labels[key], text) for key, text in rules.items()]


def build_insider_selection(opp, logger=None, *, market=None, stats=None,
                            curves=None, trades=None, write=True):
    """Replay cached inputs only; return selected_variant/top3/rules/rationale.

    Step 6 supplies its already calculated full-history results. Calling this
    directly replays them from local merged events and price files. Cost stress
    changes spread/commission only, never the five strategy definitions.
    """
    import innsidehandel_pipeline as ip
    cutoff = str(opp.inn_utvalg_slutt)
    date.fromisoformat(cutoff)
    logger = logger or ip.stillelogger()
    if market is None:
        events = ip.les_csv(opp.merget_csv)
        market = ip.Marked(ip.velg(events, opp, "KJOP", krev_kurs=False), opp)
    if not market:
        raise ValueError("Insufficient local insider events/prices for robust comparison.")
    stats = list(stats or [])
    curves = dict(curves or {})
    trades = list(trades or [])
    for strategy in ip.VARIANTER:
        if strategy.navn in curves:
            continue
        curve, history, written_down, _ = ip.kjor_strategi(market, strategy, opp)
        curves[strategy.navn] = curve
        trades.extend(dict(h, Strategi=strategy.navn) for h in history)
        m = ip.nokkeltall([float(r["Verdi_NOK"]) for r in curve], opp.risikofri_pst)
        stats.append({"Strategi": strategy.navn, "Hvorfor": strategy.hvorfor,
                      "CAGR_Pst": _number(m.get("CAGR", 0) * 100),
                      "Sharpe": _number(m.get("Sharpe")),
                      "MaxDD_Pst": _number(m.get("MaxDD", 0) * 100),
                      "Handler": len(history), "Nedskrevet": written_down})
    comparison = []
    full_stats = {row["Strategi"]: row for row in stats}
    for strategy in ip.VARIANTER:
        name = strategy.navn
        curve = curves[name]
        train, test, first, second = _split(curve, cutoff)
        own_trades = [h for h in trades if h.get("Strategi") == name]
        entries, tickers = _entry_counts(own_trades, cutoff)
        train_trades = [h for h in own_trades if str(h.get("Dato", ""))[:10] <= cutoff]
        turnover = sum(float(h.get("Verdi_NOK") or 0) for h in train_trades)
        mean_capital = sum(float(r["Verdi_NOK"]) for r in train) / max(1, len(train))
        years = ((date.fromisoformat(str(train[-1]["Dato"])[:10])
                  - date.fromisoformat(str(train[0]["Dato"])[:10])).days / 365.25) if len(train) > 1 else 0
        row = {"Variant": name, "Train_Entries": entries, "Train_Tickers": tickers,
               "Train_Trades": len(train_trades), "Train_Days": len(train),
               "Test_Days": max(0, len(test) - 1), "Selection_Cutoff": cutoff,
               "Train_CAGR_Pst": _cagr(train), "Test_CAGR_Pst": _cagr(test),
               "Full_CAGR_Pst": _number(full_stats[name].get("CAGR_Pst")),
               "Full_Calendar_CAGR_Pst": _cagr(curve),
               "Train_Turnover_Per_Year_Pst": 100 * turnover / mean_capital / years
               if mean_capital > 0 and years > 0 else None}
        for label, cost in (("Moderate", MODERATE_ONE_WAY_PCT), ("Stress", STRESS_ONE_WAY_PCT)):
            cost_opp = copy.copy(opp)
            # 0.80% = half of 1.5% spread + 0.05% commission per side.
            cost_opp.spread_pst, cost_opp.kurtasje_pst = 2 * cost, 0.0
            stress_curve, _, _, _ = ip.kjor_strategi(market, strategy, cost_opp)
            train_c, test_c, first_c, second_c = _split(stress_curve, cutoff)
            row[f"Train_{label}_CAGR_Pst"] = _cagr(train_c)
            row[f"Test_{label}_CAGR_Pst"] = _cagr(test_c)
            if label == "Stress":
                halves = [_cagr(first_c), _cagr(second_c)]
                row["Train_Stress_First_Half_CAGR_Pst"], row["Train_Stress_Second_Half_CAGR_Pst"] = halves
                row["Train_Stress_Worst_Half_CAGR_Pst"] = min(halves) if all(v is not None for v in halves) else None
        comparison.append(row)
    selected, reason, recommendation, manual_override = resolve_choice(
        comparison, os.environ.get("AKSJE_INNSIDE_VALG", ""))
    for row in comparison:
        row["Selected"] = row["Variant"] == selected["Variant"]
        row["Baseline"] = row["Variant"] == BASELINE
    exact_rules = {st.navn: strategy_rules(st, opp) for st in ip.VARIANTER}
    by_name = {r["Variant"]: r for r in comparison}
    ranked = sorted((r for r in stats if _number(r.get("CAGR_Pst")) is not None),
                    key=lambda r: (-float(r["CAGR_Pst"]), str(r["Strategi"])))[:3]
    top3 = [dict(row, **{k: v for k, v in by_name[row["Strategi"]].items()
                        if k not in row}, rules=exact_rules[row["Strategi"]], rank=n)
            for n, row in enumerate(ranked, 1)]
    result = {
        "policy_version": POLICY_VERSION, "selected_variant": selected["Variant"],
        "selected": dict(selected, Reason=reason, Baseline=BASELINE,
                         Manual_Override=manual_override, Robust_Recommendation=recommendation),
        "top3": top3, "rules": exact_rules, "rationale": reason,
        "comparison": comparison, "selection_cutoff": cutoff,
        "training_start": next((r["Dato"] for r in curves[BASELINE] if r["Dato"] <= cutoff), None),
        "test_start": next((r["Dato"] for r in curves[BASELINE] if r["Dato"] > cutoff), None),
        "period_end": curves[BASELINE][-1]["Dato"] if curves[BASELINE] else None,
        "policy": {
            "minimum_training_days": MIN_TRAIN_DAYS, "minimum_new_entries": MIN_ENTRIES,
            "minimum_tickers": MIN_TICKERS, "moderate_cost_per_side_pct": MODERATE_ONE_WAY_PCT,
            "stress_cost_per_side_pct": STRESS_ONE_WAY_PCT,
            "objective": "Highest worst-half training CAGR under stress; lower turnover breaks ties.",
            "eligibility": "Positive full-training CAGR at moderate cost; minimum history/breadth met.",
            "annualization": "Full table retains the engine's 252-trading-day convention. Training/test and cost stress use actual calendar dates (365.25 days/year).",
        },
        "ranking_note": "Topp 3 rangeres på hele historikkens CAGR kun for sammenligning; denne rangeringen velger ikke porteføljekomponenten.",
        "limitations": [
            "En forhåndsdefinert robusthetsheuristikk er ikke bevis for MOAT eller fremtidig meravkastning.",
            "Senere testdata er holdt utenfor dette valget, men eksisterende varianter var tidligere utviklet på deler av samme historikk; testen er ikke uberørt forskning.",
            "Kostnadsstress modellerer prosentkostnader, ikke ordrebok, markedspåvirkning eller garantert utførelse.",
            "Fullhistorisk kurve for den valgte varianten er tilbakeberegnet; et historisk porteføljeresultat basert på dette valget må begynne etter treningsslutt.",
        ],
    }
    result["selected"].update({"Policy_Version": POLICY_VERSION, "top3": top3,
                               "rules": exact_rules[selected["Variant"]],
                               "policy": result["policy"], "limitations": result["limitations"],
                               "ranking_note": result["ranking_note"]})
    if write:
        folder = Path(opp.s6_dir)
        folder.mkdir(parents=True, exist_ok=True)
        ip.skriv_csv(folder / "variant_comparison.csv", comparison)
        for filename, data in (("selected_variant.json", result["selected"]),
                               ("insider_selection.json", result)):
            ip.skriv_atomisk(folder / filename,
                            lambda path, data=data: path.write_text(json.dumps(data, ensure_ascii=False,
                                                                              indent=2, allow_nan=False), encoding="utf-8"))
    logger.info("Insider robust choice: %s. %s", result["selected_variant"], reason)
    return result
