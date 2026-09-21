# -*- coding: utf-8 -*-
"""
Vaktposter for feilene som gjorde at steg 2, 3, 5 og 6 sto stille.

Hver test her svarer til én kjøring der tallet var 0: 0 av 3912 meldinger
lest, 0 transaksjoner funnet, 9 handledager i kalenderen, 0 brukbare kjøp.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import innsidehandel_pipeline as P

RAMME = """<!doctype html><html><head><title>x</title>
<script>var a=1;</script><style>.a{color:red}</style></head><body>
<div class="site-header"><nav class="main-nav"><a href="/">Hjem</a><a href="/a">Marked</a>
<a href="/b">Selskaper</a><a href="/c">Indekser</a><a href="/d">Om oss</a></nav></div>
<div id="onetrust-consent" class="cookie-banner"><h2>Cookies Preferences</h2>
<p>We process your data to deliver content. We use cookies and other technologies
across our vendor list under legitimate interest. Manage your preferences.</p></div>
<div class="%s"><div class="article-body">%s</div></div>
<footer class="site-footer"><p>Euronext 2026. Alle rettigheter. Personvern.</p></footer>
</body></html>"""

# Slik ser en meldepliktig handel ut i praksis: et MAR-skjema, altså en
# TABELL. Merkelapp og verdi havner på hver sin linje, uten kolon.
MELDING = """<h1>{sel}: Meldepliktig handel</h1>
<table><tr><th>Name</th><td>{pers}</td></tr>
<tr><th>Position</th><td>Chief Executive Officer</td></tr>
<tr><th>Issuer</th><td>{sel} ASA</td></tr>
<tr><th>Nature of transaction</th><td>Purchase of shares</td></tr>
<tr><th>Volume</th><td>{ant}</td></tr>
<tr><th>Price</th><td>{pris} NOK</td></tr>
<tr><th>Date of transaction</th><td>{dato}</td></tr></table>
<p>Following the transaction, {pers} holds {eth} shares in {sel} ASA,
corresponding to a total holding after the transaction. This information is
subject to the disclosure requirements pursuant to the Market Abuse Regulation.</p>"""


def bygg(mappe: Path, n: int = 30, beholder: str = "content-wrapper",
         krop: str = MELDING) -> P.Oppsett:
    opp = P.Oppsett(base_dir=mappe)
    opp.lag_mapper()
    rader = []
    for i in range(n):
        mid = f"m{i:03d}"
        d = date(2024, 1, 3) + timedelta(days=i)
        html = RAMME % (beholder, krop.format(
            sel=f"Selskap{i}", pers=f"Person {i}", ant=1000 + i * 7,
            pris=f"{100 + i}.50", dato=d.isoformat(), eth=50000 + i * 11))
        (opp.artikkel_dir / f"{mid}.html").write_text(html, encoding="utf-8")
        rader.append({"Melding_ID": mid, "Selskap": f"Selskap{i}",
                      "Ticker": f"S{i:02d}.OL", "Dato": d.isoformat(),
                      "Klokkeslett": "08:30", "Tittel": "Meldepliktig handel",
                      "HTML_Fil": f"{mid}.html", "Sprak": "en"})
    P.skriv_csv(opp.indeks_csv, rader, P.INDEKS_KOLONNER)
    return opp



# ── En .xlsx med EKTE datoceller ─────────────────────────────────────────
#
# Slik pandas og openpyxl skriver dem: tallet står i cellen, og formatet på
# cellen sier at tallet er en dato. Vi bygger filen for hånd her, så testen
# ikke trenger openpyxl for å bevise at leseren tåler openpyxl.

def skriv_xlsx_med_datoceller(sti: Path, hode, rader, datostil: bool = True) -> None:
    """Kolonne A får datoformat (numFmtId 164), resten er vanlige celler."""
    import zipfile

    def celle(ref, verdi, stil):
        if isinstance(verdi, str):
            return (f'<c r="{ref}" t="inlineStr"{stil}>'
                    f'<is><t>{verdi}</t></is></c>')
        return f'<c r="{ref}"{stil}><v>{verdi}</v></c>'

    ut = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
          '<worksheet xmlns="http://schemas.openxmlformats.org/'
          'spreadsheetml/2006/main"><sheetData>']
    ut.append('<row r="1">' + "".join(
        celle(f"{chr(65 + i)}1", h, "") for i, h in enumerate(hode)) + "</row>")
    for nr, rad in enumerate(rader, start=2):
        celler = []
        for i, v in enumerate(rad):
            stil = ' s="1"' if (i == 0 and datostil) else ""
            celler.append(celle(f"{chr(65 + i)}{nr}", v, stil))
        ut.append(f'<row r="{nr}">' + "".join(celler) + "</row>")
    ut.append("</sheetData></worksheet>")

    stiler = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<styleSheet xmlns="http://schemas.openxmlformats.org/'
              'spreadsheetml/2006/main">'
              '<numFmts count="1">'
              '<numFmt numFmtId="164" formatCode="yyyy\\-mm\\-dd\\ h:mm:ss"/>'
              '</numFmts>'
              '<cellXfs count="2">'
              '<xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>'
              '<xf numFmtId="164" fontId="0" fillId="0" borderId="0" applyNumberFormat="1"/>'
              '</cellXfs></styleSheet>')

    with zipfile.ZipFile(sti, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", P._XLSX_TYPER)
        z.writestr("_rels/.rels", P._XLSX_RELS)
        z.writestr("xl/workbook.xml",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<workbook xmlns="http://schemas.openxmlformats.org/'
                   'spreadsheetml/2006/main" xmlns:r="http://schemas.'
                   'openxmlformats.org/officeDocument/2006/relationships">'
                   '<sheets><sheet name="Score_Log" sheetId="1" r:id="rId1"/>'
                   "</sheets></workbook>")
        z.writestr("xl/_rels/workbook.xml.rels", P._XLSX_WB_RELS)
        z.writestr("xl/styles.xml", stiler)
        z.writestr("xl/worksheets/sheet1.xml", "".join(ut))

class Steg2(unittest.TestCase):
    """0 av 3912 med tekst."""

    def _kjor(self, **kw):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        opp = bygg(Path(self.tmp.name), **kw)
        svar = P.steg2_tekst(opp, P.stillelogger())
        return opp, svar

    def test_tabellmelding_blir_lest(self):
        opp, svar = self._kjor()
        self.assertEqual(svar["med_tekst"], 30)
        t = (opp.tekst_dir / "m005.txt").read_text(encoding="utf-8")
        self.assertIn("Purchase of shares", t)
        self.assertIn("1035", t)               # volumet, fra en tabellcelle
        self.assertNotIn("Cookies Preferences", t)
        self.assertNotIn("Alle rettigheter", t)

    def test_melding_i_fjernet_beholder_berges_av_reserven(self):
        # «navigation-panel» fjernes av mønsteret. Meldingen skal likevel ut.
        opp, svar = self._kjor(beholder="navigation-panel")
        self.assertEqual(svar["med_tekst"], 30)
        t = (opp.tekst_dir / "m005.txt").read_text(encoding="utf-8")
        self.assertIn("Purchase of shares", t)
        self.assertNotIn("Cookies Preferences", t)

    def test_side_uten_melding_gir_ingen_tekst(self):
        # Den opprinnelige feilen: cookie-vinduet lagret som «meldingen».
        _, svar = self._kjor(krop="<p>&nbsp;</p>")
        self.assertEqual(svar["med_tekst"], 0)

    def test_research_er_ikke_search(self):
        self.assertIsNone(P._FJERN_MONSTER.search("company-research-block"))
        self.assertIsNone(P._FJERN_MONSTER.search("share-price"))
        self.assertTrue(P._FJERN_MONSTER.search("main-nav"))
        self.assertTrue(P._FJERN_MONSTER.search("onetrust-consent"))


class Steg3(unittest.TestCase):
    """Teksten var der, men ingen transaksjon ble funnet."""

    TABELL = ("Nature of transaction\nPurchase of shares\n"
              "Volume\n1035\nPrice\n105.50 NOK\nDate of transaction\n2024-01-08")

    def test_merkelapp_og_verdi_paa_hver_sin_linje(self):
        self.assertEqual(P.finn_verdi(self.TABELL, P.LABEL_VOLUM), "1035")
        self.assertEqual(P.finn_verdi(self.TABELL, P.LABEL_ART), "Purchase of shares")

    def test_kolon_virker_fortsatt(self):
        self.assertEqual(P.finn_verdi("Volume: 2 500", P.LABEL_VOLUM), "2 500")

    def test_loepende_tekst_stjeler_ikke_neste_linje(self):
        # «… price» sist på en linje er ikke en merkelapp.
        tekst = "shares were sold at an average price\n2024-01-08"
        self.assertEqual(P.finn_verdi(tekst, ("price",)), "")

    def test_hele_meldingen_blir_et_kjoep(self):
        u = P.les_melding("Meldepliktig handel", self.TABELL)
        self.assertEqual(u.klasse, "KJOP")
        self.assertEqual(u.antall_netto, 1035)


class Kalenderen(unittest.TestCase):
    """Ni handledager, fordi 241 tynne serier stemte ned alle andre dager."""

    def test_tynne_serier_kveler_ikke_kalenderen(self):
        lang = [date(2024, 1, 1) + timedelta(days=i) for i in range(0, 600, 3)]
        kort = [date(2026, 8, 17) + timedelta(days=i) for i in range(9)]
        per = {f"L{i}": lang for i in range(4)}
        per.update({f"K{i}": kort for i in range(40)})
        self.assertGreater(len(P.utled_handledager(per, 0.20)), 190)


class Steg5(unittest.TestCase):
    """En melding fra 2019 fikk kjøpskurs fra 2026 og ble merket FOR_NY."""

    def test_melding_foer_foerste_kursdag_avvises(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        opp = P.Oppsett(base_dir=Path(tmp.name))
        opp.lag_mapper()
        dager = [d for d in (date(2026, 8, 1) + timedelta(days=i) for i in range(60))
                 if d.weekday() < 5]
        bok = P.Kursbok(opp.s4_dir)
        for t in ("AAA.OL", "OSEBX.OL"):
            bok.slå_sammen(t, {d: {"close": 100.0, "adjclose": 100.0, "volum": 1e5}
                               for d in dager})
            bok.lagre_ticker(t)
        P.skriv_referansevalg(opp, "OSEBX.OL", "indeks")
        P.skriv_csv(opp.hendelser_csv,
                    [{"Melding_ID": "a", "Dato": "2019-05-02", "Klokkeslett": "09:00",
                      "Ticker": "AAA.OL", "Klasse": "KJOP", "Tillit": "HOY",
                      "Primaer_I_Klynge": "JA"}], P.HENDELSE_KOLONNER)
        P.steg5_merge(opp, P.stillelogger())
        rad = P.les_csv(opp.merget_csv)[0]
        self.assertEqual(rad["Kurs_Status"], "ELDRE_ENN_KURSDATA")
        self.assertEqual(rad["Kurs_0"], "")


class Steg4(unittest.TestCase):
    """Vannmerket sa «komplett», filen hadde ni dager. Ti år ble ikke hentet."""

    def test_vannmerket_sjekkes_mot_filene(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        opp = P.Oppsett(base_dir=Path(tmp.name))
        opp.lag_mapper()
        i_dag, eldste = date.today(), opp.eldste_kurs()
        bok = P.Kursbok(opp.s4_dir)
        bok.slå_sammen("S00.OL", {i_dag - timedelta(days=k):
                                  {"close": 100.0, "adjclose": 100.0, "volum": 1e5}
                                  for k in range(9)})
        bok.lagre_ticker("S00.OL")
        vm = P.Vannmerke(opp.vannmerke_json, P.stillelogger())
        vm.sett(P.GRUPPE_KURSER, "S00.OL", i_dag - timedelta(days=1), dager=9)

        bedt = []
        ekte_yf, ekte_en = P.hent_yfinance, P._hent_en_ticker
        P.hent_yfinance = lambda t, fra, til: (bedt.append(fra) or {})
        P._hent_en_ticker = lambda t, fra, til, lo, o: (bedt.append(fra) or {})
        try:
            P._hent_alle_kurser(opp, P.stillelogger(), bok, vm, ["S00.OL"],
                                eldste, i_dag)
        finally:
            P.hent_yfinance, P._hent_en_ticker = ekte_yf, ekte_en
        self.assertTrue(bedt)
        self.assertEqual(min(bedt), eldste)



class ExcelDatoer(unittest.TestCase):
    """
    Datoen som forsvant: pandas skriver en ekte dato, Excel lagrer den som
    tallet 45900, og en leser som venter ÅÅÅÅ-MM-DD forkaster hele filen
    uten et ord. SentMom-kilden i master.py sto på 0 rader av nøyaktig
    denne grunnen.
    """

    def test_serienummer_blir_riktig_dato(self):
        self.assertEqual(P.fra_excel_serienr(45900).date(), date(2025, 8, 31))
        self.assertEqual(P.fra_excel_serienr(1).date(), date(1900, 1, 1))
        # Serienummer 60 finnes ikke — Excel tror 1900 var et skuddår.
        self.assertEqual(P.fra_excel_serienr(59).date(), date(1900, 2, 28))
        self.assertEqual(P.fra_excel_serienr(61).date(), date(1900, 3, 1))

    def test_klokkeslettet_avrundes_til_hele_sekunder(self):
        dt = P.fra_excel_serienr(45900.5)
        self.assertEqual((dt.hour, dt.minute, dt.second), (12, 0, 0))

    def test_1904_systemet(self):
        self.assertEqual(P.fra_excel_serienr(0.0 + 1, dato1904=True).date(),
                         date(1904, 1, 2))

    def test_tolerant_leser_tar_alle_skrivemaatene(self):
        for rå, fasit in (("2026-09-05", date(2026, 9, 5)),
                          ("2026-09-05 15:30:00", date(2026, 9, 5)),
                          ("2026-09-05T15:30:00", date(2026, 9, 5)),
                          ("05.09.2026", date(2026, 9, 5)),
                          ("20260905", date(2026, 9, 5)),
                          ("45900", date(2025, 8, 31)),
                          (45900, date(2025, 8, 31))):
            self.assertEqual(P.fra_dato_celle(rå), fasit, f"«{rå}»")

    def test_et_tall_som_ikke_kan_vaere_en_dato_blir_ingen_dato(self):
        """
        Det farligste et tolerant format kan gjøre er å tolke en SCORE som
        en dato. Vinduet er derfor snevert: 0,73 og 12 er ikke datoer.
        """
        for rå in (0.73, "0,73", 12, "12", -45900, 999_999_999, True, None, "",
                   "EQNR", "2026-13-45"):
            self.assertIsNone(P.fra_dato_celle(rå), f"«{rå}» ble tolket som dato")

    def test_fra_iso_er_fortsatt_streng(self):
        """
        Den tolerante leseren er for ANDRES filer. Våre egne skal fortsatt
        avvise et tall i et datofelt — der er det en feil, ikke en dato.
        """
        self.assertIsNone(P.fra_iso("45900"))
        self.assertIsNone(P.fra_iso("05.09.2026"))
        self.assertEqual(P.fra_iso("2026-09-05"), date(2026, 9, 5))


class XlsxDatoceller(unittest.TestCase):
    """Leseren må se forskjell på tallet 45900 og datoen 45900."""

    def test_datoformatert_celle_leses_som_dato(self):
        with tempfile.TemporaryDirectory() as mappe:
            sti = Path(mappe) / "scorelogg.xlsx"
            skriv_xlsx_med_datoceller(
                sti, ["Date", "Ticker", "Composite"],
                [(45900, "EQNR", 1.23), (45900.5, "DNB", -0.5)])
            rader = P.les_xlsx(sti, ("date", "ticker"))
            self.assertEqual(len(rader), 2)
            self.assertEqual(rader[0]["Date"], "2025-08-31")
            self.assertEqual(rader[1]["Date"], "2025-08-31 12:00:00")
            # Tallkolonnen skal IKKE bli en dato.
            self.assertEqual(rader[0]["Composite"], "1.23")

    def test_tall_uten_datoformat_blir_staaende(self):
        with tempfile.TemporaryDirectory() as mappe:
            sti = Path(mappe) / "tall.xlsx"
            skriv_xlsx_med_datoceller(sti, ["Date", "Ticker", "Composite"],
                                      [(45900, "EQNR", 1.23)], datostil=False)
            rader = P.les_xlsx(sti, ("date", "ticker"))
            self.assertEqual(rader[0]["Date"], "45900")

    def test_arknavnene_kan_leses(self):
        with tempfile.TemporaryDirectory() as mappe:
            sti = Path(mappe) / "ark.xlsx"
            P.skriv_xlsx(sti, [{"a": 1}], ["a"], arknavn="Score_Log")
            self.assertEqual(P.xlsx_arknavn(sti), ["Score_Log"])
            self.assertTrue(P.har_xlsx_ark(sti, "score_log"))
            self.assertFalse(P.har_xlsx_ark(sti, "Signals"))
            self.assertFalse(P.har_xlsx_ark(Path(mappe) / "finnes_ikke.xlsx", "x"))

if __name__ == "__main__":
    unittest.main()


# ══════════════════════════════════════════════════════════════════════════
# STEG 1 — meldingen ble aldri hentet, bare listesiden
# ══════════════════════════════════════════════════════════════════════════

# Slik ser en rad i Euronext sin trefflliste ut. Merk href="": overskriften
# er ingen lenke, den åpner en modal. Leser man a.href, får man LISTESIDENS
# egen adresse — og da lagrer man søkeresultatet 3912 ganger.
LISTESIDE = """<!doctype html><html><head><title>Press releases</title></head><body>
<div class="site-header"><nav class="main-nav"><a href="/">Home</a></nav></div>
<table><thead><tr><th>Date</th><th>Company</th><th>Title</th><th>ICB</th>
<th>Category</th></tr></thead><tbody>
%s
</tbody></table>
%s
</body></html>"""

RAD = """<tr>
<td class="views-field-field-company-pr-pub-datetime"><span class="nowrap">
%(dag)s</span><br><span class="nowrap"> %(kl)s CEST</span></td>
<td class="views-field-field-company-name">%(sel)s ASA</td>
<td class="views-field-title"><a href="" class="standardRightCompanyPressRelease"
 data-node-nid="%(nid)s" data-toggle="modal"
 data-target="#CompanyPressRelease-%(nid)s">%(tittel)s</a></td>
