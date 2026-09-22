# -*- coding: utf-8 -*-
"""
Vaktposter for masterkoden: fire modeller slått sammen til én score.

Den viktigste testen er den siste. Å slå sammen fire scorer er lett å gjøre
slik at fasiten lekker inn — en persentil regnet mot hele historikken vet i
2019 hvordan 2025 ble. Da måler backtesten sin egen fasit, og alt over den
er verdiløst uansett hvor pent det ser ut.
"""

from __future__ import annotations

import os
import random
import sys
import tempfile
import time
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import innsidehandel_pipeline as IP
import master as M
import test_pipeline as TP


def _marked(mappe: Path, effekt_pst: float = 0.0, fro: int = 5):
    """Et syntetisk marked med kurser, kalender og innsidehendelser."""
    rnd = random.Random(fro)
    opp = IP.Oppsett(base_dir=mappe, inn_utvalg_slutt="2021-12-31",
                     min_omsetning_nok=0.0, min_score_portefolje=0.0)
    opp.lag_mapper()
    kal = [d for d in (date(2019, 1, 1) + timedelta(days=k) for k in range(1200))
           if d.weekday() < 5]
    tickere = [f"T{i:02d}.OL" for i in range(14)]
    hendelser = [(rnd.choice(tickere), kal[rnd.randrange(40, len(kal) - 90)],
                  rnd.uniform(30, 95)) for _ in range(150)]
    løft = {}
    for t, d, _ in hendelser:
        for k in range(1, 21):
            løft[(t, d + timedelta(days=k))] = 1

    bok = IP.Kursbok(opp.s4_dir)
    for t in tickere + ["OSEBX.OL"]:
        kurs, serie = 100.0, {}
        for d in kal:
            kurs *= 1.0 + rnd.gauss(0.0002, 0.015)
            if t != "OSEBX.OL" and løft.get((t, d)):
                kurs *= 1.0 + effekt_pst / 100.0 / 20.0
            serie[d] = {"close": round(kurs, 4), "adjclose": round(kurs, 4),
                        "volum": 100_000.0 * rnd.uniform(0.5, 2.0)}
        bok.slå_sammen(t, serie)
        bok.lagre_ticker(t)
    IP.skriv_referansevalg(opp, "OSEBX.OL", "indeks")
    IP.skriv_csv(opp.hendelser_csv, [
        {"Melding_ID": f"E{i}", "Dato": IP.iso(d), "Klokkeslett": "09:00",
         "Selskap": t, "Ticker": t, "Klasse": "KJOP", "Tillit": "HOY",
         "Bullish_Score": round(sc, 1), "Primaer_I_Klynge": "JA",
         "Verdi_NOK": 250_000, "Rolle": "CEO"}
        for i, (t, d, sc) in enumerate(hendelser)], IP.HENDELSE_KOLONNER)
    IP.steg5_merge(opp, IP.stillelogger())
    return opp, tickere


def _excel(mappe: Path, kal, tickere, fro: int = 1) -> Path:
    """Oppdiktede resultatfiler fra de tre andre modellene."""
    rnd = random.Random(fro)
    bare = [t[:-3] for t in tickere]
    maaneder = sorted({(d.year, d.month): d for d in kal}.values())

    def logg(f):
        r = random.Random(f)
        return [{"date": IP.iso(d), "ticker": t, "score": round(r.uniform(0.2, 0.9), 4),
                 "rank": i, "valgt": "JA" if i <= 5 else "NEI"}
                for d in maaneder
                for i, t in enumerate(r.sample(bare, 8), start=1)]

    (mappe / "DataPB_ROE" / "Backtest").mkdir(parents=True, exist_ok=True)
    IP.skriv_xlsx(mappe / "DataPB_ROE" / "Backtest" / "BT_v3_Enhanced_2026-01-01.xlsx",
                  logg(fro), ["date", "ticker", "score", "rank", "valgt"],
                  arknavn="Score_Log")
    (mappe / "StrategyResults_v4_Sentiment").mkdir(parents=True, exist_ok=True)
    IP.skriv_xlsx(mappe / "StrategyResults_v4_Sentiment" /
                  "Sentiment_v4_SMA200_2026-01-01.xlsx",
                  logg(fro + 1), ["date", "ticker", "score", "rank", "valgt"],
                  arknavn="Score_Log")
    (mappe / "DataNLP" / "BacktestResults").mkdir(parents=True, exist_ok=True)
    IP.skriv_xlsx(mappe / "DataNLP" / "BacktestResults" /
                  "S5_SentMom31_Signals_20260101_120000.xlsx",
                  [{"Date": IP.iso(d), "Ticker": t,
                    "Composite": round(rnd.gauss(0, 1), 3)}
                   for d in kal[::5] for t in rnd.sample(bare, 6)],
                  ["Date", "Ticker", "Composite"])
    return mappe