<td class="views-field-field-icb">60101030 Oil Equipment and Services</td>
<td class="views-field-field-company-press-releases">Mandatory notification of
trade primary insiders</td></tr>"""

MODAL = """<div class="modal fade" id="CompanyPressRelease-%(nid)s">
<div class="modal-dialog"><div class="modal-content">
<div class="modal-body cpr-canvas-content"></div></div></div></div>"""

# Euronext fyller modalen med JavaScript når du klikker. Uten dette skriptet
# er testsida en tro kopi av den ekte: tom modal, tom href.
MELDING_HTML = """<div class="pr"><h1>Mandatory notification of trade</h1>
<table><tr><th>Nature of transaction</th><td>Purchase of shares</td></tr>
<tr><th>Volume</th><td>4 500</td></tr><tr><th>Price</th><td>NOK 88.20</td></tr>
<tr><th>Position</th><td>Chief Executive Officer</td></tr></table>
<p>Node {nid}. This information is subject to the disclosure
requirements pursuant to the Market Abuse Regulation.</p></div>"""

KLIKK_JS = """
document.querySelectorAll('a[data-node-nid]').forEach(function (a) {
  a.addEventListener('click', function (e) {
    e.preventDefault();
    var nid = a.getAttribute('data-node-nid');
    fetch('/nb/ajax/press-release/' + nid).then(function (response) {
      return response.text();
    }).then(function (html) {
      var d = document.querySelector('#CompanyPressRelease-' + nid + ' .modal-body');
      if (d) d.innerHTML = html;
    });
  });
});
"""


def _listeside(antall: int = 5) -> str:
    rader, modaler = [], []
    for i in range(antall):
        d = {"dag": f"{2 + i:02d} Mar 2026", "kl": "09:40", "sel": f"Selskap{i}",
             "nid": str(12900000 + i), "tittel": "Mandatory notification of trade"}
        rader.append(RAD % d)
        modaler.append(MODAL % d)
    return LISTESIDE % ("\n".join(rader), "\n".join(modaler))


class Steg1Nøkkel(unittest.TestCase):
    """Samme melding ble lagret to ganger, én gang per datovindu."""

    def test_node_id_gir_samme_noekkel_fra_to_datovinduer(self):
        a = P.lag_id("https://x/listview/y?start=2016-08-29", "ZALARIS",
                     "2026-08-29", "09:40", "Mandatory notification of trade",
                     "12906309")
        b = P.lag_id("https://x/listview/y?start=2026-08-19", "ZALARIS",
                     "2026-08-29", "09:40", "Mandatory notification of trade",
                     "12906309")
        self.assertEqual(a, b)
        self.assertEqual(a, "EN-12906309")

    def test_uten_node_id_faller_vi_tilbake_paa_hashen(self):
        self.assertTrue(P.lag_id("", "A", "2026-01-01", "09:00", "x").startswith("H-"))


class Steg1Rydding(unittest.TestCase):
    """De gamle radene pekte på en halv megabyte søkeresultat hver."""

    def test_listesider_kastes_ekte_meldinger_beholdes(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        opp = P.Oppsett(base_dir=Path(tmp.name))
        opp.lag_mapper()
        (opp.artikkel_dir / "gammel.html").write_text("x" * 150_000, encoding="utf-8")
        (opp.artikkel_dir / "liten.html").write_text("x" * 2_000, encoding="utf-8")
        lagret = {
            "H-1": {"Melding_ID": "H-1", "Node_ID": "", "HTML_Fil": "gammel.html"},
            "H-2": {"Melding_ID": "H-2", "Node_ID": "", "HTML_Fil": "liten.html"},
            "EN-3": {"Melding_ID": "EN-3", "Node_ID": "3", "HTML_Fil": "ny.html"},
        }
        self.assertEqual(P.rydd_gammelt_format(opp, lagret, P.stillelogger()), 1)
        self.assertEqual(sorted(lagret), ["EN-3", "H-2"])
        self.assertFalse((opp.artikkel_dir / "gammel.html").exists())


class Steg1Svar(unittest.TestCase):
    """Svaret fra Euronext er ikke alltid ren HTML."""

    def test_json_konvolutten_pakkes_ut(self):
        svar = ('[{"command":"insert","method":"html",'
                '"data":"<div><p>Nature of transaction</p></div>"}]')
        self.assertIn("<p>Nature of transaction</p>", P.Euronext._som_html(svar))

    def test_listesiden_godtas_ikke_som_melding(self):
        klient = P.Euronext.__new__(P.Euronext)
        klient.opp = P.Oppsett(base_dir=Path("."))
        self.assertFalse(klient._duger("kort"))
        self.assertFalse(klient._duger(
            "x" * 500 + 'data-node-nid="1"' + 'data-node-nid="2"'))
        self.assertTrue(klient._duger("x" * 500))


class Steg1Uttrekk(unittest.TestCase):
    """Trenger nettleser: kjøres bare der Playwright finnes."""

    def setUp(self):
        try:
            import playwright.sync_api            # noqa: F401
        except ImportError:
            self.skipTest("Playwright er ikke installert")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.mappe = Path(self.tmp.name)
        # A file:// page cannot make this relative HTTP fetch. Serve a real
        # loopback response so the browser's request listener learns an endpoint
        # only when the modal content actually arrived from it. No remote access.
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from threading import Thread

        self.requests = []
        received = self.requests

        class FixtureHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                received.append(self.path)
                if self.path == "/liste.html":
                    body = _listeside()
                elif self.path.startswith("/nb/ajax/press-release/"):
                    nid = self.path.rsplit("/", 1)[-1]
                    if not nid.isdigit():
                        self.send_error(404)
                        return
                    body = MELDING_HTML.format(nid=nid)
                else:
                    self.send_error(404)
                    return
                payload = body.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def close_server():
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        self.addCleanup(close_server)
        self.fixture_origin = f"http://127.0.0.1:{server.server_port}"

    def test_node_id_ut_av_tabellen_og_melding_ut_av_modalen(self):
        # PW_CHROME lar deg peke på en Chromium som ligger et annet sted.
        opp = P.Oppsett(base_dir=self.mappe / "data",
                        browser_sti=os.environ.get("PW_CHROME", ""))
        opp.lag_mapper()
        logg = P.stillelogger()
        try:
            with P.Nettleser(opp, logg) as nl:
                nl.page.goto(self.fixture_origin + "/liste.html",
                             wait_until="domcontentloaded")
                klient = P.Euronext(nl, opp, logg)
                rader = klient._les_tabell(self.fixture_origin + "/liste.html")
                self.assertEqual(len(rader), 5)
                self.assertEqual([r["nid"] for r in rader],
                                 [str(12900000 + i) for i in range(5)])
                # href må IKKE bli listesidens egen adresse
                self.assertEqual([r["href"] for r in rader], [""] * 5)
                self.assertEqual(rader[0]["dato"], "2026-03-02")
                self.assertEqual(rader[0]["klokkeslett"], "09:40")

                nl.page.evaluate(KLIKK_JS)
                html = klient.hent_melding(rader[0])
                self.assertIn("Purchase of shares", html)
                # Første melding lærer opp resten: adressen leses av trafikken
                self.assertIn("{nid}", klient.mal)
                self.assertIn("12900000", klient.mal.format(nid="12900000"))
                self.assertEqual(klient.mal, self.fixture_origin + "/nb/ajax/press-release/{nid}")
                second = klient.hent_melding(rader[1])
                self.assertIn("Node 12900001", second)
                self.assertEqual(klient.via_klikk, 1)
                self.assertEqual(klient.via_url, 1)
                self.assertIn("/nb/ajax/press-release/12900000", self.requests)
                self.assertIn("/nb/ajax/press-release/12900001", self.requests)

                u = P.les_melding(rader[0]["tittel"],
                                  P.uten_sidemal(P.les_side(html)[1], set(), 50))
                self.assertEqual(u.klasse, "KJOP")
                self.assertEqual(u.antall_netto, 4500)
        except Exception as e:                     # ingen browser på maskinen
            if "Executable doesn't exist" in str(e) or "BrowserType.launch" in str(e):
                self.skipTest(f"Ingen Chromium tilgjengelig: {e}")
            raise


# ══════════════════════════════════════════════════════════════════════════
# STEG 6 — STRATEGIMOTOREN
# ══════════════════════════════════════════════════════════════════════════

def _marked(mappe: Path, effekt_pst: float = 0.0, n_tickere: int = 12,
            n_hendelser: int = 120, fro: int = 5):
    """Et syntetisk marked der fasiten er kjent."""
    import random
    rnd = random.Random(fro)
    opp = P.Oppsett(base_dir=mappe, inn_utvalg_slutt="2021-12-31",
                    min_omsetning_nok=0.0, min_score_portefolje=0.0)
    opp.lag_mapper()
    kal = [d for d in (date(2019, 1, 1) + timedelta(days=k) for k in range(1400))
           if d.weekday() < 5]
    tickere = [f"T{i:02d}.OL" for i in range(n_tickere)]
    hendelser = [(rnd.choice(tickere), kal[rnd.randrange(40, len(kal) - 120)],
                  rnd.uniform(30, 95)) for _ in range(n_hendelser)]

    løft = {}
    for t, d, _ in hendelser:
        for k in range(1, 21):
            løft[(t, d + timedelta(days=k))] = 1

    bok = P.Kursbok(opp.s4_dir)
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
    P.skriv_referansevalg(opp, "OSEBX.OL", "indeks")

    P.skriv_csv(opp.hendelser_csv, [
        {"Melding_ID": f"E{i}", "Dato": P.iso(d), "Klokkeslett": "09:00",
         "Selskap": t, "Ticker": t, "Klasse": "KJOP", "Tillit": "HOY",
         "Bullish_Score": round(sc, 1), "Primaer_I_Klynge": "JA",
         "Verdi_NOK": 250_000, "Rolle": "CEO"}
        for i, (t, d, sc) in enumerate(hendelser)], P.HENDELSE_KOLONNER)
    P.steg5_merge(opp, P.stillelogger())
    kjop = P.velg(P.les_csv(opp.merget_csv), opp, "KJOP")
    return opp, kjop


class Strategimotoren(unittest.TestCase):

    def _mappe(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name)

    def test_ingen_look_ahead_i_ren_stoey(self):
        """
        Den viktigste testen i filen. Uten plantet effekt skal INGEN variant
        skinne. Gjør en det, leser den framover i tid.
        """
        opp, kjop = _marked(self._mappe(), effekt_pst=0.0, fro=41)
        tabell, _, _, _ = P.sammenlikn_strategier(kjop, opp, P.stillelogger())
        self.assertTrue(tabell)
        sharper = [float(r["Sharpe"]) for r in tabell if r["Sharpe"] != ""]
        self.assertTrue(sharper)
        self.assertLess(max(sharper), 1.5,
                        f"Sharpe {max(sharper):.2f} i ren støy lukter look-ahead")

    def test_hendelsesdrevet_holder_foelge_med_daglig(self):
        """
        Månedlig rebalansering er tatt ut nettopp fordi den mistet effekten.
        Testen holder igjen på det som er igjen: hendelsesdrevet skal ikke
        være vesentlig svakere enn daglig når effekten varer 20 dager.
        """
        opp, kjop = _marked(self._mappe(), effekt_pst=6.0, fro=9)
        marked = P.Marked(kjop, opp)
        self.assertTrue(marked)
        m = {}
        for navn in ("daglig", "hendelse-20"):
            st = next(v for v in P.VARIANTER if v.navn == navn)
            e, _, _, _ = P.kjor_strategi(marked, st, opp)
            m[navn] = P.nokkeltall([float(r["Verdi_NOK"]) for r in e])["CAGR"]
        self.assertGreater(m["hendelse-20"], m["daglig"] * 0.8)

    def test_ingen_signaler_gir_kontanter(self):
        """Porteføljen skal ut av markedet når vinduet er tomt — og det synes."""
        opp, kjop = _marked(self._mappe(), effekt_pst=0.0, fro=3)
        marked = P.Marked(kjop, opp)
        st = P.Strategi("kort", takt="maaned", vindu_dager=1)
        equity, _, _, _ = P.kjor_strategi(marked, st, opp)
        self.assertTrue(any(int(r["Antall_Navn"]) == 0 for r in equity))

    def test_holder_aldri_flere_navn_enn_taket(self):
        opp, kjop = _marked(self._mappe(), effekt_pst=3.0, fro=17)
        opp.min_navn_portefolje = 3       # ellers blir taket på 3 uoppnåelig
        marked = P.Marked(kjop, opp)
        st = P.Strategi("tak", takt="dag", maks_navn=3, vindu_dager=365)
        equity, _, _, _ = P.kjor_strategi(marked, st, opp)
        self.assertLessEqual(max(int(r["Antall_Navn"]) for r in equity), 3)

    def test_filtrene_strammer_inn(self):
        """Hvert filter skal kunne avvise noe. Et filter som aldri biter, lyver."""
        opp, kjop = _marked(self._mappe(), effekt_pst=3.0, fro=23)
        marked = P.Marked(kjop, opp)
        i = marked.dager[len(marked.dager) // 2]
        aapen = P.Strategi("alt", takt="dag", vindu_dager=365)
        n_aapen = len(P._kandidater(marked, aapen, opp, i))
        for st in (P.Strategi("mom", takt="dag", vindu_dager=365,
                              momentum_dager=60, momentum_min=0.10),
                   P.Strategi("snu", takt="dag", vindu_dager=365,
                              snu_lang_dager=250, snu_lang_maks=-0.10,
                              snu_kort_dager=20, snu_kort_min=0.02),
                   P.Strategi("vol", takt="dag", vindu_dager=365, volum_faktor=2.0)):
            self.assertLessEqual(len(P._kandidater(marked, st, opp, i)), n_aapen,
                                 f"{st.navn} slapp gjennom flere enn uten filter")

    def test_vinduet_er_i_kalenderdager(self):
        opp, kjop = _marked(self._mappe(), fro=31)
        marked = P.Marked(kjop, opp)
        kort = P.Strategi("kort", takt="dag", vindu_dager=5)
        lang = P.Strategi("lang", takt="dag", vindu_dager=365)
        i = marked.dager[len(marked.dager) // 2]
        self.assertLessEqual(len(P._kandidater(marked, kort, opp, i)),
                             len(P._kandidater(marked, lang, opp, i)))


class Mailen(unittest.TestCase):
    """Mailen bygges av filene steg 6 skrev — aldri av tall som ligger løst."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.opp, kjop = _marked(Path(tmp.name), effekt_pst=4.0, fro=13)
        P.steg6_backtest(self.opp, P.stillelogger())

    def test_alle_variantene_er_med_med_beholdning_og_handler(self):
        html = P.bygg_epost(self.opp, [])
        self.assertTrue(html)
        for st in P.VARIANTER:
            self.assertIn(st.navn, html, f"{st.navn} mangler i mailen")
        self.assertIn("Beholdning", html)
        self.assertIn("Siste handler", html)
        self.assertIn("valgt strategi", html)
        # Advarslene skal aldri kunne falle ut av mailen i det stille.
        self.assertIn("Kapital ute", html)
        self.assertIn("Drag v/1,5 %", html)

    def test_de_fjernede_variantene_er_borte(self):
        navn = {v.navn for v in P.VARIANTER}
        for fjernet in ("basis", "ukentlig", "hendelse-60"):
            self.assertNotIn(fjernet, navn)

    def test_beholdningen_er_fra_siste_dag_strategien_eide_noe(self):
        rader = P.les_csv(self.opp.beholdning_csv)
        self.assertTrue(rader, "ingen beholdning skrevet")
        for r in rader:
            self.assertTrue(r["Dato"])
            self.assertTrue(r["Ticker"])
            self.assertGreater(float(r["Verdi_NOK"]), 0)

    def test_uten_passord_sendes_ingenting(self):
        from unittest.mock import patch
        self.opp.epost_passord = ""
        with patch.object(self.opp, 'passord_kandidater', return_value=[]):
            self.assertEqual(self.opp.les_passord(), "")
            self.assertFalse(P.send_epost(self.opp, "<p>x</p>", "test",
                                          P.stillelogger()))

    def test_passordet_kan_ligge_i_fil_utenfor_koden(self):
        self.opp.passordfil.write_text("abcd efgh ijkl mnop", encoding="utf-8")
        self.assertEqual(self.opp.les_passord(), "abcd efgh ijkl mnop")

    def test_ingen_hemmeligheter_i_kildefilen(self):
        kilde = (Path(__file__).resolve().parent /
                 "innsidehandel_pipeline.py").read_text(encoding="utf-8")
        self.assertEqual(P.Oppsett(base_dir=Path(".")).epost_passord, "")
        self.assertNotIn("cotm fppr", kilde)


class Konsentrasjon(unittest.TestCase):
    """
    Porteføljen skal aldri kunne stå med hele kapitalen i ÉN aksje.

    Uten taket målte backtesten det ene selskapet som tilfeldigvis var det
    eneste kvalifiserte, og kalte det et signal.
    """

    def _mappe(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name)

    def test_ingen_posisjon_over_taket(self):
        """
        Taket settes ved kjøp, ikke hver dag. En posisjon som stiger mens de
        andre faller vokser forbi 1/5 uten at noen har handlet — det er
        drift, ikke et brudd, og en holdestrategi skal ikke trimme daglig.
        Testen fanger det som betyr noe: at ingen kan nærme seg alt-i-én.
        """
        opp, kjop = _marked(self._mappe(), effekt_pst=4.0, fro=27)
        opp.min_navn_portefolje = 5
        tabell, _, _, _ = P.sammenlikn_strategier(kjop, opp, P.stillelogger())
        self.assertTrue(tabell)
        for r in tabell:
            self.assertLessEqual(float(r["Maks_Vekt_Pst"]), 40.0,
                                 f"{r['Strategi']} kom langt over taket på 1/5")

    def test_taket_kan_slaas_av(self):
        opp, kjop = _marked(self._mappe(), effekt_pst=4.0, fro=27)
        opp.min_navn_portefolje = 0
        marked = P.Marked(kjop, opp)
        st = next(v for v in P.VARIANTER if v.navn == "daglig")
        equity, _, _, _ = P.kjor_strategi(marked, st, opp)
        self.assertGreater(max(float(r["Storste_Vekt"]) for r in equity), 0.5)

    def test_pengene_som_ikke_investeres_blir_kontanter(self):
        """Taket skal gi kontanter, ikke tapte kroner. Regnskapet må gå opp."""
        opp, kjop = _marked(self._mappe(), effekt_pst=4.0, fro=27)
        opp.min_navn_portefolje = 5
        marked = P.Marked(kjop, opp)
        st = next(v for v in P.VARIANTER if v.navn == "daglig")
        equity, _, _, _ = P.kjor_strategi(marked, st, opp)
        for r in equity:
            self.assertGreater(float(r["Verdi_NOK"]), 0)
            self.assertLessEqual(float(r["Andel_Kapital"]), 1.0001)
        # Med taket på skal kapitalen som står ute være lavere enn uten.
        opp.min_navn_portefolje = 0
        uten, _, _, _ = P.kjor_strategi(marked, st, opp)
        med_snitt = sum(float(r["Andel_Kapital"]) for r in equity) / len(equity)
        uten_snitt = sum(float(r["Andel_Kapital"]) for r in uten) / len(uten)
        self.assertLess(med_snitt, uten_snitt)

    def test_median_navn_rapporteres_ikke_bare_snittet(self):
        opp, kjop = _marked(self._mappe(), effekt_pst=4.0, fro=27)
        tabell, _, _, _ = P.sammenlikn_strategier(kjop, opp, P.stillelogger())
        for r in tabell:
            self.assertIn("Median_Navn", r)
            self.assertIn("Dager_I_Kontanter_Pst", r)