class Persentilene(unittest.TestCase):
    """Rangeringen skal aldri kunne se framover."""

    def test_persentilen_endres_ikke_av_framtidige_rader(self):
        tidlig = [{"Kilde": "PB-ROE", "Dato": "2020-01-01", "Ticker": "A", "Ra_Score": 1.0},
                  {"Kilde": "PB-ROE", "Dato": "2020-02-01", "Ticker": "A", "Ra_Score": 2.0},
                  {"Kilde": "PB-ROE", "Dato": "2020-03-01", "Ticker": "A", "Ra_Score": 3.0}]
        senere = [dict(r) for r in tidlig] + [
            {"Kilde": "PB-ROE", "Dato": "2021-01-01", "Ticker": "A", "Ra_Score": 99.0},
            {"Kilde": "PB-ROE", "Dato": "2021-02-01", "Ticker": "A", "Ra_Score": -99.0}]
        M.persentiler(tidlig)
        M.persentiler(senere)
        for a, b in zip(tidlig, senere[:3]):
            self.assertEqual(a["Score"], b["Score"],
                             "en rad fra 2020 endret seg da 2021 ble lagt til")

    def test_alle_radene_samme_dag_rangeres_mot_samme_grunnlag(self):
        rader = [{"Kilde": "NLP", "Dato": "2020-01-01", "Ticker": "A", "Ra_Score": 1.0},
                 {"Kilde": "NLP", "Dato": "2020-01-01", "Ticker": "B", "Ra_Score": 9.0}]
        M.persentiler(rader)
        self.assertEqual(rader[0]["Score"], rader[1]["Score"])   # ingen historikk ennå

    def test_persentilen_ligger_mellom_null_og_hundre(self):
        rnd = random.Random(3)
        rader = [{"Kilde": "SentMom", "Dato": f"2020-{m:02d}-01", "Ticker": "A",
                  "Ra_Score": rnd.gauss(0, 1)} for m in range(1, 13)]
        M.persentiler(rader)
        for r in rader:
            self.assertGreaterEqual(r["Score"], 0.0)
            self.assertLessEqual(r["Score"], 100.0)