class Beholdningsdagen(unittest.TestCase):
    """
    Mailen viste ÉN posisjon med 100 % vekt for ni av ti strategier, selv om
    medianen var ni navn. Grunnen: den valgte siste dag med noe i porteføljen
    — og det er alltid siste dag i nedtrappingen, når signalene er slutt.
    """

    def _mappe(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name)

    def test_beholdningen_hentes_fra_siste_handelsdag(self):
        opp, kjop = _marked(self._mappe(), effekt_pst=4.0, fro=19)
        opp.min_navn_portefolje = 5
        marked = P.Marked(kjop, opp)
        st = next(v for v in P.VARIANTER if v.navn == "daglig")
        equity, _, _, beholdning = P.kjor_strategi(marked, st, opp)
        aksjer = [b for b in beholdning if b["Ticker"] != "(kontanter)"]
        self.assertEqual(len(aksjer), int(equity[-1]['Antall_Navn']))
        self.assertTrue(all(b['Dato'] == equity[-1]['Dato'] for b in beholdning))

    def test_kontantene_er_med_saa_vektene_summerer_til_hundre(self):
        """Med faste plasser à 1/20 er resten av kapitalen kontanter."""
        opp, kjop = _marked(self._mappe(), effekt_pst=4.0, fro=19)
        marked = P.Marked(kjop, opp)
        st = P.Strategi("fast", takt="dag", hold_dager=20, kapitalbruk="fast",
                        maks_navn=20)
        _, _, _, beholdning = P.kjor_strategi(marked, st, opp)
        self.assertTrue(beholdning)
        self.assertIn("(kontanter)", [b["Ticker"] for b in beholdning])
        sum_vekt = sum(float(b["Andel_Pst"]) for b in beholdning)
        self.assertAlmostEqual(sum_vekt, 100.0, delta=1.0)
        for b in beholdning:
            self.assertLessEqual(float(b["Andel_Pst"]), 100.0)


class DagensListe(unittest.TestCase):
    """Det backtesten ikke kan svare på: hva kvalifiserer NÅ?"""

    def _data(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        opp, _ = _marked(Path(tmp.name), effekt_pst=4.0, fro=29)
        # Ferske meldinger uten fasit: nøyaktig det backtesten kaster.
        rader = P.les_csv(opp.hendelser_csv)
        kal = P.les_kalenderfil(opp.kalender_csv)
        for i in range(12):
            rader.append({
                "Melding_ID": f"NY{i}", "Dato": P.iso(kal[-3]),
                "Klokkeslett": "09:00", "Selskap": "T01.OL", "Ticker": "T01.OL",
                "Klasse": "KJOP", "Tillit": "HOY", "Bullish_Score": 88.0,
                "Primaer_I_Klynge": "JA", "Verdi_NOK": 250_000, "Rolle": "CEO"})
        P.skriv_csv(opp.hendelser_csv, rader, P.HENDELSE_KOLONNER)
        P.steg5_merge(opp, P.stillelogger())
        return opp, P.les_csv(opp.merget_csv)

    def test_ferske_meldinger_er_med_selv_om_backtesten_kastet_dem(self):
        opp, alle = self._data()
        ferske = [r for r in alle if r["Melding_ID"].startswith("NY")]
        self.assertTrue(ferske)
        # Backtesten kaster dem…
        self.assertNotIn("T01.OL", {r["Ticker"] for r in
                                    P.velg(ferske, opp, "KJOP")})
        # …dagens liste gjør det ikke.
        dagens = P.dagens_kandidater(alle, opp, P.stillelogger())
        self.assertIn("T01.OL", {r["Ticker"] for r in dagens})
        for r in dagens:
            self.assertTrue(r["Strategi"])
            self.assertNotEqual(r["Score"], "")

    def test_hver_strategi_faar_sin_egen_liste(self):
        opp, alle = self._data()
        dagens = P.dagens_kandidater(alle, opp, P.stillelogger())
        navn = {r["Strategi"] for r in dagens}
        self.assertTrue(navn.issubset({v.navn for v in P.VARIANTER}))


class Likviditetsscoren(unittest.TestCase):
    """En nøytral 50,0 skrevet over en ekte score gjorde hele scoren usynlig."""

    def test_ingen_justert_score_uten_signalstyrke(self):
        rad: dict = {}
        opp = P.Oppsett(base_dir=Path("."))
        P._likviditet(rad, opp, [10.0] * 30, [1000.0] * 30, 25,
                      {"Verdi_NOK": 50_000, "Bullish_Score": 80.0,
                       "Klasse": "KJOP"})
        self.assertNotIn("Score_Likviditetsjustert", rad)

    def test_justert_score_naar_styrken_finnes(self):
        rad: dict = {}
        opp = P.Oppsett(base_dir=Path("."))
        P._likviditet(rad, opp, [10.0] * 30, [1000.0] * 30, 25,
                      {"Verdi_NOK": 50_000, "Bullish_Score": 80.0,
                       "Signal_Styrke": 60.0, "Klasse": "KJOP"})
        self.assertGreater(float(rad["Score_Likviditetsjustert"]), 50.0)


class HelEllerTom(unittest.TestCase):
    """
    Kravet fra brukeren, gjort til en regel: en strategi eier enten minst
    min_navn selskaper, eller ingenting. Én posisjon er ikke en portefølje.
    """

    def _mappe(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name)

    def test_ingen_strategi_eier_mellom_1_og_min_navn(self):
        opp, kjop = _marked(self._mappe(), effekt_pst=4.0, fro=19)
        opp.min_navn_portefolje = 5
        marked = P.Marked(kjop, opp)
        for st in P.VARIANTER:
            equity, _, _, _ = P.kjor_strategi(marked, st, opp)
            tynne = [r for r in equity if 0 < int(r["Antall_Navn"]) < 5]
            if tynne:
                self.fail(f"{st.navn} eide {tynne[0]['Antall_Navn']} selskaper "
                          f"{tynne[0]['Dato']} — én aksje er ikke en portefølje")

    def test_beholdningen_i_mailen_er_aldri_en_enkelt_aksje(self):
        opp, kjop = _marked(self._mappe(), effekt_pst=4.0, fro=19)
        opp.min_navn_portefolje = 5
        P.steg6_backtest(opp, P.stillelogger())
        rader = P.les_csv(opp.beholdning_csv)
        per_strategi: dict = {}
        for r in rader:
            if r["Ticker"] != "(kontanter)":
                per_strategi.setdefault(r["Strategi"], []).append(r)
        self.assertTrue(rader, "ingen sluttbeholdning skrevet")
        curves = P.les_csv(opp.strategi_equity_csv)
        for r in rader:
            last = max(x['Dato'] for x in curves if x['Strategi'] == r['Strategi'])
            self.assertEqual(r['Dato'], last)
        for navn, aksjer in per_strategi.items():
            self.assertGreaterEqual(len(aksjer), 5,
                                    f"{navn} viser bare {len(aksjer)} aksje(r)")

    def test_taket_kan_senkes(self):
        opp, kjop = _marked(self._mappe(), effekt_pst=4.0, fro=19)
        opp.min_navn_portefolje = 2
        marked = P.Marked(kjop, opp)
        st = next(v for v in P.VARIANTER if v.navn == "daglig")
        equity, _, _, _ = P.kjor_strategi(marked, st, opp)
        self.assertTrue(any(int(r["Antall_Navn"]) in (2, 3, 4) for r in equity))