class SamletScore(unittest.TestCase):

    def _oppsett(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        mappe = Path(tmp.name)
        opp, tickere = _marked(mappe / "data", effekt_pst=4.0, fro=11)
        kal = IP.les_kalenderfil(opp.kalender_csv)
        _excel(mappe / "excel", kal, tickere)
        m = M.Master(excel_dir=mappe / "excel", innside_dir=opp.base_dir)
        m.ut_dir = mappe / "ut"
        m.ut_dir.mkdir(parents=True, exist_ok=True)
        return m, kal

    def test_alle_fire_kildene_leses(self):
        m, _ = self._oppsett()
        rader, kilder = M.les_alle_scorer(m, IP.stillelogger())
        self.assertEqual({k["Kilde"] for k in kilder}, set(M.KILDER))
        for k in kilder:
            self.assertEqual(k["Merknad"], "", f"{k['Kilde']}: {k['Merknad']}")
            self.assertGreater(int(k["Rader"]), 0)

    def test_kilde_uten_mening_teller_som_noeytral_ikke_null(self):
        """
        Forskjellen på «modellen misliker selskapet» og «modellen kjenner det
        ikke». Uten dette ville et selskap bare én modell kjenner fått samme
        samlede score som ett alle fire misliker.
        """
        m, kal = self._oppsett()
        m.min_kilder = 1
        rader = [{"Kilde": "Innside", "Dato": IP.iso(kal[100]), "Ticker": "T01",
                  "Ra_Score": 90.0, "Score": 100.0}]
        samlet = M.bygg_samlet(m, rader, [kal[101]], IP.stillelogger())
        self.assertEqual(len(samlet), 1)
        # 25 % × 100 + tre kilder à 50 = 62,5
        self.assertAlmostEqual(float(samlet[0]["Samlet_Score"]), 62.5, places=1)
        self.assertEqual(int(samlet[0]["Kilder"]), 1)

    def test_gammel_score_faller_ut_av_vinduet(self):
        m, kal = self._oppsett()
        gammel = kal[0]
        rader = [{"Kilde": "SentMom", "Dato": IP.iso(gammel), "Ticker": "T01",
                  "Ra_Score": 9.0, "Score": 100.0}]
        m.min_kilder = 1
        nær = M.bygg_samlet(m, rader, [gammel + timedelta(days=1)], IP.stillelogger())
        fjern = M.bygg_samlet(m, rader, [gammel + timedelta(days=400)],
                              IP.stillelogger())
        self.assertEqual(len(nær), 1)
        self.assertEqual(fjern, [], "en score fra i fjor teller fortsatt")


class SamletBacktest(unittest.TestCase):

    def _kjor(self, effekt_pst: float, fro: int):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        mappe = Path(tmp.name)
        opp, tickere = _marked(mappe / "data", effekt_pst=effekt_pst, fro=fro)
        kal = IP.les_kalenderfil(opp.kalender_csv)
        _excel(mappe / "excel", kal, tickere, fro=fro)
        m = M.Master(excel_dir=mappe / "excel", innside_dir=opp.base_dir)
        m.ut_dir = mappe / "ut"
        m.ut_dir.mkdir(parents=True, exist_ok=True)
        rader, _ = M.les_alle_scorer(m, IP.stillelogger())
        M.persentiler(rader)
        samlet = M.bygg_samlet(m, rader, kal, IP.stillelogger())
        return m, M.backtest_samlet(m, samlet, IP.stillelogger())

    def test_reglene_fra_motoren_gjelder_ogsaa_her(self):
        m, (equity, _, beholdning, maal) = self._kjor(4.0, 21)
        self.assertTrue(equity)
        tynne = [r for r in equity if 0 < int(r["Antall_Navn"]) < m.min_navn]
        if tynne:
            self.fail(f"samlet strategi eide {tynne[0]['Antall_Navn']} navn "
                      f"{tynne[0]['Dato']}")
        self.assertLessEqual(float(maal["Maks_Vekt_Pst"]), 40.0)
        aksjer = [b for b in beholdning if b["Ticker"] != "(kontanter)"]
        self.assertGreaterEqual(len(aksjer), m.min_navn)

    def test_ingen_look_ahead_i_ren_stoey(self):
        """
        Uten plantet effekt skal den samlede scoren ikke skinne. Gjør den det,
        har sammenslåingen lekket framtiden inn i fortiden.
        """
        _, (equity, _, _, maal) = self._kjor(0.0, 47)
        self.assertTrue(equity)
        sharpe = IP.tolk_maskin(maal.get("Sharpe"))
        self.assertIsNotNone(sharpe)
        self.assertLess(sharpe, 1.5,
                        f"Sharpe {sharpe} i ren støy — fasiten lekker inn")


class ManglendeHistorikk(unittest.TestCase):
    """Den gamle Only-filen lagret ingen score per måned. Si det, ikke ti."""

    def test_leseren_sier_hva_som_mangler(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        mappe = Path(tmp.name)
        (mappe / "DataPB_ROE" / "Backtest").mkdir(parents=True)
        IP.skriv_xlsx(mappe / "DataPB_ROE" / "Backtest" / "BT_v3_Enhanced_x.xlsx",
                      [{"date": "2020-01", "holdings": "A, B"}],
                      ["date", "holdings"], arknavn="Monthly_Holdings")
        m = M.Master(excel_dir=mappe, innside_dir=mappe / "tomt")
        rader, fil, feil, _ = M.les_pbroe(m)
        self.assertEqual(rader, [])
        self.assertIsNotNone(fil)
        self.assertIn("Score_Log", feil)
        self.assertIn("PBROE_All3", feil)


class StilleFeilene(unittest.TestCase):
    """
    De to feilene som gjorde at halve grunnlaget forsvant uten en lyd.

    NLP: masteren valgte fil på ALDER, og den ferskeste filen var skrevet av
    en annen utgave av modellen som aldri lager et Score_Log-ark. Å kjøre
    modellen på nytt hjalp ikke.

    SentMom: hver rad hadde en dato Excel lagret som tallet 45900, og hver
    rad ble forkastet. Kilden meldte «0 scorer» med en hake foran seg.
    """

    def _mappe(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name)

    @staticmethod
    def _logg(n: int = 12):
        return [{"date": f"2026-0{1 + i % 9}-01", "ticker": f"T{i:02d}",
                 "score": 0.1 * i, "rank": i + 1, "valgt": "JA"}
                for i in range(n)]

    def _eldre(self, sti: Path) -> None:
        """Gjør filen eldre enn alt annet, uansett hvor raskt disken skriver."""
        os.utime(sti, (1_600_000_000, 1_600_000_000))

    def test_nlp_hopper_over_nyere_fil_uten_arket(self):
        mappe = self._mappe()
        nlp = mappe / "StrategyResults_v4_Sentiment"
        nlp.mkdir(parents=True)
        god = nlp / "Sentiment_v4_SMA200_20260101.xlsx"
        IP.skriv_xlsx(god, self._logg(), ["date", "ticker", "score", "rank", "valgt"],
                      arknavn="Score_Log")
        self._eldre(god)
        # Tvillingen: nyere, passer samme mønster, uten scoreloggen.
        IP.skriv_xlsx(nlp / "Sentiment_v4_1_SMA200_20260905.xlsx",
                      [{"date": "2026-09-01", "value": 1.0}], ["date", "value"],
                      arknavn="Equity_Curve")

        m = M.Master(excel_dir=mappe, innside_dir=mappe / "tomt")
        rader, fil, feil, notat = M.les_nlp(m)
        self.assertEqual(feil, "", "leseren ga opp i stedet for å lete videre")
        self.assertEqual(fil.name, god.name)
        self.assertEqual(len(rader), 12)
        self.assertIn("Sentiment_v4_1", notat, "notatet sier ikke hva som ble hoppet over")

    def test_nlp_sier_fra_naar_ingen_fil_har_arket(self):
        mappe = self._mappe()
        nlp = mappe / "StrategyResults_v4_Sentiment"
        nlp.mkdir(parents=True)
        IP.skriv_xlsx(nlp / "Sentiment_v4_1_SMA200_20260905.xlsx",
                      [{"date": "2026-09-01", "value": 1.0}], ["date", "value"],
                      arknavn="Equity_Curve")
        m = M.Master(excel_dir=mappe, innside_dir=mappe / "tomt")
        rader, fil, feil, _ = M.les_nlp(m)
        self.assertEqual(rader, [])
        self.assertIn("Score_Log", feil)
        self.assertIn("SentimentHendelseLab", feil)

    def test_nlp_velger_hendelsesmotoren_foran_en_nyere_maanedlig(self):
        """
        To motorer kan skrive en scorelogg om det samme selskapet, og de måler
        ikke det samme: den månedlige ga den SAMME nyheten som signal måned etter
        måned, den hendelsesdrevne gir den én gang. Da er det ikke den ferskeste
        filen som skal vinne — det er motoren som er kilden nå. Å velge på alder
        ville gjort hvilken motor som gjaldt avhengig av rekkefølgen du kjørte
        dem i.
        """
        mappe = self._mappe()
        nlp = mappe / "StrategyResults_v4_Sentiment"
        nlp.mkdir(parents=True)
        hendelse = nlp / "Sentiment_v6_Hendelse_SMA50_2026-01-01.xlsx"
        IP.skriv_xlsx(hendelse, self._logg(),
                      ["date", "ticker", "score", "rank", "valgt"],
                      arknavn="Score_Log")
        self._eldre(hendelse)
        # Den månedlige: NYERE, og med en fullgod scorelogg.
        IP.skriv_xlsx(nlp / "Sentiment_v4_SMA200_20260905.xlsx", self._logg(3),
                      ["date", "ticker", "score", "rank", "valgt"],
                      arknavn="Score_Log")

        m = M.Master(excel_dir=mappe, innside_dir=mappe / "tomt")
        rader, fil, feil, notat = M.les_nlp(m)
        self.assertEqual(feil, "", feil)
        self.assertEqual(fil.name, hendelse.name)
        self.assertEqual(len(rader), 12)
        self.assertIn("v6", notat)

    def test_nlp_faller_tilbake_paa_den_maanedlige_og_sier_det(self):
        """
        Uten hendelsesfilen er den månedlige bedre enn ingenting — en tom
        NLP-kilde koster en fjerdedel av samlet score. Men tallene er fra en
        annen motor, og det skal stå i mailen, ikke oppdages tre måneder senere.
        """
        mappe = self._mappe()
        nlp = mappe / "StrategyResults_v4_Sentiment"
        nlp.mkdir(parents=True)
        IP.skriv_xlsx(nlp / "Sentiment_v4_SMA200_20260905.xlsx", self._logg(5),
                      ["date", "ticker", "score", "rank", "valgt"],
                      arknavn="Score_Log")
        m = M.Master(excel_dir=mappe, innside_dir=mappe / "tomt")
        rader, fil, feil, notat = M.les_nlp(m)
        self.assertEqual(feil, "", feil)
        self.assertEqual(len(rader), 5)
        self.assertIn("ANNEN motor", notat)
        self.assertIn("Sentiment_v6_Hendelse", notat)

    def test_nlp_uten_noen_av_motorene_navngir_begge(self):
        mappe = self._mappe()
        (mappe / "StrategyResults_v4_Sentiment").mkdir(parents=True)
        m = M.Master(excel_dir=mappe, innside_dir=mappe / "tomt")
        _, _, feil, _ = M.les_nlp(m)
        self.assertIn("Sentiment_v6_Hendelse_SMA*.xlsx", feil)
        self.assertIn("Sentiment_v4*_SMA*.xlsx", feil)

    def test_sentmom_leser_datoer_lagret_som_excel_tall(self):
        """Filen pandas faktisk skriver: ekte datoceller, ikke tekst."""
        mappe = self._mappe()
        sm = mappe / "DataNLP" / "BacktestResults"
        sm.mkdir(parents=True)
        TP.skriv_xlsx_med_datoceller(
            sm / "S5_SentMom31_Signals_20260905_120000.xlsx",
            ["Date", "Ticker", "Composite"],
            [(45900, "EQNR", 1.23), (45901, "DNB", -0.44), (45902, "NHY", 0.7)])
        m = M.Master(excel_dir=mappe, innside_dir=mappe / "tomt")
        rader, _, feil, _ = M.les_sentmom(m)
        self.assertEqual(feil, "", feil)
        self.assertEqual(len(rader), 3)
        self.assertEqual(rader[0]["Dato"], "2025-08-31")
        self.assertEqual(rader[0]["Ticker"], "EQNR")

    def test_sentmom_foretrekker_kandidatloggen(self):
        """
        Signalloggen inneholder bare navn modellen KJØPTE. Finnes
        kandidatloggen, skal den brukes — og gjør den ikke det, skal
        notatet si hvorfor persentilen blir for høy.
        """
        mappe = self._mappe()
        sm = mappe / "DataNLP" / "BacktestResults"
        sm.mkdir(parents=True)
        bare_signaler = sm / "S5_SentMom31_Signals_20260101_120000.xlsx"
        IP.skriv_xlsx(bare_signaler,
                      [{"Date": "2026-01-05", "Ticker": "EQNR", "Composite": 2.0}],
                      ["Date", "Ticker", "Composite"], arknavn="Signals")
        m = M.Master(excel_dir=mappe, innside_dir=mappe / "tomt")
        rader, _, feil, notat = M.les_sentmom(m)
        self.assertEqual(feil, "")
        self.assertEqual(len(rader), 1)
        self.assertIn("KJØPTE", notat)

        # Samme fil, men med kandidatloggen i sitt eget ark.
        IP.skriv_xlsx(sm / "S5_SentMom31_Signals_20260905_120000.xlsx",
                      [{"Date": "2026-09-01", "Ticker": "DNB", "Composite": 1.0,
                        "Rank": 1, "Kandidat": "NEI"},
                       {"Date": "2026-09-01", "Ticker": "NHY", "Composite": 0.4,
                        "Rank": 2, "Kandidat": "JA"}],
                      ["Date", "Ticker", "Composite", "Rank", "Kandidat"],
                      arknavn="Score_Log")
        rader, _, feil, notat = M.les_sentmom(m)
        self.assertEqual(feil, "")
        self.assertEqual(notat, "", "notatet står igjen selv om arket finnes")
        self.assertEqual({r["Ticker"] for r in rader}, {"DNB", "NHY"})

    def test_uleselige_datoer_gir_forklaring_ikke_hake(self):
        mappe = self._mappe()
        sm = mappe / "DataNLP" / "BacktestResults"
        sm.mkdir(parents=True)
        IP.skriv_xlsx(sm / "S5_SentMom31_Signals_20260905_120000.xlsx",
                      [{"Date": "i går", "Ticker": "EQNR", "Composite": 1.0},
                       {"Date": "", "Ticker": "DNB", "Composite": 2.0}],
                      ["Date", "Ticker", "Composite"], arknavn="Score_Log")
        m = M.Master(excel_dir=mappe, innside_dir=mappe / "tomt")
        rader, _, feil, _ = M.les_sentmom(m)
        self.assertEqual(rader, [])
        self.assertIn("2 rader lest", feil)
        self.assertIn("dato", feil.lower())

    def test_null_rader_er_aldri_en_hake(self):
        """
        Regelen hele denne klassen finnes for: en kilde uten rader teller 50
        for hvert selskap, og det skal stå i statusen — ikke oppdages senere.
        """
        mappe = self._mappe()
        (mappe / "DataNLP" / "BacktestResults").mkdir(parents=True)
        IP.skriv_xlsx(mappe / "DataNLP" / "BacktestResults" /
                      "S5_SentMom31_Signals_20260905_120000.xlsx", [],
                      ["Date", "Ticker", "Composite"], arknavn="Score_Log")
        m = M.Master(excel_dir=mappe, innside_dir=mappe / "tomt")
        _, kilder = M.les_alle_scorer(m, IP.stillelogger())
        for k in kilder:
            self.assertEqual(int(k["Rader"]), 0)
            self.assertTrue(k["Merknad"], f"{k['Kilde']} meldte 0 rader uten merknad")


class ÉnAvsender(unittest.TestCase):
    """
    Strategisammendraget er en SEKSJON i masterens mail, ikke en egen mail.

    Før gikk det to mailer per kjøring: master sendte sin, og mail_strategier
    sendte sin, hver med sitt passord. Bare den ene kom fram, og de to fortalte
    hver sin historie om de samme filene.

    Seksjonen henter tall gjennom pandas, som masteren ellers klarer seg uten.
    Derfor er kravet her todelt: den skal bygges når den kan, og den skal koste
    deg én seksjon — aldri hele mailen — når den ikke kan.
    """

    def test_manglende_modul_gir_en_merknad_ikke_et_unntak(self):
        mappe = Path(tempfile.mkdtemp())
        m = M.Master(excel_dir=mappe, innside_dir=mappe / "tomt")
        ekte = M.SKRIPTMAPPE
        try:
            M.SKRIPTMAPPE = mappe          # her finnes ingen mail/-mappe
            s = M.strategisammendrag(m, IP.stillelogger())
        finally:
            M.SKRIPTMAPPE = ekte
        self.assertEqual(s["stil"], "")
        self.assertEqual(s["kort"], {})
        self.assertIn("mail_strategier.py", s["html"])

    def test_feil_under_bygging_tar_ikke_mailen_med_seg(self):
        """
        Uten pandas kan seksjonen ikke bygges. Da skal resten av mailen stå.
        Er pandas installert, bygges den — og da er det den veien som testes.
        """
        mappe = Path(tempfile.mkdtemp())
        m = M.Master(excel_dir=mappe, innside_dir=mappe / "tomt")
        s = M.strategisammendrag(m, IP.stillelogger())
        for n in ("stil", "html", "kort", "strategier", "ekstra"):
            self.assertIn(n, s)

    def test_mailen_bygges_med_og_uten_seksjonen(self):
        mappe = Path(tempfile.mkdtemp())
        m = M.Master(excel_dir=mappe, innside_dir=mappe / "tomt")
        m.ut_dir.mkdir(parents=True, exist_ok=True)
        uten = M.bygg_mail(m, [], [], [], {}, [], [])
        med = M.bygg_mail(m, [], [], [], {}, [], [],
                          ".strategier .card { color:#111; }",
                          '<div class="strategier"><div class="card">hei</div></div>')
        for html in (uten, med):
            self.assertTrue(html.startswith("<html>"))
            self.assertIn("</html>", html)
        self.assertNotIn("strategier", uten)
        self.assertIn('<div class="strategier">', med)
        # CSS-en fra sammendraget skal være scopet, ellers drar den i
        # masterens egne tabeller.
        self.assertIn(".strategier .card", med)

    def test_seksjonens_css_er_scopet(self):
        """
        Malen i mail_strategier.py skal kunne settes med og uten prefiks, og
        begge former skal være gyldig CSS. Leses fra kilden: modulen krever
        pandas, som ikke trengs for å svare på dette.
        """
        import re
        kilde = (Path(M.__file__).resolve().parent / "mail" /
                 "mail_strategier.py")
        if not kilde.exists():
            self.skipTest("mail_strategier.py er ikke med i denne utsjekken")
        mal = re.search(r'STIL_MAL = """(.*?)"""',
                        kilde.read_text(encoding="utf-8"), re.S).group(1)

        def sett(prefiks):
            return (mal.replace("{{", "\x00").replace("}}", "\x01")
                       .replace("{p}", prefiks)
                       .replace("\x00", "{").replace("\x01", "}"))

        for prefiks in ("", ".strategier "):
            ut = sett(prefiks)
            self.assertNotIn("{p}", ut)
            self.assertEqual(ut.count("{"), ut.count("}"))
        self.assertIn(".strategier .card", sett(".strategier "))


class HvilkenMotorMasterKjorer(unittest.TestCase):
    """
    Ledelses-sentiment skal komme fra hendelseslaben, ikke fra den månedlige.

    Dette er ikke en detalj: den månedlige gikk gjennom alle selskaper hver
    månedsslutt og regnet bedringen fra forrige rapport på nytt — men forrige
    rapport endrer seg ikke mellom rapportene, så den SAMME nyheten ga det samme
    signalet måned etter måned. Én rapport ble tretten kjøp, det første 23 dager
    for sent. Står den gamle funksjonen igjen i listen, er det den som kjører.

    Masteren kan ikke kjøres her (den laster ned kurser), så listen leses med
    ast. Det er tilstrekkelig: spørsmålet er hvilket navn som står der.
    """

    @staticmethod
    def _de_tre():
        import ast
        kilde = Path(M.__file__).resolve().with_suffix(".py")
        tre = ast.parse(kilde.read_text(encoding="utf-8"))
        for n in ast.walk(tre):
            if isinstance(n, ast.FunctionDef) and n.name == "de_tre":
                return n
        raise AssertionError("fant ikke de_tre i master.py")

    def test_hendelseslaben_er_kilden(self):
        import ast
        kilde = ast.unparse(self._de_tre())
        self.assertIn("O.SentimentHendelseLab", kilde)
        self.assertIn("NLP Sentiment — ledelse", kilde)
        # Navnet på kilden og navnet på funksjonen skal høre sammen.
        par = [l for l in kilde.splitlines() if "NLP Sentiment — ledelse" in l]
        self.assertTrue(par)
        self.assertTrue(any("SentimentHendelseLab" in l for l in par),
                        f"kilden er koblet til noe annet: {par}")

    def test_den_maanedlige_kjores_bare_for_aa_skrape(self):
        """
        SentimentManagement() skal ikke være borte — den er fortsatt den som
        henter artiklene. Men den skal bare kjøre når du ber om skraping, og
        den skal ikke hete det kilden heter.
        """
        import ast
        de_tre = self._de_tre()
        kall = [n for n in ast.walk(de_tre)
                if isinstance(n, ast.Attribute) and n.attr == "SentimentManagement"]
        self.assertEqual(len(kall), 1, "SentimentManagement står flere steder")
        # Det ene stedet må ligge inne i en if.
        inne_i_if = [n for n in ast.walk(de_tre) if isinstance(n, ast.If)
                     and any(isinstance(x, ast.Attribute)
                             and x.attr == "SentimentManagement"
                             for x in ast.walk(n))]
        self.assertTrue(inne_i_if, "skrapingen er ikke betinget")
        self.assertIn("AKSJE_NLP_HENT", ast.unparse(inne_i_if[0].test))
        linjer = [l for l in ast.unparse(de_tre).splitlines()
                  if "SentimentManagement" in l]
        self.assertFalse(any("NLP Sentiment — ledelse" in l for l in linjer),
                         f"den månedlige er fortsatt merket som kilden: {linjer}")


class InnsidebacktestenBekreftes(unittest.TestCase):
    """
    Returkode 2 fra innsidepipelinen betyr ikke at backtesten kjørte.

    Et delvis steg 1 stanset kjeden før steg 6 og ga 2. Masteren kalte det OK,
    og feilen kom først fram som fem «not refreshed»-linjer uten årsak.
    """

    def setUp(self):
        self.mappe = Path(tempfile.mkdtemp())
        self.m = M.Master(excel_dir=self.mappe, innside_dir=self.mappe)
        self.ekte = IP.main
        self.addCleanup(setattr, IP, "main", self.ekte)

    def _pipeline(self, statuser, kode, skriv=True):
        def falsk(argv):
            if skriv:
                steg = [{"Steg": n, "Navn": IP.STEGNAVN[n], "Status": s,
                         "Sekunder": 1.0, "Detaljer": d, "Feil": ""}
                        for n, (s, d) in sorted(statuser.items())]
                self.m.oppsett().status_json.write_text(
                    __import__("json").dumps({"steg": steg}), encoding="utf-8")
            return kode
        IP.main = falsk

    def test_delvis_nedlasting_som_stanset_kjeden_er_en_feil(self):
        self._pipeline({1: ("DELVIS", "3912 artikler på disk (40 selskaper feilet)"),
                        **{n: ("IKKE_VALGT", "stanset fordi steg 1 feilet")
                           for n in range(2, 7)}}, 2)
        with self.assertRaisesRegex(RuntimeError, r"stanset på steg 1 .*40 selskaper"):
            M.kjor_innsidehandel(self.m, IP.stillelogger())

    def test_delvis_tekstuttrekk_med_fullfort_backtest_er_ok_med_merknad(self):
        self._pipeline({**{n: ("OK", "") for n in range(1, 7)},
                        3: ("DELVIS", "30 % ukjent")}, 2)
        merknad = M.kjor_innsidehandel(self.m, IP.stillelogger())
        self.assertIn("steg 3", merknad)
        self.assertIn("30 % ukjent", merknad)

    def test_noen_faa_feilede_selskaper_vises_som_merknad(self):
        self._pipeline({**{n: ("OK", "") for n in range(1, 7)},
                        1: ("OK", "3912 artikler på disk (2 selskaper feilet)")}, 0)
        self.assertIn("2 selskaper feilet",
                      M.kjor_innsidehandel(self.m, IP.stillelogger()))

    def test_ren_kjoring_gir_ingen_merknad(self):
        self._pipeline({n: ("OK", "") for n in range(1, 7)}, 0)
        self.assertEqual(M.kjor_innsidehandel(self.m, IP.stillelogger()), "")

    def test_gammel_statustavle_godtas_ikke(self):
        sti = self.m.oppsett().status_json
        sti.parent.mkdir(parents=True, exist_ok=True)
        sti.write_text('{"steg": [{"Steg": 6, "Status": "OK"}]}', encoding="utf-8")
        gammel = time.time() - 3600
        os.utime(sti, (gammel, gammel))
        self._pipeline({}, 0, skriv=False)
        with self.assertRaisesRegex(RuntimeError, "statustavle"):
            M.kjor_innsidehandel(self.m, IP.stillelogger())


class Prisnotat(unittest.TestCase):
    def test_rettede_og_utelatte_tickere_vises_i_kjoringen(self):
        mappe = Path(tempfile.mkdtemp())
        m = M.Master(excel_dir=mappe, innside_dir=mappe)
        start = time.time()
        sti = mappe / "StrategyResults_v5_Sentiment_Exit" / "management_price_issues.csv"
        sti.parent.mkdir(parents=True)
        sti.write_text(
            "ticker,date,issue,previous_price,price,ratio,resolution\n"
            "BSP.OL,2025-01-02,unit_scale_artifact,0.1,10.1,100.0,earlier prices multiplied by 100\n"
            "2020.OL,2025-06-02,unverified_adjusted_price_discontinuity,50,9,0.18,"
            "ticker excluded from the universe\n", encoding="utf-8")
        notat = M.prisnotat(m, start)
        self.assertIn("enhetsavvik rettet: BSP.OL", notat)
        self.assertIn("utelatt for uforklarte kurssprang: 2020.OL", notat)
        gammel = start - 3600
        os.utime(sti, (gammel, gammel))
        self.assertEqual(M.prisnotat(m, start), "")    # fra en tidligere kjøring


class Folgefeil(unittest.TestCase):
    def test_folgene_av_en_feilet_analyse_blir_en_linje(self):
        kjoring = [{"Analyse": "NLP Sentiment — ledelse", "Status": "FEIL",
                    "Feil": "RuntimeError: prisene"},
                   {"Analyse": "Innsidehandel Oslo Børs", "Status": "FEIL",
                    "Feil": "Backtesten ble ikke kjørt"},
                   {"Analyse": "PB-ROE-Momentum", "Status": "OK", "Feil": ""}]
        errors = ["NLP Sentiment — ledelse: RuntimeError: prisene",
                  "Innsidehandel Oslo Børs: Backtesten ble ikke kjørt",
                  "NLP Sentiment — ledelse: Management export predates accounting_version=2",
                  "NLP Sentiment — ledelse: output was not refreshed by this run",
                  "Innsidehandel — Oslo Børs: output was not refreshed by this run",
                  "Insider report was not refreshed: strategier.csv",
                  "PB-ROE-Momentum: output was not refreshed by this run"]
        ut, sammenslatt = M.samle_folgefeil(errors, kjoring)
        self.assertEqual(len(ut), 3)
        self.assertTrue(ut[0].startswith("NLP Sentiment — ledelse: RuntimeError: prisene"))
        self.assertIn("2 kontroller feilet", ut[0])
        self.assertIn("2 kontroller feilet", ut[1])
        # PB-ROE kjørte OK, så en utdatert fil der er en egen feil.
        self.assertIn("PB-ROE-Momentum: output was not refreshed by this run", ut)
        self.assertEqual(len(sammenslatt), 4)

    def test_uten_feilede_analyser_er_listen_uendret(self):
        errors = ["Insider report missing: strategier.csv"]
        self.assertEqual(M.samle_folgefeil(errors, [])[0], errors)


if __name__ == "__main__":
    unittest.main()
