def finnDødsboScraperv18(maks_annonser=None):
    """
    finn_dodsbo_scraper.py — v18.1

    ★ v18.1 — KUN ROBUSTHET (henting og deteksjon er UENDRET)
      Lange kjøringer (FINN_SIDE_CAP = 50) krasjet med Node-feilen
      "EPIPE" (broken pipe). Årsak: Fase 1 brukte SAMME Chromium for
      alle søkesider uten omstart, og til slutt døde den. Nå:
        - Fase 1 starter ny nettleser hver FASE1_RESTART_EVERY side.
        - Feiler en søkeside, startes ny nettleser og siden prøves på
          nytt (maks NAV_FORSOK ganger) før partisjonen gis opp.
        - Prispartisjoneringen starter ny nettleser før nytt forsøk.
        - Fase 2: kan ikke annonsen åpnes, startes ny nettleser og
          annonsen prøves én gang til.
      Den røde EPIPE-teksten kan fortsatt dukke opp i konsollen når
      en nettleser dør — det er den gamle hjelpeprosessen som klager.
      Skrapingen fortsetter med en ny.

    v18 GJØR ÉN TING: henter flere PDF-er enn v17.

    DETEKSJONEN ER IKKE RØRT. analyser_pdf_kontekst, _TV_POS,
    _DB_POS, _NEG_FELLES, _hent_setninger, _vurder, selger-feltene
    og egenerklæringslesingen er byte-identiske med v17. Ingen ny
    måte å vurdere signaler på, ingen nye regler, ingen scoring.
    Får v18 tak i samme PDF som v17, faller nøyaktig samme dom.
    tests/test_v18.py sammenligner kildekoden til deteksjonen
    tegn for tegn og feiler hvis noe har endret seg.

    ★ v18 — ENDRING 1: DIREKTE PDF PÅ FINN  (hovedfeilen)
      Advokatkontorer laster salgsoppgaven opp til FINN selv. Lenken
      peker da rett på PDF-en:
        https://images.finncdn.no/item/<finnkode>/file/<uuid>.pdf

      v17 FANT den lenken. Den ble så sendt til _handler_generisk,
      som starter med self._goto(megler_url). Chromium RENDRER ikke
      en PDF-URL — den laster den ned. page.goto() gir
      net::ERR_ABORTED, _goto() returnerer False, og handleren døde
      på "Kunne ikke åpne megler-side". PDF-en lå klar hele tiden.

      v17 HADDE en .pdf-sjekk, men den lå som SISTE steg i
      _handler_generisk — uoppnåelig, fordi _goto feilet på steg 1.

      Nå: er_direkte_pdf_url() kjenner igjen URL-en FØR handler
      velges, og _handler_direkte_pdf() henter den med
      _last_ned_pdf_url() — som allerede sender context-cookies og
      Referer. Ingen navigasjon, ingen cookie-runde på nytt.

    ★ v18 — ENDRING 2: EGEN RUTE FOR ADVOKATKONTOR
      Alt som ikke er en kjent kjede havnet i sekkeposten "annet".
      kjede_er_haplos() sperrer en kjede etter 40 forsøk med under
      5 % treff — så ett parti dårlige småmeglere kunne sperre HELE
      bøtta, advokatene inkludert. "advokat" og "direkte_pdf" er nå
      egne ruter i KJEDE_ALDRI_SPERR og kan ikke sperres.

    ★ v18 — ENDRING 3: UTVIDET LENKESØK (det robuste alternativet)
      _finn_megler_lenke() krever ordet "salgsoppgave"/"prospekt" i
      lenketeksten. Den beholdes UENDRET som førstevalg. Først når
      den gir None, kjøres _finn_pdf_lenke_utvidet(), som takler
      flere sideformater:
        - alle <a> som peker på .pdf, uansett lenketekst
        - knapper som heter "Dokumenter", "Vedlegg", "Prospekt"
        - PDF-er lagt inn i <iframe>, <embed> eller <object>
      Dette påvirker KUN hvilken fil som lastes ned, aldri hvordan
      innholdet tolkes.

    ── Ny kolonne ──
      pdf_url — hvor salgsoppgaven faktisk ble hentet fra, så du kan
                se hvilke treff som kom via de nye rutene.

    ── ARVET FRA v17, UENDRET ──

    ALT fra v15, men deteksjonen er skrevet om fra bunnen. v15 kunne
    merke en annonse som tvangssalg uten at ordet "tvangssalg" fantes
    i dokumentet i det hele tatt. Det skjer ikke lenger.

    ★ v16 — ENDRING 1: REN SETNINGSBASERT DETEKSJON
      v15 søkte etter mønstre i HELE dokumentteksten, slik at anker og
      påstandsramme kunne stå hundrevis av sider fra hverandre. Mønsteret
      r"rekvirent\\s*[:\\n]" traff derfor på feltetiketten "Rekvirent" i
      standard-headeren til enhver tilstandsrapport.

      Nå plukkes SETNINGEN ankerordet står i ut først, og dommen felles
      på den setningen alene. Et treff krever samtidig:
        (a) ANKERORD      — tvangssalg / tvangssolgt / medhjelpersalg
                            eller dødsbo / uskiftet bo
        (b) PÅSTANDSRAMME — "dette er et ...", "selges som ...",
                            "begjært ...", "besluttet ..."
        (c) INGEN DISKVALIFIKASJON i samme setning — "dersom", "kan
                            kreves", "hva er et ...", "ikke et ..."

      Konsekvenser:
        - ANTALL-TERSKELEN er fjernet i sin helhet. Ingen telling.
        - mulig_dodsbo / mulig_tvangssalg er fjernet. De var ren
          ordforekomst og ga bare støy.
        - AVKREFT er ikke lenger en GLOBAL bryter. I v15 slo ordet
          "borettslagsloven" ett sted i dokumentet av sikkerhetsnettet
          for hele filen. Nå dreper en generell lovsetning kun seg selv.
        - Nøkkelordsøk i tittel/annonsekort er fjernet.

    ★ v16 — ENDRING 2: ENCODING-REPARASJON
      PDF-er med ødelagt ToUnicode-CMap (Identity-H) gir tegn bitskiftet
      8 plasser: 't' (0x74) kommer ut som U+7400 '琀'. "Dette" leses som
      "De琀琀e". Ankerordet "tvangssalg" overlever tilfeldigvis, men
      påstandsrammen ryker. Skaden er reversibel og fikses nå i
      les_pdf_tekst(), slik at også adresseuttrekket blir riktigere.

    ★ v16 — ENDRING 3: VERDIVAKT PÅ SELGER-FELTET
      "\\bSelger\\s*[:\\n\\r]+" fanget setningsfragmenter som
      "Selger\\nhar likevel utarbeidet en egenerklæring ...". Hadde et
      slikt fragment inneholdt "tingretten", ville det gitt falsk
      positiv i den sterkeste deteksjonsruta. Feltverdier må nå se ut
      som verdier, ikke som setninger.

    ★ BEHOLDT UENDRET FRA v15
      - emnorge-retry med CloudFront-fallback.
      - All fartsoptimalisering (ett page.evaluate per side, throttlet
        checkpoint, ressursblokkering, kjedesperre, PDF-gjenbruk).
      - Egenerklæringslesing: skjemafelt -> vektorboks -> glyf -> tekst.
      - Prispartisjonering rundt Finns 2500-tak.
      - Sted/adresse fra FINN-detaljside -> PDF -> annonsekort.
      - Database, checkpoint, eksport, rapport.
    """

    import re
    import os
    import sys
    import time
    import json
    import logging
    import sqlite3
    import traceback
    import threading
    from pathlib import Path
    from collections import Counter
    from datetime import datetime, timezone
    from urllib.parse import urljoin
    from concurrent.futures import ThreadPoolExecutor, as_completed

    import pandas as pd
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

    # ══════════════════════════════════════════════
    # KONFIGURASJON
    # ══════════════════════════════════════════════
    DB_PATH               = "finn_dodsbo.db"
    CHECKPOINT_PATH       = "finn_scraper_checkpoint.json"
    PDF_STATS_PATH        = "finn_pdf_stats.json"
    BASE_URL              = "https://www.finn.no/realestate/homes/search.html"
    PDF_DIR               = "salgsoppgaver"
    EXCEL_DIR             = r"C:\Users\ander\Desktop\Python_K4\ExcelData\DataFinnDødsbo"

    # ── Fart ──────────────────────────────────────
    NUM_WORKERS           = 10
    SLEEP_BETWEEN         = 0.6
    DETAIL_WAIT           = 0.4
    PAGE_LOAD_WAIT        = 0.3
    NAV_TIMEOUT_MS        = 15_000
    STEP_TIMEOUT_MS       = 8_000
    PDF_LENKE_POLL_S      = 3.0
    PDF_DOWNLOAD_TIMEOUT  = 25
    BROWSER_RESTART_EVERY = 80
    CHECKPOINT_MIN_SEK    = 90
    BLOKKER_TUNGE_RESSURSER = True
    GJENBRUK_PDF          = True
    BRUK_KJEDESPERRE      = True
    KJEDE_MIN_FORSOK      = 40
    KJEDE_MIN_OK_RATE     = 0.05
    BRUK_GENERISK_FALLBACK = True
    EMNORGE_FORSOK        = 3

    # ★ v18.1 — robusthet mot nettleserkrasj (EPIPE)
    FASE1_RESTART_EVERY   = 100   # ny nettleser hver N-te søkeside i Fase 1
    NAV_FORSOK            = 3     # forsøk pr. søkeside, med ny nettleser mellom

    # ── Søk ───────────────────────────────────────
    FINN_SIDE_CAP         = 50 #5
    PRIS_MIN              = 0
    PRIS_MAKS             = 250_000_000
    PARTISJON_CAP         = 2400
    MIN_PRIS_SPENN        = 50_000
    TA_MED_UFILTRERT      = False

    # ── Analyse ───────────────────────────────────
    MAKS_ANNONSER         = maks_annonser
    KUN_TREFF_I_EXCEL     = True
    MAKS_PDF_SIDER        = 400

    # ★ v16: hvor mange tegn hver vei rundt ankerordet som regnes
    #        som "setningen" når det ikke finnes noe setningsskille.
    MAKS_SETNING          = 320

    # ★ v17: Skal "Rekvirent: X tingrett" i selger-feltet kunne gi
    # tvangssalg? Slått AV — v17 krever en eksplisitt setning, punktum.
    # Sett True hvis du vil ha feltruta tilbake (fanger tvangssalg der
    # megleren aldri skriver setningen, men er en ekstra risikoflate).
    BRUK_SELGERFELT_TVANGSSALG = False

    # ══════════════════════════════════════════════
    # ★ v18 — BRYTERE FOR PDF-HENTING
    # Alle gjelder KUN hvordan filen skaffes. Ingen av dem påvirker
    # hvordan innholdet tolkes. Settes alle til False, henter v18
    # nøyaktig de samme PDF-ene som v17.
    # ══════════════════════════════════════════════

    # Last ned direkte når lenken ER PDF-en (ikke naviger til den).
    BRUK_DIREKTE_PDF        = True
    # Verter der FINN selv hoster salgsoppgaven (advokatkontorer m.fl.)
    DIREKTE_PDF_VERTER      = ("images.finncdn.no", "finncdn.no")

    # Utvidet lenkesøk når det vanlige lenkesøket ikke finner noe.
    BRUK_UTVIDET_LENKESOK   = True
    # Se også i iframe/embed/object — noen meglersider bygger inn PDF-en
    # i stedet for å lenke til den.
    BRUK_INNBYGD_PDF_SOK    = True

    # Ruter som ALDRI skal kjedesperres. "direkte_pdf" er ingen
    # meglerkjede, og "advokat" er en sekkepost av småkontorer som
    # ellers ville dratt hverandre under 5 %-grensa.
    KJEDE_ALDRI_SPERR       = {"direkte_pdf", "advokat"}

    # Statuser som IKKE skal forsøkes på nytt ved omkjøring.
    # "pdf_ikke_funnet" er BEVISST utelatt -> de prøves på nytt.
    #FASE2_FERDIG_STATUS   = {"lastet_ned"}

    FASE2_FERDIG_STATUS   = {"lastet_ned"}

    # ══════════════════════════════════════════════
    # TRÅDSIKKERHET
    # ══════════════════════════════════════════════
    _cp_lock       = threading.Lock()
    _stats_lock    = threading.Lock()
    _listings_lock = threading.Lock()
    _cp_sist       = [0.0]
    _kjede_sperret = set()

    # ══════════════════════════════════════════════
    # LOGGING
    # ══════════════════════════════════════════════
    log = logging.getLogger("finn_scraper")
    log.setLevel(logging.INFO)
    log.handlers.clear()
    fmt = logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s",
                            datefmt="%H:%M:%S")
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    log.addHandler(ch)

    # ══════════════════════════════════════════════
    # ★ v16 — ENCODING-REPARASJON
    # ══════════════════════════════════════════════
    _SKADD = re.compile(r"[\u2000-\uFFFF]")

    def reparer_encoding(tekst):
        """
        Reverserer bitskift fra ødelagt ToUnicode-CMap.
        't' (0x74) -> U+7400 '琀', 'i' (0x69) -> U+6900 '椀'.
        Uten dette leses "Dette er et tvangssalg" som "De琀琀e er et
        tvangssalg" — ankerordet overlever, men rammen ryker.
        """
        if not tekst or not _SKADD.search(tekst):
            return tekst

        def bytt(m):
            kode = ord(m.group(0)) >> 8
            return chr(kode) if 0x20 <= kode <= 0x7E else m.group(0)

        return _SKADD.sub(bytt, tekst)

    # ══════════════════════════════════════════════
    # ★ v16 — ANKERORD OG SETNINGSREGLER
    # ══════════════════════════════════════════════
    # Setningsskille. Punktum splitter KUN når neste tegn er stor
    # bokstav eller siffer — ellers ryker setningen på "kap.", "nr.".
    _SETN_SLUTT = re.compile(
        r"(?<=[.!?;])[\s\u00a0]+(?=[A-ZÆØÅ0-9«])"
        r"|\n[ \t]*\n"
        r"|[•·▪]"
    )

    # ★ v17: KUN "tvangssalg". "tvangsauksjon" er fjernet — det ordet
    # lever nesten utelukkende videre i Kartverkets pantsettelsesskjema
    # ("kan pantsettes, samt overdras ved tvangsauksjon eller frivillig
    # salg"), som følger med HVER ENESTE salgsoppgave for festetomt.
    # "medhjelpersalg" er fjernet av samme grunn: for smalt utbytte,
    # for stor risiko.
    _ANKER_TVANG = re.compile(r"tvangssalg", re.I)
    _ANKER_DODSBO = re.compile(
        r"dødsbo|dodsbo|doedsbo|uskiftet[\s\u00a0]+bo", re.I)

    # ★ v17 — TVANGSSALG KREVER EN EKSPLISITT ERKLÆRING
    #
    # Kun to setningsformer godtas. Begge er direkte påstander om at
    # NETTOPP DETTE salget er et tvangssalg:
    #
    #   1. "Boligen selges som et tvangssalg"
    #      (også: eiendommen/leiligheten/hytta/objektet,
    #       selges/blir solgt/skal selges, som/ved, med/uten "et")
    #   2. "Dette er et tvangssalg"  /  "Salget er et tvangssalg"
    #
    # ALT annet er fjernet, bevisst:
    #   - "begjært tvangssalg"          (kan gjelde en annen eiendom)
    #   - "besluttet/stadfestet tvangssalg"
    #   - "oppnevnt som medhjelper"     (megleren, ikke salget)
    #   - "tvangsfullbyrdelsesloven § 11"
    #   - "etter reglene om tvangssalg"
    #   - "overdras ved tvangsauksjon"  (pantsettelsesskjema, festetomt)
    #
    # Prisen er dekning: et ekte tvangssalg som IKKE skriver setningen
    # rett ut, blir ikke fanget. Det er et bevisst bytte — en falsk
    # positiv på eier1.no koster mer enn et tapt treff.
    _TV_POS = [
        # "Boligen selges som et tvangssalg" / "Eiendommen selges ved tvangssalg"
        r"\b(boligen|eiendommen|leiligheten|hytta|hytten|objektet|seksjonen"
        r"|andelen|enheten|denne\s+(boligen|eiendommen|leiligheten))\s+"
        r"(selges|blir\s+solgt|skal\s+selges)\s+(som|ved)\s+"
        r"(et|ett|eit)?\s*tvangssalg\b",

        # "Dette er et tvangssalg" / "Salget er ett tvangssalg"
        r"\b(dette|salget|oppdraget)\s+er\s+(et|ett|eit)\s+tvangssalg\b",
    ]
    _DB_POS = [
        # "Selger er et dødsbo" / "Dette er ett dødsbo"
        r"\b(selger|selgeren|hjemmelshaver|oppdragsgiver|eier|boet|dette|det|salget"
        r"|eiendommen|boligen|leiligheten|objektet|hytta|hytten)\s+"
        r"(er|utgjør|gjelder)\s+(et|ett|eit)?\s*(dødsbo|dodsbo)\b",

        # "Boligen selges som dødsbo" / "selges fra et dødsbo"
        r"\b(selges|skal\s+selges|blir\s+solgt|avhendes|overdras|omsettes)\s+"
        r"(som|for|fra|av|på\s+vegne\s+av)\s+(et|ett|eit)?\s*(dødsbo|dodsbo)\b",

        # "Salget skjer som ledd i skifte av dødsbo"
        r"\b(som\s+)?ledd\s+i\s+(et\s+)?skifte\s+av\s+(et|ett)?\s*(dødsbo|dodsbo)\b",

        # "Dødsbo etter Kari Nordmann" — krever navn etter, ikke løst ord
        r"\b(dødsbo|dodsbo)(et)?\s+etter\s+(avdøde\s+)?[A-ZÆØÅ][a-zæøåA-ZÆØÅ\-]{2,}",

        # "Boet er under offentlig skifte"
        r"\bboet\s+(er|står)\s+under\s+(offentlig|privat)\s+skifte\b",

        # "Selger sitter i uskiftet bo"
        r"\b(sitter|satt|sitte)\s+i\s+uskiftet\s+bo\b",
        r"\b(selger|selgeren|hjemmelshaver)\s+(er|har)\s+.{0,30}uskiftet\s+bo\b",

        # "Selger har ikke bebodd eiendommen da dette er et dødsbo"
        r"\b(arvingene?|selger)\s+har\s+(ikke\s+)?(bebodd|bodd\s+i|kjennskap)"
        r"(?=[^.]{0,140}(dødsbo|dodsbo))",
    ]

    # Diskvalifiserende kontekst. Vurderes PER SETNING, aldri globalt.
    # Et generelt lovavsnitt dreper kun sin egen setning.
    _NEG_FELLES = [
        r"\bhva\s+(er|menes\s+med)\s+(et|ett)?\s*(tvangssalg|dødsbo)",
        r"\bgenerelt\s+(om|vedrørende)\b",
        r"\bdersom\b",
        r"\bhvis\b",
        r"\bskulle\s+(det|dette|eiendommen|boligen)\b",
        r"\bved\s+(vesentlig\s+)?mislighold\b",
        # ★ v16.1 MODALVAKT. Et modalverb gjør setningen hypotetisk:
        # "kan overdras ved tvangsauksjon" sier hva som KAN skje, ikke
        # hva dette salget ER. Bar "kan" er trygt fordi _vurder() går
        # gjennom ALLE ankersetninger — et ekte tvangssalg har flere.
        r"\bkan\b",
        r"\bkunne\b",
        # ★ v16.1 PANTSETTELSESERKLÆRING. Standardskjemaet for samtykke
        # fra hjemmelshaver/bortfester nevner tvangsauksjon rutinemessig.
        r"\bsamtykker?\b",
        r"\bpantsettes|\bpanthaver|\bpantedokument|\bpantsettelse",
        r"\bbortfester|\bfesteretten\b",
        r"\beller\s+frivillig\s+salg\b",
        r"\b(styret|sameiet|borettslaget|forretningsfører)\s+kan\b",
        r"\bborettslagsloven\b",
        r"\beierseksjonsloven\b",
        r"\bikke\s+(et|ett)?\s*(tvangssalg|dødsbo)\b",
        r"\bi\s+motsetning\s+til\b",
        r"\beksempel(vis)?\b",
        r"\bhverken\b",
    ]
    _NEG_TVANG = _NEG_FELLES + [
        r"\bpanteretten?\b(?=[^.]{0,80}\bkan\b)",
        r"\bmanglende\s+betaling\s+av\s+(felleskostnader|fellesutgifter)\b",
    ]
    _NEG_DODSBO = _NEG_FELLES + [
        r"\bved\s+(et\s+)?(senere\s+)?dødsfall\b",
        r"\bfremtidig(e)?\s+arv\b",
    ]

    _RX_TV_POS = [re.compile(p, re.I) for p in _TV_POS]
    _RX_DB_POS = [re.compile(p, re.I) for p in _DB_POS]
    _RX_TV_NEG = [re.compile(p, re.I) for p in _NEG_TVANG]
    _RX_DB_NEG = [re.compile(p, re.I) for p in _NEG_DODSBO]

    def _hent_setninger(tekst, anker_rx):
        """
        Returnerer setningene som faktisk inneholder et ankerord.

        En "setning" = teksten mellom nærmeste setningsskille før og
        etter ankeret, maks MAKS_SETNING tegn hver vei. Whitespace
        normaliseres, fordi PDF-uttrekk bryter linjer midt i setninger.
        """
        ut, sett = [], set()
        for m in anker_rx.finditer(tekst):
            lo = max(0, m.start() - MAKS_SETNING)
            hi = min(len(tekst), m.end() + MAKS_SETNING)
            for sep in _SETN_SLUTT.finditer(tekst, lo, m.start()):
                lo = sep.end()
            sep = _SETN_SLUTT.search(tekst, m.end(), hi)
            if sep:
                hi = sep.start()
            s = re.sub(r"[\s\u00a0]+", " ", tekst[lo:hi]).strip()
            if s and s.lower() not in sett:
                sett.add(s.lower())
                ut.append(s)
        return ut

    def _vurder(setninger, pos_rx, neg_rx):
        """(bekreftet, mønster, setning). Negasjon vurderes per setning."""
        for s in setninger:
            if any(r.search(s) for r in neg_rx):
                continue
            pos = next((r.pattern for r in pos_rx if r.search(s)), None)
            if pos:
                return True, pos, s
        return False, None, None

    # ══════════════════════════════════════════════
    # STED/ADRESSE-REGEX
    # ══════════════════════════════════════════════
    FULL_ADRESSE_RE = re.compile(
        r"([A-ZÆØÅ][^\n,]{2,58}?\s+\d{1,4}\s?[A-Za-z]?(?:\s*[-/]\s*\d{1,4}\s?[A-Za-z]?)?)"
        r"\s*,\s*(\d{4})\s+([A-ZÆØÅ][^\n,]{1,40})"
    )
    POSTNR_POSTSTED_RE = re.compile(
        r"\b(\d{4})\s+([A-ZÆØÅ][A-Za-zÆØÅæøå.\-]+(?:\s+[A-ZÆØÅ][A-Za-zÆØÅæøå.\-]+){0,2})"
    )
    GATE_SO_FLERLINJE_RE = re.compile(
        r"([A-ZÆØÅ][^\n,]{2,48}?\s+\d{1,4}\s?[A-Za-z]?)\s*[\n,]\s*(\d{4})\s+([A-ZÆØÅ][^\n,]{1,40})"
    )

    _SMULE_STOPP = (
        "logo", "bildegalleri", "galleribilde", "plantegning", "visning",
        "favoritt", "prisantydning", "nøkkelinfo", "om boligen", "annonse",
        "kart", "se ", "send", "gi bud", "lys og", "renoveringsobjekt",
        "innholdsrik", "se våre",
    )

    def _norm_ws(s):
        if not s:
            return s
        return (s.replace("\xa0", " ").replace("\u2009", " ")
                 .replace("\u202f", " ").replace("\u00ad", ""))

    def _rens_sted(s):
        return re.sub(r"\s+", " ", _norm_ws(s or "")).strip(" .,;:-")

    def _ser_ut_som_sted(s):
        if not s or len(s) > 32:
            return False
        low = s.lower()
        if any(stop in low for stop in _SMULE_STOPP):
            return False
        return bool(re.fullmatch(r"[A-ZÆØÅ][A-Za-zÆØÅæøå .\-]{1,31}", s))

    def _hent_brodsmuler(linjer):
        anker = None
        for i, l in enumerate(linjer):
            if l.strip().lower() == "bolig til salgs":
                anker = i
                break
        if anker is None:
            return None
        smuler = []
        for l in linjer[anker + 1: anker + 9]:
            s = l.strip()
            if not s:
                continue
            if not _ser_ut_som_sted(s):
                break
            smuler.append(s)
            if len(smuler) >= 3:
                break
        return smuler or None

    def parse_finn_sted(body):
        res = {"gateadresse": None, "postnr": None, "poststed": None,
               "fylke": None, "kommune": None, "omrade": None,
               "full_adresse": None}
        if not body:
            return res
        body = _norm_ws(body)
        linjer = body.splitlines()
        m = FULL_ADRESSE_RE.search(body)
        if m:
            gate = _rens_sted(m.group(1))
            res["gateadresse"] = gate
            res["postnr"] = m.group(2)
            res["poststed"] = _rens_sted(m.group(3))
            res["full_adresse"] = f"{gate}, {res['postnr']} {res['poststed']}"
        else:
            m2 = POSTNR_POSTSTED_RE.search(body)
            if m2:
                res["postnr"] = m2.group(1)
                res["poststed"] = _rens_sted(m2.group(2))
                res["full_adresse"] = f"{res['postnr']} {res['poststed']}"
        smuler = _hent_brodsmuler(linjer)
        if smuler:
            if len(smuler) >= 1: res["fylke"] = smuler[0]
            if len(smuler) >= 2: res["kommune"] = smuler[1]
            if len(smuler) >= 3: res["omrade"] = smuler[2]
        return res

    def parse_finn_detalj_felt(body):
        out = {"property_type": None, "ownership": None,
               "bedrooms": None, "size_m2": None}
        if not body:
            return out
        body = _norm_ws(body)

        def etter(label):
            m = re.search(r"(?m)^\s*" + re.escape(label) + r"\s*$\n\s*([^\n]+)", body)
            return m.group(1).strip() if m else None

        bt = etter("Boligtype")
        if bt and len(bt) < 40:
            out["property_type"] = bt
        ef = etter("Eieform")
        if ef and len(ef) < 40:
            out["ownership"] = ef
        sov = etter("Soverom")
        if sov and sov.strip().isdigit():
            out["bedrooms"] = sov.strip()
        m_bra = re.search(r"(?m)^\s*Bruksareal\s*$\n\s*(\d[\d\s]*)\s*m²", body)
        if m_bra:
            out["size_m2"] = re.sub(r"\D", "", m_bra.group(1))
        return out

    def hent_sted_fra_pdf(pdf_tekst):
        res = {"gateadresse": None, "postnr": None, "poststed": None,
               "full_adresse": None}
        if not pdf_tekst:
            return res
        t = _norm_ws(pdf_tekst[:200_000])
        par = [(p, _rens_sted(s)) for p, s in POSTNR_POSTSTED_RE.findall(t)]
        if not par:
            return res
        best = Counter(par).most_common(1)[0][0]
        res["postnr"], res["poststed"] = best[0], best[1]
        m = GATE_SO_FLERLINJE_RE.search(t)
        if m and m.group(2) == best[0]:
            res["gateadresse"] = _rens_sted(m.group(1))
            res["full_adresse"] = f"{res['gateadresse']}, {best[0]} {best[1]}"
        else:
            res["full_adresse"] = f"{best[0]} {best[1]}"
        return res

    def parse_kort_sted(text):
        res = {"gateadresse": None, "postnr": None, "poststed": None,
               "full_adresse": None}
        if not text:
            return res
        t = _norm_ws(text)
        m = FULL_ADRESSE_RE.search(t)
        if m:
            res["gateadresse"] = _rens_sted(m.group(1))
            res["postnr"] = m.group(2)
            res["poststed"] = _rens_sted(m.group(3))
            res["full_adresse"] = f"{res['gateadresse']}, {res['postnr']} {res['poststed']}"
        else:
            m2 = POSTNR_POSTSTED_RE.search(t)
            if m2:
                res["postnr"] = m2.group(1)
                res["poststed"] = _rens_sted(m2.group(2))
                res["full_adresse"] = f"{res['postnr']} {res['poststed']}"
        return res

    def bygg_sok_url(pris_lo=None, pris_hi=None, side=1):
        deler = []
        if pris_lo is not None: deler.append(f"price_from={pris_lo}")
        if pris_hi is not None: deler.append(f"price_to={pris_hi}")
        if side and side > 1:   deler.append(f"page={side}")
        q = "&".join(deler)
        return BASE_URL + (f"?{q}" if q else "")

    # ══════════════════════════════════════════════
    # PDF-STATS + KJEDESPERRE
    # ══════════════════════════════════════════════
    pdf_stats = {"per_kjede": {}, "epost_vegg_eks": [], "sperrede_kjeder": []}

    def _stats_bump(kjede, felt):
        with _stats_lock:
            d = pdf_stats["per_kjede"].setdefault(
                kjede, {"forsokt": 0, "ok": 0, "feil": 0, "epost_vegg": 0})
            d[felt] = d.get(felt, 0) + 1

    def save_pdf_stats():
        with _stats_lock:
            try:
                with open(PDF_STATS_PATH, "w", encoding="utf-8") as f:
                    json.dump(pdf_stats, f, ensure_ascii=False, indent=2)
            except Exception as e:
                log.debug("Kunne ikke lagre pdf_stats: %s", e)

    def kjede_er_haplos(kjede):
        if not BRUK_KJEDESPERRE:
            return False
        # ★ v18: direkte_pdf og advokat er ruter, ikke kjeder. De skal
        # aldri kunne slå seg selv av.
        if kjede in KJEDE_ALDRI_SPERR:
            return False
        if kjede in _kjede_sperret:
            return True
        with _stats_lock:
            d = pdf_stats["per_kjede"].get(kjede)
            forsokt = d.get("forsokt", 0) if d else 0
            ok = d.get("ok", 0) if d else 0
        if forsokt >= KJEDE_MIN_FORSOK and (ok / forsokt) < KJEDE_MIN_OK_RATE:
            _kjede_sperret.add(kjede)
            with _stats_lock:
                if kjede not in pdf_stats["sperrede_kjeder"]:
                    pdf_stats["sperrede_kjeder"].append(kjede)
            log.warning("⛔ Sperrer kjede '%s' (%d forsøk, kun %d ok)",
                        kjede, forsokt, ok)
            return True
        return False

    # ══════════════════════════════════════════════
    # ★ v16 — SELGER-FELT MED VERDIVAKT
    # ══════════════════════════════════════════════
    _SELGER_PATTERNS = [
        (re.compile(r"SELGER\s*[:\n\r]+\s*([^\n\r]{3,200})"), "SELGER"),
        (re.compile(r"\bSelger\s*[:\n\r]+\s*([^\n\r]{3,200})"), "Selger"),
        (re.compile(r"OPPDRAGSGIVER\s*[:\n\r]+\s*([^\n\r]{3,200})"), "Oppdragsgiver"),
        (re.compile(r"\bOppdragsgiver\s*[:\n\r]+\s*([^\n\r]{3,200})"), "Oppdragsgiver"),
        (re.compile(r"HJEMMELSHAVER\s*[:\n\r]+\s*([^\n\r]{3,200})"), "Hjemmelshaver"),
        (re.compile(r"\bHjemmelshaver\s*[:\n\r]+\s*([^\n\r]{3,200})"), "Hjemmelshaver"),
        (re.compile(r"REKVIRENT\s*[:\n\r]+\s*([^\n\r]{3,200})"), "Rekvirent"),
        (re.compile(r"\bRekvirent\s*[:\n\r]+\s*([^\n\r]{3,200})"), "Rekvirent"),
    ]

    # Forkaster setningsfragmenter som "Selger\nhar likevel utarbeidet
    # en egenerklæring ...". Uten denne kan en tilfeldig setning som
    # starter med "Selger" og nevner "tingretten" gi falsk positiv i
    # den sterkeste deteksjonsruta.
    _FELT_VERB = re.compile(
        r"^(har|hadde|er|var|kan|kunne|skal|skulle|vil|ville|bør|må|gjør|gjøres"
        r"|opplyser|opplyste|bes|ønsker|kjenner|plikter|forutsettes|anbefales"
        r"|oppfordres|garanterer|fraskriver|selger|overtar|leverer)\b", re.I)

    def _ser_ut_som_feltverdi(v):
        v = (v or "").strip()
        if not (3 <= len(v) <= 120):
            return False
        if _FELT_VERB.match(v):
            return False
        if v.count(" ") > 12:
            return False
        return True

    def hent_selger_felt(tekst):
        funn, seen = [], set()
        for rx, navn in _SELGER_PATTERNS:
            for m in rx.finditer(tekst):
                verdi = m.group(1).strip()
                if not _ser_ut_som_feltverdi(verdi):
                    continue
                key = verdi.lower()[:80]
                if key in seen:
                    continue
                seen.add(key)
                funn.append((navn, verdi))
        return funn

    _DODSBO_SELGER_RE = re.compile(
        r"\bdødsbo|\bdodsbo|\buskiftet\s+bo\b|^boet\s+etter\s+", re.I)

    def selger_indikerer_dodsbo(felter):
        for feltnavn, verdi in felter:
            if _DODSBO_SELGER_RE.search(verdi):
                return True, f"{feltnavn}-felt: '{verdi[:100]}'"
        return False, None

    _TVANGS_SELGER_RE = re.compile(
        r"\btingrett(en|s)?\b|\bbyfogd|\bnamsfogd|\bnamsmann|\bnamsrett|"
        r"\bkonkursbo(et)?\b|\bbostyrer\b|\bbobestyrer\b|\bmedhjelper\b", re.I)

    def selger_indikerer_tvangssalg(felter):
        for feltnavn, verdi in felter:
            if _TVANGS_SELGER_RE.search(verdi):
                return True, f"{feltnavn}-felt: '{verdi[:100]}'"
        return False, None

    # ══════════════════════════════════════════════
    # EGENERKLÆRING (kun dødsbo — finnes ikke ved tvangssalg)
    # ══════════════════════════════════════════════
    _CHECKED_GLYFER = set("☑☒☓■▪✓✔✗✘")
    _EMPTY_GLYFER   = set("☐◻□▢")

    _EGEN_TEKST_JA = [
        re.compile(r"spørsmålene\s+i\s+egenerklæring(en)?\s+(er\s+)?ikke\s+(er\s+)?(utfylt|besvart)[^.]{0,80}dødsbo"),
        re.compile(r"egenerklæring(en)?\s+(er\s+)?ikke\s+(er\s+)?utfylt[^.]{0,80}dødsbo"),
        re.compile(r"(salget|boligen|dette)\s+(er\s+)?(et\s+)?dødsbo[^.]{0,40}egenerklæring"),
        re.compile(r"selger\s+er\s+et\s+dødsbo"),
        re.compile(r"boligen\s+selges\s+som\s+(et\s+)?dødsbo"),
        re.compile(r"salget\s+er\s+et\s+dødsbo"),
    ]

    def _res(er_dodsbo, begrunnelse):
        return {"funnet": True, "er_dodsbo": er_dodsbo,
                "begrunnelse": begrunnelse, "tvetydig": False}

    def _amb(begrunnelse):
        return {"funnet": True, "er_dodsbo": None,
                "begrunnelse": begrunnelse, "tvetydig": True}

    def _finn_dodsbo_sporsmaal(words):
        n = len(words)
        for i, w in enumerate(words):
            ord_ = (w[4] or "").lower().strip(" ?:.,")
            if "dødsbo" in ord_ or "dodsbo" in ord_:
                kontekst = " ".join(
                    (words[j][4] or "").lower()
                    for j in range(max(0, i - 3), min(n, i + 2)))
                if "er det" in kontekst or "?" in (w[4] or "") or "?" in kontekst:
                    return (w[0], w[1], w[2], w[3])
        return None

    def _finn_ja_nei(words, q_rect):
        qx0, qy0, qx1, qy1 = q_rect
        y_lo, y_hi = qy0 - 6, qy1 + 70
        ja_kand, nei_kand = [], []
        for w in words:
            ord_ = (w[4] or "").lower().strip(" ?:.,")
            if ord_ not in ("ja", "nei"):
                continue
            wy = (w[1] + w[3]) / 2
            if not (y_lo <= wy <= y_hi):
                continue
            (ja_kand if ord_ == "ja" else nei_kand).append(w)
        if not ja_kand or not nei_kand:
            return None, None

        def naer(w):
            cx = (w[0] + w[2]) / 2
            cy = (w[1] + w[3]) / 2
            return ((cx - qx0) ** 2 + (cy - qy1) ** 2) ** 0.5

        ja = min(ja_kand, key=naer)
        nei = min(nei_kand, key=naer)
        jc = (ja[1] + ja[3]) / 2
        nc = (nei[1] + nei[3]) / 2
        if abs(jc - nc) > 40 and abs(ja[0] - nei[0]) > 400:
            return None, None
        return (ja[0], ja[1], ja[2], ja[3]), (nei[0], nei[1], nei[2], nei[3])

    def _ink_ratio(page, rect):
        try:
            import fitz
            r = fitz.Rect(rect)
            if r.is_empty or r.width <= 1 or r.height <= 1:
                return 0.0
            pix = page.get_pixmap(matrix=fitz.Matrix(6.0, 6.0), clip=r,
                                  colorspace=fitz.csGRAY, alpha=False)
            data = pix.samples
            if not data:
                return 0.0
            return sum(1 for b in data if b < 128) / len(data)
        except Exception:
            return 0.0

    def _avgjor_via_widgets(page, ja_rect, nei_rect):
        try:
            import fitz
            widgets = list(page.widgets() or [])
        except Exception:
            return None
        if not widgets:
            return None
        checkbox_type = getattr(fitz, "PDF_WIDGET_TYPE_CHECKBOX", 2)
        radio_type = getattr(fitz, "PDF_WIDGET_TYPE_RADIOBUTTON", 5)
        bokser = []
        for w in widgets:
            try:
                if getattr(w, "field_type", None) not in (checkbox_type, radio_type):
                    continue
                on = str(w.field_value).lower() not in ("", "off", "no", "0", "false", "none")
                bokser.append((w.rect, on))
            except Exception:
                continue
        if not bokser:
            return None

        def naermest(label_rect):
            lx = (label_rect[0] + label_rect[2]) / 2
            ly = (label_rect[1] + label_rect[3]) / 2
            best, bd = None, float("inf")
            for rect, on in bokser:
                cx = (rect.x0 + rect.x1) / 2
                cy = (rect.y0 + rect.y1) / 2
                d = ((cx - lx) ** 2 + (cy - ly) ** 2) ** 0.5
                if d < bd:
                    bd, best = d, (on, d)
            return best

        ja_b, nei_b = naermest(ja_rect), naermest(nei_rect)
        if not ja_b or not nei_b:
            return None
        if ja_b[1] > 60 or nei_b[1] > 60:
            return None
        ja_on, nei_on = ja_b[0], nei_b[0]
        if ja_on and not nei_on:
            return _res(True, "Egenerklæring (skjemafelt): 'Ja' avkrysset")
        if nei_on and not ja_on:
            return _res(False, "Egenerklæring (skjemafelt): 'Nei' avkrysset")
        if ja_on and nei_on:
            return _amb("Egenerklæring (skjemafelt): både Ja og Nei avkrysset")
        return None

    def _hent_drawings(page):
        try:
            return page.get_drawings() or []
        except Exception:
            return []

    def _fill_er_mork(fill):
        if not fill:
            return False
        try:
            vals = list(fill)
            return bool(vals) and (sum(vals) / len(vals)) < 0.5
        except Exception:
            return False

    def _vektor_bokser(drawings):
        import fitz
        bokser = []
        for d in drawings:
            r = d.get("rect")
            if r is None:
                continue
            w, h = r.width, r.height
            if w <= 0 or h <= 0:
                continue
            if 4 <= w <= 26 and 4 <= h <= 26 and 0.55 <= (w / h) <= 1.8:
                bokser.append((fitz.Rect(r), d.get("fill")))
        return bokser

    def _boks_naer_label(bokser, label_rect, maks=46):
        lx0, ly0, lx1, ly1 = label_rect
        lcy = (ly0 + ly1) / 2
        h = max(ly1 - ly0, 6)
        best, bd = None, maks
        for rect, fill in bokser:
            bcy = (rect.y0 + rect.y1) / 2
            if abs(bcy - lcy) > h * 0.9 + 4:
                continue
            d = min(abs(rect.x1 - lx0), abs(rect.x0 - lx1))
            if d < bd:
                bd, best = d, (rect, fill)
        return best

    def _boks_har_vektormerke(drawings, box_rect):
        import fitz
        w, h = box_rect.width, box_rect.height
        inset = max(1.0, 0.18 * min(w, h))
        inner = fitz.Rect(box_rect.x0 + inset, box_rect.y0 + inset,
                          box_rect.x1 - inset, box_rect.y1 - inset)
        if inner.is_empty or inner.width <= 0 or inner.height <= 0:
            return False
        for d in drawings:
            for item in d.get("items", []):
                typ = item[0]
                pts = []
                try:
                    if typ == "l":
                        pts = [item[1], item[2]]
                    elif typ == "c":
                        pts = [item[1], item[2], item[3], item[4]]
                    elif typ == "qu":
                        q = item[1]
                        pts = [q.ul, q.ur, q.ll, q.lr]
                    elif typ == "re":
                        rr = fitz.Rect(item[1])
                        if (rr.width < w * 0.92 and rr.height < h * 0.92
                                and inner.intersects(rr)):
                            return True
                        continue
                except Exception:
                    continue
                for p in pts:
                    try:
                        if inner.contains(fitz.Point(p)):
                            return True
                    except Exception:
                        pass
        return False

    def _avgjor_via_vektorbokser(page, drawings, ja_rect, nei_rect):
        bokser = _vektor_bokser(drawings)
        if not bokser:
            return None
        ja = _boks_naer_label(bokser, ja_rect)
        nei = _boks_naer_label(bokser, nei_rect)
        if not ja or not nei:
            return None
        ja_box, ja_fill = ja
        nei_box, nei_fill = nei

        def markert(box, fill):
            return _fill_er_mork(fill) or _boks_har_vektormerke(drawings, box)

        ja_m, nei_m = markert(ja_box, ja_fill), markert(nei_box, nei_fill)
        if ja_m and not nei_m:
            return _res(True, "Egenerklæring (vektorboks): 'Ja' avkrysset")
        if nei_m and not ja_m:
            return _res(False, "Egenerklæring (vektorboks): 'Nei' avkrysset")
        if ja_m and nei_m:
            return _amb("Egenerklæring (vektorboks): både Ja og Nei markert")
        ja_ink = _ink_ratio(page, (ja_box.x0, ja_box.y0, ja_box.x1, ja_box.y1))
        nei_ink = _ink_ratio(page, (nei_box.x0, nei_box.y0, nei_box.x1, nei_box.y1))
        hoy, lav = max(ja_ink, nei_ink), min(ja_ink, nei_ink)
        diff = ja_ink - nei_ink
        if abs(diff) >= 0.05 and hoy >= 0.10 and (hoy / (lav + 1e-6)) >= 1.4:
            if diff > 0:
                return _res(True, f"Egenerklæring (boks-ink): 'Ja' "
                                  f"(ink {ja_ink:.3f} > {nei_ink:.3f})")
            return _res(False, f"Egenerklæring (boks-ink): 'Nei' "
                               f"(ink {nei_ink:.3f} > {ja_ink:.3f})")
        return _amb(f"Egenerklæring tvetydig (begge bokser tomme/like, "
                    f"ink {ja_ink:.3f}/{nei_ink:.3f})")

    def _avgjor_via_glyfer(words, ja_rect, nei_rect):
        def merke_for(label_rect):
            lx0, ly0, lx1, ly1 = label_rect
            lcy = (ly0 + ly1) / 2
            h = max(ly1 - ly0, 6)
            best, bd = None, h * 2.5 + 8
            for w in words:
                t = (w[4] or "").strip()
                if len(t) != 1:
                    continue
                if t not in _CHECKED_GLYFER and t not in _EMPTY_GLYFER:
                    continue
                wcy = (w[1] + w[3]) / 2
                if abs(wcy - lcy) > h * 0.9:
                    continue
                d = min(abs(w[2] - lx0), abs(w[0] - lx1))
                if d < bd:
                    bd = d
                    best = "checked" if t in _CHECKED_GLYFER else "empty"
            return best

        ja, nei = merke_for(ja_rect), merke_for(nei_rect)
        if ja == "checked" and nei != "checked":
            return _res(True, "Egenerklæring (glyf): 'Ja' avkrysset")
        if nei == "checked" and ja != "checked":
            return _res(False, "Egenerklæring (glyf): 'Nei' avkrysset")
        if ja == "checked" and nei == "checked":
            return _amb("Egenerklæring (glyf): både Ja og Nei avkrysset")
        return None

    def _egenerklaering_tekst_svar(tl):
        if not tl:
            return None
        if re.search(r"selger\s+er\s+et\s+dødsbo", tl):
            return _res(True, "Egenerklæring (tekst): 'Selger er et dødsbo'")
        if "egenerklæring" not in tl and "egenerklaering" not in tl:
            return None
        for rx in _EGEN_TEKST_JA:
            if rx.search(tl):
                return _res(True, "Egenerklæring (tekst): dødsbo bekreftet i skjema")
        return None

    def les_egenerklaering_dodsbo(pdf_path, tekst_lower):
        if not pdf_path or not tekst_lower:
            return None
        if "dødsbo" not in tekst_lower and "dodsbo" not in tekst_lower:
            return None
        try:
            import fitz
        except ImportError:
            return None
        try:
            doc = fitz.open(pdf_path)
        except Exception:
            return None
        sikker = tvetydig = None
        try:
            for pno in range(min(doc.page_count, MAKS_PDF_SIDER)):
                try:
                    page = doc[pno]
                    # ★ v16: samme encoding-reparasjon som i les_pdf_tekst
                    sidetekst = reparer_encoding(page.get_text())
                except Exception:
                    continue
                sl = sidetekst.lower()
                if "dødsbo" not in sl and "dodsbo" not in sl:
                    continue
                try:
                    words = page.get_text("words")
                except Exception:
                    words = []
                if not words:
                    continue
                q_rect = _finn_dodsbo_sporsmaal(words)
                if q_rect is None:
                    continue
                ja_rect, nei_rect = _finn_ja_nei(words, q_rect)
                if ja_rect is None or nei_rect is None:
                    tvetydig = tvetydig or _amb(
                        "Spørsmål funnet, men ingen klar Ja/Nei-struktur")
                    continue
                drawings = _hent_drawings(page)
                kandidat = (_avgjor_via_widgets(page, ja_rect, nei_rect)
                            or _avgjor_via_vektorbokser(page, drawings, ja_rect, nei_rect)
                            or _avgjor_via_glyfer(words, ja_rect, nei_rect))
                if kandidat is None:
                    tvetydig = tvetydig or _amb(
                        "Egenerklæring funnet, men avkrysning kunne ikke leses sikkert")
                    continue
                if kandidat["er_dodsbo"] in (True, False):
                    sikker = kandidat
                    break
                tvetydig = tvetydig or kandidat
        finally:
            try:
                doc.close()
            except Exception:
                pass
        if sikker is not None:
            return sikker
        return _egenerklaering_tekst_svar(tekst_lower) or tvetydig

    # ══════════════════════════════════════════════
    # ★ v16 — HOVEDANALYSE (kun setninger og feltverdier)
    # ══════════════════════════════════════════════
    def analyser_pdf_kontekst(tekst, pdf_path=None):
        """
        Tre ruter, første treff vinner pr. kategori:

          1. SELGER-/hjemmelshaver-/rekvirentfelt (strukturert verdi)
          2. BEKREFTENDE SETNING (anker + påstandsramme, negasjon
             vurdert i samme setning)
          3. EGENERKLÆRING (kun dødsbo, avkrysningsboks)

        Ingen ordtelling. Et ankerord uten påstandsramme gir ingenting.
        """
        result = {
            "er_dodsbo": False, "er_tvangssalg": False,
            "treff_ord": [], "begrunnelse": [], "kontekst_sample": None,
            "signal_kilde": [],
        }

        if not tekst or len(tekst) < 100:
            result["begrunnelse"] = "PDF-tekst tom eller for kort"
            result["signal_kilde"] = None
            result["treff_ord"] = None
            return result

        tekst = reparer_encoding(tekst)

        # ── 1. SELGER-FELT ────────────────────────────────
        felter = hent_selger_felt(tekst)

        ok, begr = selger_indikerer_dodsbo(felter)
        if ok:
            result["er_dodsbo"] = True
            result["treff_ord"].append("dødsbo")
            result["begrunnelse"].append(f"✓ {begr}")
            result["signal_kilde"].append("selger_felt")
            result["kontekst_sample"] = begr[:400]

        ok, begr = ((False, None) if not BRUK_SELGERFELT_TVANGSSALG
                    else selger_indikerer_tvangssalg(felter))
        if ok:
            result["er_tvangssalg"] = True
            if "tvangssalg" not in result["treff_ord"]:
                result["treff_ord"].append("tvangssalg")
            result["begrunnelse"].append(f"✓ {begr}")
            result["signal_kilde"].append("selger_felt_tvangssalg")
            if not result["kontekst_sample"]:
                result["kontekst_sample"] = begr[:400]

        # ── 2. BEKREFTENDE SETNING ────────────────────────
        if not result["er_tvangssalg"]:
            traff, pat, setning = _vurder(
                _hent_setninger(tekst, _ANKER_TVANG), _RX_TV_POS, _RX_TV_NEG)
            if traff:
                result["er_tvangssalg"] = True
                if "tvangssalg" not in result["treff_ord"]:
                    result["treff_ord"].append("tvangssalg")
                result["begrunnelse"].append(
                    f"✓ setning bekrefter tvangssalg: {pat}")
                result["signal_kilde"].append("setning_tvangssalg")
                if not result["kontekst_sample"]:
                    result["kontekst_sample"] = setning[:500]

        if not result["er_dodsbo"]:
            traff, pat, setning = _vurder(
                _hent_setninger(tekst, _ANKER_DODSBO), _RX_DB_POS, _RX_DB_NEG)
            if traff:
                result["er_dodsbo"] = True
                if "dødsbo" not in result["treff_ord"]:
                    result["treff_ord"].append("dødsbo")
                result["begrunnelse"].append(
                    f"✓ setning bekrefter dødsbo: {pat}")
                result["signal_kilde"].append("setning_dodsbo")
                if not result["kontekst_sample"]:
                    result["kontekst_sample"] = setning[:500]

        # ── 3. EGENERKLÆRING (kun dødsbo) ─────────────────
        if not result["er_dodsbo"] and pdf_path:
            egen = les_egenerklaering_dodsbo(pdf_path, tekst.lower())
            if egen and egen.get("funnet") and egen.get("er_dodsbo") is True:
                result["er_dodsbo"] = True
                if "dødsbo" not in result["treff_ord"]:
                    result["treff_ord"].append("dødsbo")
                result["begrunnelse"].append(egen["begrunnelse"])
                result["signal_kilde"].append("egenerklaering")

        result["signal_kilde"] = ", ".join(result["signal_kilde"]) or None
        result["begrunnelse"] = " | ".join(result["begrunnelse"]) or "Ingen treff"
        return result

    def beregn_kategori(l):
        d = int(l.get("er_dodsbo") or 0) == 1
        t = int(l.get("er_tvangssalg") or 0) == 1
        if d and t: return "dodsbo_tvangssalg"
        if d:       return "dodsbo"
        if t:       return "tvangssalg"
        return "vanlig"

    # ══════════════════════════════════════════════
    # DATABASE
    # Robust oppstart. "disk I/O error" på CREATE TABLE skyldes nesten
    # alltid MILJØET, ikke koden:
    #   1. Mappa er OneDrive/Dropbox-synkronisert (Skrivebordet!)
    #   2. Stale .db-wal / .db-shm etter en krasj
    #   3. Skrivebeskyttet mappe / full disk
    # Prøves i tur: WAL -> rydd wal/shm -> journal_mode=DELETE -> LOCALAPPDATA
    #
    # Merk: mulig_dodsbo/mulig_tvangssalg beholdes i skjemaet selv om
    # v16 aldri setter dem. Da slipper du migrering av eksisterende base.
    # ══════════════════════════════════════════════
    _db_valgt_sti = [None]
    _db_bruk_wal  = [True]

    def _db_kandidatstier():
        """Stier å prøve, i prioritert rekkefølge."""
        stier = []
        primar = DB_PATH if os.path.isabs(DB_PATH) else os.path.abspath(DB_PATH)
        stier.append(primar)
        lokal = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_CACHE_HOME")
        if lokal:
            stier.append(os.path.join(lokal, "finn_dodsbo", os.path.basename(primar)))
        try:
            stier.append(os.path.join(os.path.expanduser("~"),
                                      ".finn_dodsbo", os.path.basename(primar)))
        except Exception:
            pass
        try:
            import tempfile
            stier.append(os.path.join(tempfile.gettempdir(), os.path.basename(primar)))
        except Exception:
            pass
        sett, ut = set(), []
        for s in stier:
            if s not in sett:
                sett.add(s)
                ut.append(s)
        return ut

    def _rydd_stale_wal(sti):
        """Fjerner -wal/-shm som er blitt liggende etter en krasj."""
        fjernet = []
        for suffix in ("-wal", "-shm"):
            f = sti + suffix
            try:
                if os.path.exists(f):
                    os.remove(f)
                    fjernet.append(os.path.basename(f))
            except Exception:
                pass
        return fjernet

    def _prov_tilkobling(sti, bruk_wal):
        """Åpner DB og gjør en EKTE skrivetest. Returnerer conn eller None."""
        conn = None
        try:
            mappe = os.path.dirname(sti)
            if mappe:
                os.makedirs(mappe, exist_ok=True)
            conn = sqlite3.connect(sti, check_same_thread=False, timeout=30)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA busy_timeout=30000")
            try:
                conn.execute("PRAGMA journal_mode=" + ("WAL" if bruk_wal else "DELETE"))
            except sqlite3.DatabaseError:
                if bruk_wal:
                    conn.close()
                    return None
            try:
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA cache_size=-40000")
            except Exception:
                pass
            # ── EKTE skrivetest: her slår "disk I/O error" til ──
            conn.execute("CREATE TABLE IF NOT EXISTS _skrivetest (x INTEGER)")
            conn.execute("INSERT INTO _skrivetest (x) VALUES (1)")
            conn.execute("DROP TABLE _skrivetest")
            conn.commit()
            return conn
        except sqlite3.DatabaseError as e:
            try:
                if conn: conn.close()
            except Exception:
                pass
            log.debug("DB-forsøk feilet (%s, wal=%s): %s", sti, bruk_wal, e)
            return None
        except Exception as e:
            try:
                if conn: conn.close()
            except Exception:
                pass
            log.debug("DB-forsøk feilet uventet (%s): %s", sti, e)
            return None

    def _finn_fungerende_db():
        """Kjører hele fallback-kjeden ÉN gang og husker hva som virket."""
        for sti in _db_kandidatstier():
            conn = _prov_tilkobling(sti, True)
            if conn:
                _db_valgt_sti[0], _db_bruk_wal[0] = sti, True
                return conn
            fjernet = _rydd_stale_wal(sti)
            if fjernet:
                log.warning("Fjernet stale %s — prøver igjen.", ", ".join(fjernet))
                conn = _prov_tilkobling(sti, True)
                if conn:
                    _db_valgt_sti[0], _db_bruk_wal[0] = sti, True
                    return conn
            conn = _prov_tilkobling(sti, False)
            if conn:
                _db_valgt_sti[0], _db_bruk_wal[0] = sti, False
                log.warning("WAL virker ikke for %s — bruker journal_mode=DELETE "
                            "(litt tregere, men trygt).", sti)
                return conn
            log.warning("Kunne ikke bruke DB-sti: %s", sti)
        return None

    def get_conn():
        if _db_valgt_sti[0]:
            conn = _prov_tilkobling(_db_valgt_sti[0], _db_bruk_wal[0])
            if conn:
                return conn
        conn = _finn_fungerende_db()
        if conn is None:
            prøvd = "\n    ".join(_db_kandidatstier())
            raise RuntimeError(
                "Kunne ikke åpne SQLite-databasen noe sted.\n"
                f"  Prøvde:\n    {prøvd}\n"
                "  Vanligste årsaker:\n"
                "    • Mappa synkroniseres av OneDrive/Dropbox (Skrivebordet!)\n"
                "      -> flytt prosjektet til f.eks. C:\\Python_K4\\, eller sett\n"
                "         DB_PATH til en absolutt sti utenfor synk-mappa.\n"
                "    • Antivirus/backup holder .db-filen låst\n"
                "    • Full disk eller skrivebeskyttet mappe")
        if _db_valgt_sti[0] != os.path.abspath(DB_PATH):
            log.warning("⚠ Bruker fallback-plassering for databasen:\n    %s",
                        _db_valgt_sti[0])
        return conn

    def init_db(conn):
        conn.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                finn_id             TEXT PRIMARY KEY,
                title               TEXT,
                address             TEXT,
                gateadresse         TEXT,
                postnr              TEXT,
                poststed            TEXT,
                kommune             TEXT,
                fylke               TEXT,
                omrade              TEXT,
                price_nok           INTEGER,
                total_price         INTEGER,
                shared_cost         INTEGER,
                size_m2             INTEGER,
                bedrooms            INTEGER,
                ownership           TEXT,
                property_type       TEXT,
                viewing_date        TEXT,
                broker              TEXT,
                url                 TEXT,
                scraped_at          TEXT,
                created_at          TEXT DEFAULT CURRENT_TIMESTAMP,
                flagg_i_tittel      INTEGER DEFAULT 0,
                flagg_i_annonse     INTEGER DEFAULT 0,
                flagg_i_pdf         INTEGER DEFAULT 0,
                kategori            TEXT DEFAULT 'vanlig',
                er_dodsbo           INTEGER DEFAULT 0,
                er_tvangssalg       INTEGER DEFAULT 0,
                mulig_dodsbo        INTEGER DEFAULT 0,
                mulig_tvangssalg    INTEGER DEFAULT 0,
                treff_ord           TEXT,
                salgsoppgave_pdf    TEXT,
                salgsoppgave_status TEXT DEFAULT 'ikke_sjekket',
                analyse_begrunnelse TEXT,
                kontekst_sample     TEXT,
                pdf_kjede           TEXT,
                pdf_feilgrunn       TEXT,
                signal_kilde        TEXT
            )
        """)
        existing = {row[1] for row in conn.execute("PRAGMA table_info(listings)")}
        extras = [
            ("gateadresse", "TEXT"), ("postnr", "TEXT"), ("poststed", "TEXT"),
            ("kommune", "TEXT"), ("fylke", "TEXT"), ("omrade", "TEXT"),
            ("property_type", "TEXT"), ("total_price", "INTEGER"),
            ("shared_cost", "INTEGER"), ("bedrooms", "INTEGER"),
            ("viewing_date", "TEXT"), ("broker", "TEXT"),
            ("flagg_i_tittel", "INTEGER DEFAULT 0"),
            ("flagg_i_annonse", "INTEGER DEFAULT 0"),
            ("flagg_i_pdf", "INTEGER DEFAULT 0"),
            ("kategori", "TEXT DEFAULT 'vanlig'"),
            ("er_dodsbo", "INTEGER DEFAULT 0"),
            ("er_tvangssalg", "INTEGER DEFAULT 0"),
            ("mulig_dodsbo", "INTEGER DEFAULT 0"),
            ("mulig_tvangssalg", "INTEGER DEFAULT 0"),
            ("treff_ord", "TEXT"),
            ("salgsoppgave_pdf", "TEXT"),
            ("salgsoppgave_status", "TEXT DEFAULT 'ikke_sjekket'"),
            ("analyse_begrunnelse", "TEXT"),
            ("kontekst_sample", "TEXT"),
            ("pdf_kjede", "TEXT"),
            ("pdf_feilgrunn", "TEXT"),
            ("signal_kilde", "TEXT"),
            # ★ v18 — legges automatisk til i eksisterende base
            ("pdf_url", "TEXT"),
        ]
        for col, typedef in extras:
            if col not in existing:
                conn.execute(f"ALTER TABLE listings ADD COLUMN {col} {typedef}")
        try:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status "
                         "ON listings(salgsoppgave_status)")
        except Exception:
            pass
        conn.commit()
        log.info("Database klar: %s (WAL=%s)",
                 _db_valgt_sti[0] or os.path.abspath(DB_PATH), _db_bruk_wal[0])

    def to_int(raw):
        digits = re.sub(r"[^\d]", "", _norm_ws(str(raw or "")))
        return int(digits) if digits else None

    _INSERT_SQL = """
        INSERT INTO listings (
            finn_id, title, address,
            gateadresse, postnr, poststed, kommune, fylke, omrade,
            price_nok, total_price, shared_cost,
            size_m2, bedrooms, ownership, property_type, viewing_date,
            broker, url, scraped_at,
            flagg_i_tittel, flagg_i_annonse, flagg_i_pdf,
            kategori,
            er_dodsbo, er_tvangssalg, mulig_dodsbo, mulig_tvangssalg,
            treff_ord,
            salgsoppgave_pdf, salgsoppgave_status,
            analyse_begrunnelse, kontekst_sample,
            pdf_kjede, pdf_feilgrunn, signal_kilde,
            pdf_url
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(finn_id) DO UPDATE SET
            address = excluded.address,
            gateadresse = excluded.gateadresse,
            postnr = excluded.postnr,
            poststed = excluded.poststed,
            kommune = excluded.kommune,
            fylke = excluded.fylke,
            omrade = excluded.omrade,
            price_nok = excluded.price_nok,
            total_price = excluded.total_price,
            title = excluded.title,
            size_m2 = excluded.size_m2,
            bedrooms = excluded.bedrooms,
            ownership = excluded.ownership,
            property_type = excluded.property_type,
            scraped_at = excluded.scraped_at,
            flagg_i_tittel = excluded.flagg_i_tittel,
            flagg_i_annonse = excluded.flagg_i_annonse,
            flagg_i_pdf = excluded.flagg_i_pdf,
            kategori = excluded.kategori,
            er_dodsbo = excluded.er_dodsbo,
            er_tvangssalg = excluded.er_tvangssalg,
            mulig_dodsbo = excluded.mulig_dodsbo,
            mulig_tvangssalg = excluded.mulig_tvangssalg,
            treff_ord = excluded.treff_ord,
            salgsoppgave_pdf = excluded.salgsoppgave_pdf,
            salgsoppgave_status = excluded.salgsoppgave_status,
            analyse_begrunnelse = excluded.analyse_begrunnelse,
            kontekst_sample = excluded.kontekst_sample,
            pdf_kjede = excluded.pdf_kjede,
            pdf_feilgrunn = excluded.pdf_feilgrunn,
            signal_kilde = excluded.signal_kilde,
            pdf_url = excluded.pdf_url
    """

    def _rad(l):
        return (
            l.get("finn_id"), l.get("title"), l.get("address"),
            l.get("gateadresse"), l.get("postnr"), l.get("poststed"),
            l.get("kommune"), l.get("fylke"), l.get("omrade"),
            to_int(l.get("price_nok")), to_int(l.get("total_price")),
            to_int(l.get("shared_cost")), to_int(l.get("size_m2")),
            to_int(l.get("bedrooms")), l.get("ownership"),
            l.get("property_type"), l.get("viewing_date"),
            l.get("broker"), l.get("url"), l.get("scraped_at"),
            l.get("flagg_i_tittel", 0), l.get("flagg_i_annonse", 0),
            l.get("flagg_i_pdf", 0), l.get("kategori", "vanlig"),
            l.get("er_dodsbo", 0), l.get("er_tvangssalg", 0),
            0, 0,
            l.get("treff_ord"),
            l.get("salgsoppgave_pdf"), l.get("salgsoppgave_status"),
            l.get("analyse_begrunnelse"), l.get("kontekst_sample"),
            l.get("pdf_kjede"), l.get("pdf_feilgrunn"), l.get("signal_kilde"),
            l.get("pdf_url"),                                   # ★ v18
        )

    def lagre_til_db(conn, listings, stille=False):
        if not listings:
            return
        for l in listings:
            for felt in ("signal_kilde", "treff_ord", "analyse_begrunnelse"):
                v = l.get(felt)
                if isinstance(v, list):
                    l[felt] = ", ".join(str(x) for x in v) if v else None
            l["kategori"] = beregn_kategori(l)
        try:
            conn.executemany(_INSERT_SQL, [_rad(l) for l in listings])
            conn.commit()
        except Exception as e:
            log.warning("DB-batch feilet (%s) — faller tilbake til rad-for-rad", e)
            for l in listings:
                try:
                    conn.execute(_INSERT_SQL, _rad(l))
                except Exception as e2:
                    log.debug("DB-insert feilet for %s: %s", l.get("finn_id"), e2)
            try:
                conn.commit()
            except Exception:
                pass
        if not stille:
            log.info("Lagret %d annonser til DB.", len(listings))

    def last_listings_fra_db(conn):
        try:
            return [dict(r) for r in conn.execute("SELECT * FROM listings")]
        except Exception as e:
            log.error("Kunne ikke lese listings fra DB: %s", e)
            return []

    # ══════════════════════════════════════════════
    # CHECKPOINT
    # ══════════════════════════════════════════════
    def load_checkpoint():
        if Path(CHECKPOINT_PATH).exists():
            try:
                with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
                    cp = json.load(f)
                log.info("Lastet checkpoint: %d annonser i fil, partisjon=%d, "
                         "fase1_done=%s, i_db=%s",
                         len(cp.get("listings", [])), cp.get("fase1_part_index", 0),
                         cp.get("fase1_done"), cp.get("listings_i_db"))
                return cp
            except Exception as e:
                log.warning("Kunne ikke lese checkpoint: %s", e)
        return {"listings": [], "fase1_done": False, "listings_i_db": False,
                "partisjoner": None, "fase1_part_index": 0}

    def save_checkpoint(cp, force=False):
        with _cp_lock:
            na = time.time()
            if not force and (na - _cp_sist[0]) < CHECKPOINT_MIN_SEK:
                return
            _cp_sist[0] = na
            try:
                tmp = CHECKPOINT_PATH + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(cp, f, ensure_ascii=False, default=str)
                os.replace(tmp, CHECKPOINT_PATH)
            except Exception as e:
                log.warning("Kunne ikke lagre checkpoint: %s", e)

    # ══════════════════════════════════════════════
    # EKSPORT
    # ══════════════════════════════════════════════
    KOLONNER = [
        "finn_id", "title",
        "address", "gateadresse", "postnr", "poststed",
        "omrade", "kommune", "fylke",
        "price_nok", "total_price",
        "size_m2", "bedrooms", "ownership", "property_type",
        "kategori",
        "er_dodsbo", "er_tvangssalg",
        "treff_ord", "analyse_begrunnelse", "kontekst_sample",
        "signal_kilde",
        "flagg_i_tittel", "flagg_i_annonse", "flagg_i_pdf",
        "salgsoppgave_status", "pdf_kjede", "pdf_feilgrunn",
        "salgsoppgave_pdf",
        "viewing_date", "broker", "url", "scraped_at",
        "pdf_url",                                              # ★ v18
    ]

    def _bygg_df(listings):
        if not listings:
            return pd.DataFrame(columns=KOLONNER)
        df = pd.DataFrame(listings)
        for c in KOLONNER:
            if c not in df.columns:
                df[c] = None
        df = df[KOLONNER]
        df["_score"] = (df["er_dodsbo"].fillna(0).astype(int)
                        + df["er_tvangssalg"].fillna(0).astype(int))
        return df.sort_values("_score", ascending=False).drop(columns=["_score"])

    def _skriv_df_trygt(df, filnavn, stille):
        tmp = filnavn + ".tmp.xlsx"
        ctmp = None
        try:
            df.to_excel(tmp, index=False, engine="openpyxl")
            try:
                os.replace(tmp, filnavn)
                mål = filnavn
            except PermissionError:
                stamp = datetime.now().strftime("%H%M%S")
                mål = filnavn.replace(".xlsx", f"_{stamp}.xlsx")
                os.replace(tmp, mål)
                log.warning("⚠ %s var låst — lagret som %s i stedet.",
                            os.path.basename(filnavn), os.path.basename(mål))
            abspath = os.path.abspath(mål)
            if not stille:
                log.info("✅ Excel skrevet: %s (%d rader)", abspath, len(df))
            return abspath
        except ImportError:
            log.warning("openpyxl mangler — faller tilbake til CSV.")
        except Exception as e:
            log.warning("Excel-skriving feilet (%s) — faller tilbake til CSV.", e)
        finally:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass
        try:
            csv_path = filnavn.replace(".xlsx", ".csv")
            ctmp = csv_path + ".tmp"
            df.to_csv(ctmp, index=False, encoding="utf-8-sig")
            try:
                os.replace(ctmp, csv_path)
                cmål = csv_path
            except PermissionError:
                stamp = datetime.now().strftime("%H%M%S")
                cmål = csv_path.replace(".csv", f"_{stamp}.csv")
                os.replace(ctmp, cmål)
            abspath = os.path.abspath(cmål)
            if not stille:
                log.info("✅ CSV skrevet: %s (%d rader)", abspath, len(df))
            return abspath
        except Exception as e:
            log.error("CSV-skriving feilet også: %s", e)
            try:
                if ctmp and os.path.exists(ctmp):
                    os.remove(ctmp)
            except Exception:
                pass
            return None

    def eksporter_excel(listings, filnavn=None, stille=False, bare_treff=False):
        if not listings:
            if not stille:
                log.warning("eksporter_excel: ingen listings å skrive")
            return None
        for l in listings:
            l["kategori"] = beregn_kategori(l)
        if bare_treff:
            listings = [l for l in listings
                        if l.get("er_dodsbo") or l.get("er_tvangssalg")]
        if not listings:
            if not stille:
                log.warning("eksporter_excel: ingen bekreftede treff ennå")
            return None
        if filnavn is None:
            filnavn = f"finn_dodsbo_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
        os.makedirs(EXCEL_DIR, exist_ok=True)
        if not os.path.isabs(filnavn):
            filnavn = os.path.join(EXCEL_DIR, filnavn)
        try:
            df = _bygg_df(listings)
        except Exception as e:
            log.error("Kunne ikke bygge DataFrame: %s", e)
            return None
        if bare_treff and not stille:
            log.info("Skriver KUN bekreftede treff (dødsbo + tvangssalg): %d rad(er)",
                     len(df))
        return _skriv_df_trygt(df, filnavn, stille)

    def eksporter_fra_db():
        try:
            c = get_conn()
            rows = last_listings_fra_db(c)
            c.close()
            if rows:
                log.info("Recovery: eksporterer %d rader fra DB", len(rows))
                return eksporter_excel(rows, bare_treff=KUN_TREFF_I_EXCEL)
        except Exception as e:
            log.error("DB-recovery feilet: %s", e)
        return None

    def skriv_rapport(listings):
        dodsbo     = [l for l in listings if l.get("er_dodsbo")]
        tvangssalg = [l for l in listings if l.get("er_tvangssalg")]
        begge      = [l for l in listings if l.get("er_dodsbo") and l.get("er_tvangssalg")]
        nedlastet  = [l for l in listings if l.get("salgsoppgave_status") == "lastet_ned"]
        ikke_funnet = [l for l in listings if l.get("salgsoppgave_status") == "pdf_ikke_funnet"]
        med_sted   = [l for l in listings if l.get("poststed") or l.get("kommune")]

        def kilder(gruppe):
            st = {"selger_felt": 0, "selger_felt_tvangssalg": 0,
                  "egenerklaering": 0, "setning_dodsbo": 0,
                  "setning_tvangssalg": 0}
            for l in gruppe:
                for k in (l.get("signal_kilde") or "").split(", "):
                    if k in st:
                        st[k] += 1
            return st

        kd, kt = kilder(dodsbo), kilder(tvangssalg)

        log.info("")
        log.info("╔════════════════════════════════════════════════╗")
        log.info("║              SLUTTRAPPORT (v17)                  ║")
        log.info("╠════════════════════════════════════════════════╣")
        log.info("║  Totalt annonser:            %6d            ║", len(listings))
        log.info("║  PDF lastet ned:             %6d            ║", len(nedlastet))
        log.info("║  PDF IKKE funnet:            %6d            ║", len(ikke_funnet))
        log.info("║  Med sted/adresse:           %6d            ║", len(med_sted))
        log.info("╠════════════════════════════════════════════════╣")
        log.info("║  Dødsbo (bekreftet):         %6d            ║", len(dodsbo))
        log.info("║  Tvangssalg (bekreftet):     %6d            ║", len(tvangssalg))
        log.info("║  — derav BEGGE deler:        %6d            ║", len(begge))
        log.info("╠════════════════════════════════════════════════╣")
        log.info("║  DØDSBO via selger-felt:     %6d            ║", kd["selger_felt"])
        log.info("║  DØDSBO via setning:         %6d            ║", kd["setning_dodsbo"])
        log.info("║  DØDSBO via egenerklæring:   %6d            ║", kd["egenerklaering"])
        log.info("║  TVANG. via selger-felt:     %6d            ║", kt["selger_felt_tvangssalg"])
        log.info("║  TVANG. via setning:         %6d            ║", kt["setning_tvangssalg"])
        log.info("╚════════════════════════════════════════════════╝")

        log.info("")
        log.info("══ PDF-statistikk pr. meglerkjede ══")
        for kjede, d in sorted(pdf_stats["per_kjede"].items(),
                               key=lambda x: -x[1].get("forsokt", 0)):
            forsokt = d.get("forsokt", 0)
            ok = d.get("ok", 0)
            pct = (100.0 * ok / forsokt) if forsokt else 0
            sperr = "  ⛔SPERRET" if kjede in _kjede_sperret else ""
            log.info("  %-20s  forsøkt=%5d  ok=%5d (%3.0f%%)  epost=%d%s",
                     kjede, forsokt, ok, pct, d.get("epost_vegg", 0), sperr)

        if ikke_funnet:
            log.info("")
            log.info("══ ⚠ PDF IKKE FUNNET — %d stk (kan skjule ekte treff) ══",
                     len(ikke_funnet))
            for l in ikke_funnet[:40]:
                log.info("  ⚠ %s | %s | %s", l.get("finn_id"),
                         (l.get("pdf_kjede") or "?"), (l.get("pdf_feilgrunn") or "")[:90])
            log.info("  → Disse prøves automatisk på nytt ved neste kjøring.")

        for label, gruppe in [("DØDSBO (bekreftet)", dodsbo),
                              ("TVANGSSALG (bekreftet)", tvangssalg)]:
            if gruppe:
                log.info("")
                log.info("══ %s — %d stk ══", label, len(gruppe))
                for l in gruppe[:200]:
                    sted = (l.get("address")
                            or " ".join(x for x in [l.get("poststed"), l.get("kommune")] if x)
                            or "?")
                    log.info("  🔴 %s | %s", l.get("finn_id"), (l.get("title") or "")[:55])
                    log.info("     Kategori: %s | Sted: %s", l.get("kategori"), sted)
                    log.info("     Kilde: %s", l.get("signal_kilde") or "?")
                    log.info("     Setning: %s", (l.get("kontekst_sample") or "")[:160])
                    log.info("     URL: %s", l.get("url"))

    # ══════════════════════════════════════════════
    # MEGLER-IDENTIFIKASJON
    # ══════════════════════════════════════════════
    def identifiser_kjede(url):
        if not url:
            return "ukjent"
        u = url.lower()
        if "aktiv.no" in u: return "aktiv"
        if "nordvik" in u: return "nordvik"
        if "eiendomsmegler1.no" in u or "em1" in u: return "em1"
        if "dnbeiendom" in u or "dnb.no" in u: return "dnb"
        if "krogsveen" in u: return "krogsveen"
        if "privatmegleren" in u: return "privatmegleren"
        if "eie.no" in u: return "eie"
        if "obos.no" in u: return "obos"
        if "meglerhuset" in u: return "meglerhuset"
        if "hem.no" in u: return "hem"
        if "notar" in u: return "notar"
        if "sormegleren" in u: return "sormegleren"
        if "fossbergmegler" in u: return "fossberg"
        if "eiendomsmeglernorge" in u or "emnorge" in u: return "emnorge"
        if "vitecnext" in u or "d3gck1or7m1j2s" in u: return "emnorge"
        # ★ v18: sjekkes ETTER alle kjedene, så ingen kjede endrer rute.
        if BRUK_DIREKTE_PDF and er_direkte_pdf_url(url):
            return "direkte_pdf"
        if _ser_ut_som_advokat(u):
            return "advokat"
        return "annet"

    # ══════════════════════════════════════════════
    # ★ v18 — DIREKTE-PDF- OG ADVOKAT-GJENKJENNING
    # Begge avgjør KUN hvilken nedlastingsrute som velges.
    # ══════════════════════════════════════════════
    _ADVOKAT_ORD = (
        "advokat", "advokatfirma", "advokatfirmaet", "advokatene",
        "law", "juridisk", "juristene", "bostyrer", "bobestyrer",
        "tingrett", "byfogd", "namsfogd", "namsmann",
    )

    def _ser_ut_som_advokat(tekst):
        """Treffer både URL-er og firmanavn ('Advokatfirmaet X AS')."""
        if not tekst:
            return False
        t = str(tekst).lower()
        return any(o in t for o in _ADVOKAT_ORD)

    def er_direkte_pdf_url(url):
        """
        True hvis URL-en ER selve PDF-en, ikke en side som lenker til den.

        Dette er hele v17-feilen i én funksjon: en URL som
        https://images.finncdn.no/item/473969209/file/<uuid>.pdf skal
        HENTES, ikke navigeres til. page.goto() på en PDF gir
        net::ERR_ABORTED i Chromium fordi nedlasting starter i stedet
        for rendering.
        """
        if not url:
            return False
        u = str(url).lower()
        sti = u.split("?", 1)[0].split("#", 1)[0]
        if sti.endswith(".pdf"):
            return True
        # FINN-hostet fil uten .pdf-suffiks i stien
        if any(v in u for v in DIREKTE_PDF_VERTER) and "/file/" in u:
            return True
        return False

    USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0.0.0 Safari/537.36")

    # ══════════════════════════════════════════════
    # JS-SNUTTER
    # ══════════════════════════════════════════════
    _JS_KORT = """() => {
        const out = [];
        for (const a of document.querySelectorAll('section article')) {
            const link = a.querySelector('h2 a') || a.querySelector('a[href*="finnkode"]') || a.querySelector('a');
            const addr = a.querySelector('[class*="address"]');
            const pris = a.querySelector('[class*="price-primary"]')
                      || a.querySelector('[class*="mt-bold"]')
                      || a.querySelector('strong');
            const img = a.querySelector('img');
            out.push({
                title: link ? (link.innerText || '').trim() : null,
                href: link ? (link.getAttribute('href') || '') : '',
                id: a.getAttribute('id') || '',
                text: a.innerText || '',
                address: addr ? (addr.innerText || '').trim() : null,
                price: pris ? (pris.innerText || '').trim() : null,
                broker: img ? img.getAttribute('alt') : null
            });
        }
        return out;
    }"""

    _JS_LENKER = """() => {
        const out = [];
        for (const a of document.querySelectorAll('a')) {
            const h = a.href || '';
            if (!h || h.startsWith('javascript:') || h.startsWith('mailto:')) continue;
            const r = a.getBoundingClientRect();
            out.push({
                href: h,
                txt: (a.innerText || a.textContent || '').trim().toLowerCase().slice(0, 140),
                vis: (r.width > 0 && r.height > 0)
            });
        }
        return out;
    }"""

    _JS_KLIKK = """(tekster) => {
        const els = document.querySelectorAll('button, a, [role="button"]');
        for (const el of els) {
            const r = el.getBoundingClientRect();
            if (r.width <= 0 && r.height <= 0) continue;
            const t = (el.innerText || el.textContent || '').trim().toLowerCase();
            if (!t) continue;
            for (const k of tekster) {
                if (t.includes(k)) {
                    try { el.scrollIntoView({block: 'center'}); } catch (e) {}
                    el.click();
                    return t.slice(0, 60);
                }
            }
        }
        return null;
    }"""

    _JS_EPOSTVEGG = """() => {
        const ep = document.querySelector('input[type="email"]');
        if (ep) { const r = ep.getBoundingClientRect(); if (r.width > 0 && r.height > 0) return true; }
        const t = (document.body ? document.body.innerText : '').toLowerCase().slice(0, 3000);
        return ['fyll inn e-post', 'din e-post', 'skriv inn e-post', 'fyll inn epost']
            .some(p => t.includes(p));
    }"""

    _JS_AAPNE_ACCORDION = """() => {
        let n = 0;
        const els = document.querySelectorAll("[class*='accordion'], button[aria-expanded='false'], summary");
        for (const el of els) {
            const t = (el.innerText || '').toLowerCase();
            if (t.includes('dokument') || t.includes('salgsoppgave') || t.includes('vedlegg')) {
                try { el.click(); n++; } catch (e) {}
            }
            if (n >= 6) break;
        }
        return n;
    }"""

    # ══════════════════════════════════════════════
    # SCRAPER
    # ══════════════════════════════════════════════
    class FinnScraper:
        def __init__(self, worker_id=0):
            self.worker_id = worker_id
            self._pw = self._browser = self._context = self._page = None
            self._start_browser()

        def _start_browser(self):
            self._stop_browser()
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-gpu",
                    "--disable-extensions",
                    "--disable-background-networking",
                    "--mute-audio",
                    "--js-flags=--max-old-space-size=512",
                ],
            )
            self._context = self._browser.new_context(
                accept_downloads=True, user_agent=USER_AGENT,
                viewport={"width": 1280, "height": 900},
                java_script_enabled=True)
            if BLOKKER_TUNGE_RESSURSER:
                try:
                    self._context.route(
                        "**/*.{png,jpg,jpeg,gif,webp,avif,ico,svg,woff,woff2,"
                        "ttf,otf,eot,mp4,webm,mp3,m4v}",
                        lambda r: r.abort())
                    for pat in ("**/*google-analytics.com/**",
                                "**/*googletagmanager.com/**",
                                "**/*doubleclick.net/**",
                                "**/*facebook.net/**",
                                "**/*hotjar.com/**",
                                "**/*clarity.ms/**",
                                "**/*criteo.com/**"):
                        self._context.route(pat, lambda r: r.abort())
                except Exception as e:
                    log.debug("Ruteblokkering feilet: %s", e)
            self._page = self._context.new_page()
            self._page.set_default_timeout(STEP_TIMEOUT_MS)
            log.info("  [w%d] Chromium klar.", self.worker_id)

        def _stop_browser(self):
            for obj in (self._context, self._browser):
                try:
                    if obj: obj.close()
                except Exception:
                    pass
            try:
                if self._pw: self._pw.stop()
            except Exception:
                pass
            self._pw = self._browser = self._context = self._page = None

        def quit(self):
            self._stop_browser()

        # ── Navigasjon ────────────────────────────
        def _goto(self, url, vent_selector=None, vent_ms=6000):
            try:
                self._page.goto(url, wait_until="domcontentloaded",
                                timeout=NAV_TIMEOUT_MS)
            except Exception as e:
                log.debug("_goto feilet: %s", e)
                return False
            if vent_selector:
                try:
                    self._page.wait_for_selector(vent_selector, timeout=vent_ms)
                except Exception:
                    pass
            return True

        def _js(self, script, arg=None):
            try:
                return self._page.evaluate(script, arg) if arg is not None \
                    else self._page.evaluate(script)
            except Exception:
                return None

        def _scroll_bunn(self):
            try:
                self._page.evaluate(
                    "() => window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(0.5)
                self._page.evaluate("() => window.scrollTo(0, 0)")
            except Exception:
                pass

        def _klikk_tekst(self, tekster, timeout_ms=STEP_TIMEOUT_MS):
            if isinstance(tekster, str):
                tekster = [tekster]
            tekster = [t.lower() for t in tekster]
            deadline = time.time() + timeout_ms / 1000.0
            while True:
                if self._js(_JS_KLIKK, tekster):
                    time.sleep(0.8)
                    return True
                if time.time() >= deadline:
                    return False
                time.sleep(0.35)

        def _aksepter_cookies(self):
            for sel in ("#declineButton", "#declineAllButton",
                        "[data-testid='coi-banner__decline-all-categories-button']",
                        "#CybotCookiebotDialogBodyLevelButtonLevelOptinDeclineAll"):
                try:
                    el = self._page.query_selector(sel)
                    if el:
                        el.click(timeout=1500)
                        time.sleep(0.3)
                        return True
                except Exception:
                    continue
            return self._klikk_tekst(
                ["kun nødvendige", "godta alle", "godta", "aksepter",
                 "accept all", "tillat alle"], timeout_ms=1500)

        def _lukk_modal(self):
            try:
                for sel in ('button[aria-label*="lukk" i]',
                            'button[aria-label*="close" i]',
                            '[role="dialog"] button:has(svg)'):
                    el = self._page.query_selector(sel)
                    if el:
                        try:
                            el.click(timeout=1200)
                            time.sleep(0.3)
                            return True
                        except Exception:
                            pass
            except Exception:
                pass
            return False

        def _detekt_epost_vegg(self):
            return bool(self._js(_JS_EPOSTVEGG))

        # ── Lenker ────────────────────────────────
        def _alle_lenker(self):
            return self._js(_JS_LENKER) or []

        def _pdf_lenker(self):
            ekte, mulige = [], []
            for d in self._alle_lenker():
                href = d.get("href") or ""
                txt = d.get("txt") or ""
                hl = href.lower().split("?")[0]
                if hl.endswith(".pdf"):
                    ekte.append((href, txt))
                elif ("/documents/" in href.lower() or "salgsoppgave" in href.lower()
                      or "prospekt" in href.lower() or "salgsoppgave" in txt):
                    mulige.append((href, txt))
            return ekte, mulige

        def _vent_pdf_lenker(self, timeout_s=PDF_LENKE_POLL_S):
            deadline = time.time() + timeout_s
            mulige_sist = []
            while True:
                ekte, mulige = self._pdf_lenker()
                if ekte:
                    return ekte + mulige
                mulige_sist = mulige
                if time.time() >= deadline:
                    return mulige_sist
                time.sleep(0.3)

        def _abs(self, href):
            if not href or href.startswith("http"):
                return href
            try:
                return urljoin(self._page.url, href)
            except Exception:
                return href

        # ── Nedlasting ────────────────────────────
        def _last_ned_pdf_url(self, url, dest, referer=None):
            import urllib.request
            if not url:
                return None
            try:
                cookies = self._context.cookies()
                headers = {
                    "Cookie": "; ".join(f"{c['name']}={c['value']}" for c in cookies),
                    "User-Agent": USER_AGENT,
                    "Accept": "application/pdf,application/octet-stream,*/*",
                }
                if referer:
                    headers["Referer"] = referer
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=PDF_DOWNLOAD_TIMEOUT) as resp:
                    data = resp.read()
                if len(data) > 1000 and b"%PDF-" in data[:2048]:
                    with open(dest, "wb") as f:
                        f.write(data)
                    return dest
            except Exception as e:
                log.debug("    urllib-nedlasting feilet: %s", e)
            try:
                resp = self._context.request.get(
                    url, timeout=PDF_DOWNLOAD_TIMEOUT * 1000)
                data = resp.body()
                if len(data) > 1000 and b"%PDF-" in data[:2048]:
                    with open(dest, "wb") as f:
                        f.write(data)
                    return dest
            except Exception as e:
                log.debug("    pw-nedlasting feilet: %s", e)
            return None

        def _prov_lenker(self, lenker, dest):
            for href, _txt in lenker[:6]:
                p = self._last_ned_pdf_url(self._abs(href), dest,
                                           referer=self._page.url)
                if p:
                    return p
            return None

        def _vent_for_nedlasting(self, action_fn, dest, timeout_s=12):
            try:
                with self._page.expect_download(timeout=timeout_s * 1000) as dl_info:
                    action_fn()
                dl_info.value.save_as(dest)
                if os.path.exists(dest) and os.path.getsize(dest) > 1000:
                    return dest
            except Exception as e:
                log.debug("    _vent_for_nedlasting: %s", e)
            return None

        def _prov_popup(self, tekster, dest, timeout_ms=5000):
            try:
                with self._page.expect_popup(timeout=timeout_ms) as pop:
                    self._klikk_tekst(tekster, timeout_ms=timeout_ms)
                popup = pop.value
                time.sleep(1.2)
                purl = popup.url or ""
                p = None
                if ".pdf" in purl.lower():
                    p = self._last_ned_pdf_url(purl, dest, referer=self._page.url)
                if not p:
                    try:
                        for d in (popup.evaluate(_JS_LENKER) or []):
                            if d["href"].lower().split("?")[0].endswith(".pdf"):
                                p = self._last_ned_pdf_url(d["href"], dest, referer=purl)
                                if p:
                                    break
                    except Exception:
                        pass
                try:
                    popup.close()
                except Exception:
                    pass
                return p
            except Exception:
                return None

        # ── Fase 1 ────────────────────────────────
        def hent_antall_treff(self, url):
            if not self._goto(url):
                return None
            time.sleep(1.0)
            try:
                body = _norm_ws(self._page.inner_text("body"))
            except Exception:
                return None
            for pat in (r"([\d\s]{1,12})\s+treff",
                        r"av\s+([\d\s]{1,12})\s+(?:bolig|annonse|resultat|treff)",
                        r"([\d\s]{1,12})\s+bolig(?:er)?\s+til\s+salgs"):
                m = re.search(pat, body)
                if m:
                    n = re.sub(r"\D", "", m.group(1))
                    if n:
                        return int(n)
            return None

        def lag_pris_partisjoner(self):
            self._goto(bygg_sok_url())
            self._aksepter_cookies()
            full = self.hent_antall_treff(bygg_sok_url())
            if full is None:
                log.warning("⚠ Kunne ikke lese treff-antall — ett søk (2500-tak).")
                return [(None, None)]
            log.info("Totalt på Finn (uten filter): ~%d treff", full)
            if full <= PARTISJON_CAP:
                return [(None, None)]

            leaves, stack, probes = [], [(PRIS_MIN, PRIS_MAKS)], 0
            while stack:
                lo, hi = stack.pop()
                antall = self.hent_antall_treff(bygg_sok_url(lo, hi))
                probes += 1
                if antall is None:
                    # ★ v18.1: kan skyldes krasjet nettleser. Uten ny
                    # nettleser ville ALLE videre prober feile, og
                    # prisområdet splittes ned i tusenvis av biter.
                    try:
                        self._start_browser()
                    except Exception as e:
                        log.error("Browser-restart feilet: %s", e)
                    antall = self.hent_antall_treff(bygg_sok_url(lo, hi))
                if antall is None:
                    if (hi - lo) > MIN_PRIS_SPENN:
                        mid = (lo + hi) // 2
                        stack += [(lo, mid), (mid + 1, hi)]
                    else:
                        leaves.append((lo, hi))
                    continue
                if antall == 0:
                    continue
                if antall <= PARTISJON_CAP or (hi - lo) <= MIN_PRIS_SPENN:
                    leaves.append((lo, hi))
                else:
                    mid = (lo + hi) // 2
                    stack += [(lo, mid), (mid + 1, hi)]
            leaves.sort()
            if TA_MED_UFILTRERT:
                leaves.append((None, None))
            log.info("Bygde %d prispartisjoner (%d probe-kall).", len(leaves), probes)
            return leaves

        def scrape_search_page(self):
            kort = self._js(_JS_KORT) or []
            listings = []
            for k in kort:
                try:
                    href = k.get("href") or ""
                    url = ("https://www.finn.no" + href) if href.startswith("/") else href
                    finn_id = ""
                    if url:
                        m = re.search(r"finnkode=(\d+)", url)
                        finn_id = m.group(1) if m else ""
                    if not finn_id:
                        finn_id = re.sub(r"[^\d]", "", k.get("id") or "")
                    if not finn_id:
                        continue

                    full_text = _norm_ws(k.get("text") or "")
                    title = k.get("title")
                    sted = parse_kort_sted(full_text)

                    total_price = shared_cost = None
                    m_tot = re.search(r"Totalpris[:\s·]+([\d\s\xa0]+)\s*kr", full_text)
                    m_shr = re.search(r"Fellesutg[\.:\s]+([\d\s\xa0]+)\s*kr", full_text)
                    if m_tot: total_price = m_tot.group(1).strip() + " kr"
                    if m_shr: shared_cost = m_shr.group(1).strip() + " kr"

                    size_m2 = bedrooms = None
                    m_size = re.search(r"(\d[\d\s\xa0]*)\s*m²", full_text)
                    m_bed = re.search(r"(\d+)\s*soverom", full_text)
                    if m_size: size_m2 = re.sub(r"\D", "", m_size.group(1))
                    if m_bed: bedrooms = m_bed.group(1)

                    ftl = full_text.lower()
                    ownership = next((x for x in ("Selveier", "Borettslag", "Aksjelag")
                                      if x.lower() in ftl), None)
                    property_type = next((x for x in ("Leilighet", "Enebolig", "Rekkehus",
                                                      "Tomannsbolig", "Hytte")
                                          if x.lower() in ftl), None)
                    viewing_date = None
                    m_view = re.search(r"Visning[–\-·\s]+([\w\s\.,\d:]+)", full_text)
                    if m_view:
                        viewing_date = m_view.group(1).strip()[:50]

                    # ★ v16: ingen nøkkelordsøk i tittel/annonsekort.
                    # Klassifisering skjer utelukkende på salgsoppgaven.
                    listings.append({
                        "finn_id": finn_id, "title": title,
                        "address": k.get("address") or sted.get("full_adresse"),
                        "gateadresse": sted.get("gateadresse"),
                        "postnr": sted.get("postnr"),
                        "poststed": sted.get("poststed"),
                        "kommune": None, "fylke": None, "omrade": None,
                        "price_nok": k.get("price"), "total_price": total_price,
                        "shared_cost": shared_cost, "size_m2": size_m2,
                        "bedrooms": bedrooms, "ownership": ownership,
                        "property_type": property_type, "viewing_date": viewing_date,
                        "broker": k.get("broker"), "url": url,
                        "scraped_at": datetime.now(timezone.utc).isoformat(),
                        "flagg_i_tittel": 0,
                        "flagg_i_annonse": 0,
                        "treff_ord": None,
                        "kategori": "vanlig",
                        "salgsoppgave_status": "ikke_sjekket",
                        "er_dodsbo": 0, "er_tvangssalg": 0,
                    })
                except Exception as e:
                    log.debug("Kort-parsing feilet: %s", e)
            return listings

        # ── Fase 2 ────────────────────────────────
        def hent_finn_detalj(self):
            try:
                body = self._page.inner_text("body")
            except Exception:
                return {}
            sted = parse_finn_sted(body)
            sted["_felt"] = parse_finn_detalj_felt(body)
            return sted

        def _finn_megler_lenke(self):
            synlige, skjulte = [], []
            for d in self._alle_lenker():
                href, txt = d.get("href") or "", d.get("txt") or ""
                if not href.startswith("http") or "finn.no" in href.lower():
                    continue
                traff = any(p in txt for p in (
                    "komplett salgsoppgave", "se salgsoppgave",
                    "last ned salgsoppgave", "salgsoppgave",
                    "se prospekt", "komplett prospekt"))
                if not traff and "bestill" in txt and ("salgsoppgave" in txt or "prospekt" in txt):
                    traff = True
                if not traff:
                    continue
                (synlige if d.get("vis") else skjulte).append(href)
            treff = (synlige or skjulte or [None])[0]
            # ★ v18: originalruta over er UENDRET og har fortsatt
            # førsteretten. Utvidet søk kjører kun når den ga None.
            if treff or not BRUK_UTVIDET_LENKESOK:
                return treff
            return self._finn_pdf_lenke_utvidet()

        def _finn_pdf_lenke_utvidet(self):
            """
            ★ v18 — det robuste alternativet for andre sideformater.

            Tre tilfeller den vanlige ruta bommer på:
              1. Lenketeksten er et filnavn uten nøkkelordet
                 ("Prospekt_Hagegata41.pdf").
              2. Knappen heter "Dokumenter" eller "Vedlegg".
              3. PDF-en er bygget inn i <iframe>/<embed>/<object> i
                 stedet for å ligge i en <a>.

            Endrer KUN hvilken fil som hentes — aldri hvordan den tolkes.

            Rangering: .pdf på FINNs egen filserver først (der
            advokatkontorene legger dem), så andre .pdf-er, så innbygde
            PDF-er, så nøkkelordlenker.
            """
            finn_pdf, andre_pdf, nokkelord = [], [], []
            for d in self._alle_lenker():
                href = d.get("href") or ""
                txt = (d.get("txt") or "").lower()
                if not href.startswith("http"):
                    continue
                low = href.lower()
                # Selve annonsesiden er aldri salgsoppgaven
                if "finn.no/realestate" in low or "finnkode=" in low:
                    continue
                if er_direkte_pdf_url(href):
                    if any(v in low for v in DIREKTE_PDF_VERTER):
                        finn_pdf.append(href)
                    else:
                        andre_pdf.append(href)
                    continue
                if any(o in txt for o in ("salgsoppg", "prospekt", "dokument",
                                          "vedlegg", "nabolagsprofil",
                                          "tilstandsrapport", "egenerklæring")):
                    if "finn.no" not in low:
                        nokkelord.append(href)

            innbygd = self._innbygde_pdf_er() if BRUK_INNBYGD_PDF_SOK else []

            valgt = (finn_pdf or andre_pdf or innbygd or nokkelord or [None])[0]
            if valgt:
                log.debug("    [w%d] Utvidet lenkesøk fant: %s",
                          self.worker_id, valgt[:120])
            return valgt

        def _innbygde_pdf_er(self):
            """★ v18 — PDF-er lagt inn i iframe/embed/object."""
            try:
                funn = self._js("""() => {
                    const ut = [];
                    const sel = 'iframe[src], embed[src], object[data]';
                    for (const el of document.querySelectorAll(sel)) {
                        const u = el.getAttribute('src')
                               || el.getAttribute('data') || '';
                        if (u) ut.push(u);
                    }
                    return ut;
                }""") or []
            except Exception:
                return []
            ut = []
            for u in funn:
                a = self._abs(u)
                if a and er_direkte_pdf_url(a):
                    ut.append(a)
            return ut

        def hent_salgsoppgave(self, finn_id, annonse_url):
            result = {
                "salgsoppgave_pdf": None, "salgsoppgave_status": "ikke_funnet",
                "flagg_i_pdf": 0,
                "er_dodsbo": 0, "er_tvangssalg": 0,
                "pdf_treff": [], "analyse_begrunnelse": "",
                "kontekst_sample": None, "pdf_kjede": None,
                "pdf_feilgrunn": None, "signal_kilde": None,
                "address": None, "gateadresse": None, "postnr": None,
                "poststed": None, "kommune": None, "fylke": None,
                "omrade": None, "_detalj_felt": None,
                "pdf_url": None,                                # ★ v18
            }

            if not self._goto(annonse_url):
                result["salgsoppgave_status"] = "feil_annonse"
                result["pdf_feilgrunn"] = "Kunne ikke åpne annonse"
                return result
            time.sleep(DETAIL_WAIT)

            try:
                sted = self.hent_finn_detalj()
                for k in ("gateadresse", "postnr", "poststed",
                          "kommune", "fylke", "omrade"):
                    result[k] = sted.get(k)
                result["address"] = sted.get("full_adresse")
                result["_detalj_felt"] = sted.get("_felt")
            except Exception as e:
                log.debug("    [w%d] Sted-uttrekk feilet: %s", self.worker_id, e)

            megler_url = self._finn_megler_lenke()
            if not megler_url:
                result["pdf_feilgrunn"] = "Ingen salgsoppgave-lenke på Finn"
                _stats_bump("ingen_lenke", "forsokt")
                _stats_bump("ingen_lenke", "feil")
                return result

            kjede = identifiser_kjede(megler_url)
            result["pdf_kjede"] = kjede
            result["pdf_url"] = megler_url          # ★ v18 — sporbarhet
            if kjede == "direkte_pdf":
                log.info("    [w%d] ★ Direkte PDF på FINN: %s",
                         self.worker_id, megler_url[:110])

            if kjede_er_haplos(kjede):
                result["salgsoppgave_status"] = "hoppet_over_kjede"
                result["pdf_feilgrunn"] = f"Kjede '{kjede}' sperret (lav treffrate)"
                return result

            _stats_bump(kjede, "forsokt")
            Path(PDF_DIR).mkdir(exist_ok=True)
            dest = str(Path(PDF_DIR) / f"{finn_id}.pdf")

            handler = self._megler_handler(kjede)
            try:
                pdf_path, feilgrunn = handler(megler_url, dest, finn_id)
            except PlaywrightTimeout:
                pdf_path, feilgrunn = None, "Timeout i handler"
            except Exception as e:
                pdf_path, feilgrunn = None, f"Krasj i handler: {e}"

            if (not pdf_path and BRUK_GENERISK_FALLBACK
                    and handler is not self._handler_generisk
                    and "epost" not in (feilgrunn or "").lower()):
                try:
                    pdf_path, f2 = self._handler_generisk(megler_url, dest, finn_id)
                    if not pdf_path:
                        feilgrunn = f"{feilgrunn} | fallback: {f2}"
                except Exception:
                    pass

            if pdf_path:
                result["salgsoppgave_pdf"] = pdf_path
                result["salgsoppgave_status"] = "lastet_ned"
                _stats_bump(kjede, "ok")
                self._analyser_og_fyll(result, pdf_path, finn_id)
            else:
                result["salgsoppgave_status"] = "pdf_ikke_funnet"
                result["pdf_feilgrunn"] = feilgrunn or "Ukjent"
                _stats_bump(kjede, "feil")
                log.warning("    [w%d] ⚠ PDF ikke funnet for %s (%s): %s",
                            self.worker_id, finn_id, kjede, (feilgrunn or "")[:110])
                if feilgrunn and "epost" in feilgrunn.lower():
                    _stats_bump(kjede, "epost_vegg")
                    with _stats_lock:
                        if len(pdf_stats["epost_vegg_eks"]) < 30:
                            pdf_stats["epost_vegg_eks"].append(
                                {"finn_id": finn_id, "kjede": kjede,
                                 "url": megler_url[:200]})
            return result

        def _analyser_og_fyll(self, result, pdf_path, finn_id):
            pdf_tekst = les_pdf_tekst(pdf_path)
            analyse = analyser_pdf_kontekst(pdf_tekst, pdf_path=pdf_path)
            result["pdf_treff"]           = analyse["treff_ord"] or []
            result["er_dodsbo"]           = 1 if analyse["er_dodsbo"] else 0
            result["er_tvangssalg"]       = 1 if analyse["er_tvangssalg"] else 0
            result["flagg_i_pdf"]         = 1 if analyse["treff_ord"] else 0
            result["analyse_begrunnelse"] = analyse["begrunnelse"]
            result["kontekst_sample"]     = analyse["kontekst_sample"]
            result["signal_kilde"]        = analyse.get("signal_kilde")

            if not result.get("poststed"):
                pdf_sted = hent_sted_fra_pdf(pdf_tekst)
                if pdf_sted.get("poststed"):
                    result["postnr"] = result.get("postnr") or pdf_sted.get("postnr")
                    result["poststed"] = pdf_sted.get("poststed")
                    result["gateadresse"] = result.get("gateadresse") or pdf_sted.get("gateadresse")
                    result["address"] = result.get("address") or pdf_sted.get("full_adresse")

            if analyse["er_dodsbo"] or analyse["er_tvangssalg"]:
                log.info("    [w%d] 🔴 %s: dødsbo=%s tvangssalg=%s | %s",
                         self.worker_id, finn_id, analyse["er_dodsbo"],
                         analyse["er_tvangssalg"], analyse["begrunnelse"][:180])

        def _megler_handler(self, kjede):
            return {
                "aktiv":   self._handler_aktiv,
                "nordvik": self._handler_nordvik,
                "em1":     self._handler_em1,
                "dnb":     self._handler_dnb,
                "emnorge": self._handler_emnorge,
                # ★ v18
                "direkte_pdf": self._handler_direkte_pdf,
                "advokat":     self._handler_advokat,
            }.get(kjede, self._handler_generisk)

        # ── ★ v18: DIREKTE PDF ────────────────────
        def _handler_direkte_pdf(self, megler_url, dest, finn_id):
            """
            Lenken ER PDF-en. Ikke naviger dit.

            Dette er feilen fra v17: _handler_generisk starter med
            self._goto(megler_url). Chromium rendrer ikke en PDF-URL —
            den starter en nedlasting, page.goto() gir net::ERR_ABORTED,
            _goto() returnerer False og handleren gir opp med "Kunne
            ikke åpne megler-side" mens PDF-en ligger klar.

            _last_ned_pdf_url() sender allerede context-cookies og
            User-Agent, så FINN-sesjonen (inkl. cookie-samtykket vi tok
            på annonsesiden) følger med på kjøpet.
            """
            try:
                self._aksepter_cookies()
            except Exception:
                pass
            referer = None
            try:
                referer = self._page.url
            except Exception:
                pass

            p = self._last_ned_pdf_url(megler_url, dest, referer=referer)
            if p:
                return p, None

            # Fallback: la Chromium ta nedlastingen selv.
            p = self._vent_for_nedlasting(
                lambda: self._page.goto(megler_url, timeout=NAV_TIMEOUT_MS),
                dest, timeout_s=PDF_DOWNLOAD_TIMEOUT)
            if p:
                return p, None

            # Siste forsøk uten cookies — noen CDN-er avviser Cookie-header.
            try:
                import urllib.request
                req = urllib.request.Request(
                    megler_url, headers={"User-Agent": USER_AGENT,
                                         "Accept": "application/pdf,*/*"})
                with urllib.request.urlopen(
                        req, timeout=PDF_DOWNLOAD_TIMEOUT) as resp:
                    data = resp.read()
                if len(data) > 1000 and b"%PDF-" in data[:2048]:
                    with open(dest, "wb") as fh:
                        fh.write(data)
                    return dest, None
            except Exception as e:
                log.debug("    naken PDF-henting feilet: %s", e)

            # Ga URL-en ingen PDF likevel? Da er den kanskje en vanlig
            # side med .pdf i navnet — la den generiske ruta prøve.
            return self._handler_generisk(megler_url, dest, finn_id)

        # ── ★ v18: ADVOKATKONTOR ──────────────────
        def _handler_advokat(self, megler_url, dest, finn_id):
            """
            Advokatkontorer har sjelden meglerportal. Som regel ligger
            PDF-en rett på siden. Direktenedlasting først, så den
            generiske ruta — som er godt testet og håndterer accordion,
            popup og klikk.

            Egen rute hovedsakelig for statistikkens skyld: i v17 havnet
            disse i sekkeposten "annet", som lett faller under
            KJEDE_MIN_OK_RATE og da sperres for ALLE småmeglere samtidig.
            """
            if er_direkte_pdf_url(megler_url):
                return self._handler_direkte_pdf(megler_url, dest, finn_id)
            return self._handler_generisk(megler_url, dest, finn_id)

        # ── Meglerhandlere ────────────────────────
        def _handler_generisk(self, megler_url, dest, finn_id):
            if not self._goto(megler_url):
                return None, "Kunne ikke åpne megler-side"
            self._aksepter_cookies()
            self._lukk_modal()
            if self._detekt_epost_vegg():
                return None, "epost_vegg (generisk)"

            p = self._prov_lenker(self._vent_pdf_lenker(1.5), dest)
            if p: return p, None

            self._scroll_bunn()
            self._js(_JS_AAPNE_ACCORDION)
            p = self._prov_lenker(self._vent_pdf_lenker(), dest)
            if p: return p, None

            p = self._vent_for_nedlasting(
                lambda: self._klikk_tekst(
                    ["last ned salgsoppgave", "last ned prospekt", "se salgsoppgave",
                     "komplett salgsoppgave", "salgsoppgave"], timeout_ms=4000),
                dest, timeout_s=12)
            if p: return p, None

            p = self._prov_popup(["last ned salgsoppgave", "se salgsoppgave",
                                  "salgsoppgave"], dest)
            if p: return p, None

            if self._detekt_epost_vegg():
                return None, "epost_vegg etter klikk"

            p = self._vent_for_nedlasting(
                lambda: self._klikk_tekst(
                    ["jeg ønsker kun salgsoppgaven", "kun salgsoppgaven",
                     "kun salgsoppgave"], timeout_ms=3000),
                dest, timeout_s=10)
            if p: return p, None

            p = self._prov_lenker(self._vent_pdf_lenker(1.5), dest)
            if p: return p, None
            try:
                if ".pdf" in self._page.url.lower():
                    p = self._last_ned_pdf_url(self._page.url, dest)
                    if p: return p, None
            except Exception:
                pass
            return None, "Generisk: ingen PDF funnet"

        def _handler_emnorge(self, megler_url, dest, finn_id):
            """Eiendomsmegler Norge / Vitec Next — lenken bygges av JS.
            Retry fordi 403 fra emnorge nesten alltid er MIDLERTIDIG."""
            apnet = False
            for forsok in range(EMNORGE_FORSOK):
                if self._goto(megler_url):
                    # Bot-mellomside ber om samme URL med ?ki-cf-botcl=1
                    try:
                        if "just a moment" in (self._page.title() or "").lower():
                            sep = "&" if "?" in megler_url else "?"
                            self._goto(megler_url + sep + "ki-cf-botcl=1")
                            time.sleep(1.0)
                    except Exception:
                        pass
                    apnet = True
                    break
                ventetid = 4 * (forsok + 1)
                log.debug("    [w%d] emnorge %s: forsøk %d/%d feilet, venter %ds",
                          self.worker_id, finn_id, forsok + 1, EMNORGE_FORSOK, ventetid)
                time.sleep(ventetid)

            if not apnet:
                return None, f"Kunne ikke åpne emnorge-side ({EMNORGE_FORSOK} forsøk)"

            self._aksepter_cookies()
            self._lukk_modal()

            p = self._prov_lenker(self._vent_pdf_lenker(4.0), dest)
            if p: return p, None
            self._scroll_bunn()
            p = self._prov_lenker(self._vent_pdf_lenker(2.0), dest)
            if p: return p, None
            p = self._prov_popup(["last ned salgsoppgave", "salgsoppgave"], dest)
            if p: return p, None
            p = self._vent_for_nedlasting(
                lambda: self._klikk_tekst(["last ned salgsoppgave"], timeout_ms=4000),
                dest, timeout_s=15)
            if p: return p, None

            # Siste utvei: CloudFront-lenke direkte. CloudFront har INGEN
            # bot-beskyttelse (verifisert: HTTP 200 uten cookies).
            for d in (self._alle_lenker() or []):
                href = d.get("href") or ""
                if "cloudfront" in href.lower() and ".pdf" in href.lower():
                    p = self._last_ned_pdf_url(href, dest, referer=megler_url)
                    if p: return p, None

            return None, "emnorge: ingen PDF funnet"

        def _handler_aktiv(self, megler_url, dest, finn_id):
            if not self._goto(megler_url):
                return None, "Kunne ikke åpne Aktiv-side"
            self._aksepter_cookies()
            p = self._prov_lenker(self._vent_pdf_lenker(2.0), dest)
            if p: return p, None
            p = self._prov_popup(["salgsoppgave"], dest)
            if p: return p, None
            try:
                if ".pdf" in self._page.url.lower():
                    p = self._last_ned_pdf_url(self._page.url, dest)
                    if p: return p, None
            except Exception:
                pass
            return None, "Aktiv: ingen PDF-URL funnet"

        def _handler_nordvik(self, megler_url, dest, finn_id):
            if not self._goto(megler_url):
                return None, "Kunne ikke åpne Nordvik-side"
            self._lukk_modal()
            self._aksepter_cookies()
            if self._detekt_epost_vegg():
                return None, "epost_vegg på Nordvik"
            p = self._prov_lenker(self._vent_pdf_lenker(2.0), dest)
            if p: return p, None
            self._js(_JS_AAPNE_ACCORDION)
            time.sleep(0.6)
            p = self._prov_lenker(self._vent_pdf_lenker(2.0), dest)
            if p: return p, None
            return None, "Nordvik: ingen PDF etter accordion"

        def _handler_em1(self, megler_url, dest, finn_id):
            if not self._goto(megler_url):
                return None, "Kunne ikke åpne EM1-side"
            self._aksepter_cookies()
            if self._detekt_epost_vegg():
                return None, "epost_vegg på EM1"
            p = self._prov_lenker(self._vent_pdf_lenker(2.0), dest)
            if p: return p, None
            if not self._klikk_tekst(
                    ["last ned salgsoppgave", "se salgsoppgave",
                     "last ned prospekt", "komplett salgsoppgave"], timeout_ms=5000):
                return None, "EM1: ingen 'Last ned'-knapp"
            time.sleep(1.0)
            if self._detekt_epost_vegg():
                return None, "epost_vegg på EM1 (etter klikk)"
            p = self._vent_for_nedlasting(
                lambda: self._klikk_tekst(
                    ["jeg ønsker kun salgsoppgaven", "kun salgsoppgaven",
                     "kun salgsoppgave", "uten boligkjøperpakke"], timeout_ms=5000),
                dest, timeout_s=15)
            if p: return p, None
            p = self._prov_lenker(self._vent_pdf_lenker(2.0), dest)
            if p: return p, None
            return None, "EM1: nedlasting ikke utløst"

        def _handler_dnb(self, megler_url, dest, finn_id):
            if not self._goto(megler_url):
                return None, "Kunne ikke åpne DNB-side"
            self._aksepter_cookies()
            if self._detekt_epost_vegg():
                return None, "epost_vegg på DNB"
            p = self._prov_lenker(self._vent_pdf_lenker(2.0), dest)
            if p: return p, None
            p = self._prov_popup(["se pdf", "se salgsoppgave", "last ned salgsoppgave",
                                  "se komplett salgsoppgave"], dest, timeout_ms=6000)
            if p: return p, None
            return None, "DNB: PDF ikke funnet"

    # ══════════════════════════════════════════════
    # PDF-LESING
    # ══════════════════════════════════════════════
    def les_pdf_tekst(pdf_path):
        try:
            import fitz
            doc = fitz.open(pdf_path)
            biter = []
            for pno in range(min(doc.page_count, MAKS_PDF_SIDER)):
                try:
                    biter.append(doc[pno].get_text())
                except Exception:
                    continue
            doc.close()
            # ★ v16: reparer bitskiftet encoding før ALL videre bruk.
            # Gjelder også adresseuttrekket i hent_sted_fra_pdf.
            return reparer_encoding("\n".join(biter))
        except ImportError:
            log.error("pymupdf ikke installert! Kjør: pip install pymupdf")
            return ""
        except Exception as e:
            log.debug("Kunne ikke lese PDF %s: %s", pdf_path, e)
            return ""

    # ══════════════════════════════════════════════
    # FASE 2 — WORKER
    # ══════════════════════════════════════════════
    def fase2_worker(worker_id, oppgaver):
        scraper = conn = None
        gjort = truffet = 0
        t0 = time.time()
        try:
            conn = get_conn()
            scraper = FinnScraper(worker_id=worker_id)
            for listing in oppgaver:
                finn_id = listing.get("finn_id")
                url = listing.get("url")
                if not finn_id or not url:
                    continue

                if gjort > 0 and gjort % BROWSER_RESTART_EVERY == 0:
                    try:
                        scraper._start_browser()
                    except Exception as e:
                        log.error("  [w%d] Browser-restart feilet: %s", worker_id, e)

                dest = os.path.join(PDF_DIR, f"{finn_id}.pdf")
                if (GJENBRUK_PDF and os.path.exists(dest)
                        and os.path.getsize(dest) > 1000 and listing.get("poststed")):
                    result = {"salgsoppgave_pdf": dest,
                              "salgsoppgave_status": "lastet_ned",
                              "pdf_kjede": listing.get("pdf_kjede"),
                              "pdf_feilgrunn": None, "pdf_treff": [],
                              "_detalj_felt": None,
                              "pdf_url": listing.get("pdf_url")}   # ★ v18
                    try:
                        scraper._analyser_og_fyll(result, dest, finn_id)
                    except Exception as e:
                        log.debug("Reanalyse feilet for %s: %s", finn_id, e)
                else:
                    # ★ v18.1: kan ikke annonsen åpnes, har nettleseren
                    # trolig krasjet. Ny nettleser og ett forsøk til —
                    # ellers feiler ALLE annonser fram til neste omstart.
                    for forsok in range(2):
                        try:
                            result = scraper.hent_salgsoppgave(finn_id, url)
                        except Exception as e:
                            log.error("[w%d] hent_salgsoppgave krasjet for %s: %s",
                                      worker_id, finn_id, e)
                            result = {"salgsoppgave_status": "feil", "pdf_treff": [],
                                      "analyse_begrunnelse": str(e), "pdf_kjede": None,
                                      "pdf_feilgrunn": str(e), "signal_kilde": None}
                        if forsok > 0 or result.get("salgsoppgave_status") not in (
                                "feil", "feil_annonse"):
                            break
                        log.warning("  [w%d] %s: annonsen kunne ikke åpnes — "
                                    "starter ny nettleser og prøver igjen",
                                    worker_id, finn_id)
                        try:
                            scraper._start_browser()
                        except Exception as e:
                            log.error("  [w%d] Browser-restart feilet: %s", worker_id, e)
                    time.sleep(SLEEP_BETWEEN)

                with _listings_lock:
                    listing["salgsoppgave_pdf"]    = result.get("salgsoppgave_pdf")
                    listing["salgsoppgave_status"] = result.get("salgsoppgave_status")
                    listing["flagg_i_pdf"]         = result.get("flagg_i_pdf", 0)
                    listing["er_dodsbo"]           = result.get("er_dodsbo", 0)
                    listing["er_tvangssalg"]       = result.get("er_tvangssalg", 0)
                    listing["analyse_begrunnelse"] = result.get("analyse_begrunnelse")
                    listing["kontekst_sample"]     = result.get("kontekst_sample")
                    listing["pdf_kjede"]           = result.get("pdf_kjede")
                    listing["pdf_feilgrunn"]       = result.get("pdf_feilgrunn")
                    listing["signal_kilde"]        = result.get("signal_kilde")
                    listing["pdf_url"]            = (result.get("pdf_url")
                                                     or listing.get("pdf_url"))
                    if result.get("address"):
                        listing["address"] = result["address"]
                    for f in ("gateadresse", "postnr", "poststed",
                              "kommune", "fylke", "omrade"):
                        listing[f] = result.get(f) or listing.get(f)
                    df_felt = result.get("_detalj_felt") or {}
                    for f in ("property_type", "ownership", "bedrooms", "size_m2"):
                        if not listing.get(f) and df_felt.get(f):
                            listing[f] = df_felt[f]
                    treff = list(result.get("pdf_treff") or [])
                    listing["treff_ord"] = ", ".join(sorted(set(treff))) if treff else None
                    listing["kategori"] = beregn_kategori(listing)

                if listing["er_dodsbo"] or listing["er_tvangssalg"]:
                    truffet += 1

                lagre_til_db(conn, [listing], stille=True)
                gjort += 1
                if gjort % 50 == 0:
                    fart = gjort / max(time.time() - t0, 1) * 60
                    log.info("  [w%d] %d/%d  (%.0f/min, %d treff)",
                             worker_id, gjort, len(oppgaver), fart, truffet)
                    save_pdf_stats()

        except Exception as e:
            log.error("[w%d] Worker krasjet: %s", worker_id, e)
            log.error(traceback.format_exc())
        finally:
            if scraper:
                try: scraper.quit()
                except Exception: pass
            if conn:
                try: conn.close()
                except Exception: pass
        log.info("  [w%d] Ferdig: %d oppgaver, %d treff, %.1f min.",
                 worker_id, gjort, truffet, (time.time() - t0) / 60)

    # ══════════════════════════════════════════════
    # FASE 1
    # ══════════════════════════════════════════════
    def kjor_fase1(cp, conn):
        all_listings = cp.get("listings", [])
        log.info("╔═══════════════════════════════════════╗")
        log.info("║  FASE 1: Scraper søkeresultater        ║")
        log.info("╚═══════════════════════════════════════╝")

        scraper = FinnScraper(worker_id=0)
        t0 = time.time()
        try:
            if not cp.get("partisjoner"):
                cp["partisjoner"] = scraper.lag_pris_partisjoner()
                cp["fase1_part_index"] = 0
                save_checkpoint(cp, force=True)
            partisjoner = cp["partisjoner"]
            seen = {l.get("finn_id") for l in all_listings if l.get("finn_id")}
            stopp = False
            sider_totalt = 0                                    # ★ v18.1

            for pidx in range(cp.get("fase1_part_index", 0), len(partisjoner)):
                lo, hi = partisjoner[pidx]
                log.info("═══ Partisjon %d/%d  pris %s–%s ═══",
                         pidx + 1, len(partisjoner),
                         lo if lo is not None else "0",
                         hi if hi is not None else "∞")

                tomme = 0
                for page_num in range(1, FINN_SIDE_CAP + 1):
                    url = bygg_sok_url(lo, hi, page_num)

                    # ★ v18.1: ny nettleser med jevne mellomrom, så den
                    # ikke går tom for minne og krasjer (EPIPE).
                    sider_totalt += 1
                    if sider_totalt % FASE1_RESTART_EVERY == 0:
                        try:
                            scraper._start_browser()
                        except Exception as e:
                            log.error("Browser-restart feilet: %s", e)

                    # ★ v18.1: krasjet nettleseren likevel? Ny nettleser og
                    # prøv SAMME side igjen, i stedet for å gi opp partisjonen.
                    sidelisting = None
                    for forsok in range(1, NAV_FORSOK + 1):
                        try:
                            if not scraper._goto(url, vent_selector="section article",
                                                 vent_ms=8000):
                                raise RuntimeError("kunne ikke åpne siden")
                            if PAGE_LOAD_WAIT:
                                time.sleep(PAGE_LOAD_WAIT)
                            sidelisting = scraper.scrape_search_page()
                            break
                        except Exception as e:
                            log.warning("Side %d (part %d) feilet, forsøk %d/%d: %s "
                                        "— starter ny nettleser",
                                        page_num, pidx + 1, forsok, NAV_FORSOK, e)
                            try:
                                scraper._start_browser()
                            except Exception as e2:
                                log.error("Browser-restart feilet: %s", e2)
                                time.sleep(5)
                    if sidelisting is None:
                        log.error("Klarte ikke åpne %s etter %d forsøk", url, NAV_FORSOK)
                        break

                    if not sidelisting:
                        tomme += 1
                        if tomme >= 2:
                            break
                        time.sleep(4)
                        continue
                    tomme = 0

                    nye = [l for l in sidelisting
                           if l.get("finn_id") and l["finn_id"] not in seen]
                    for l in nye:
                        seen.add(l["finn_id"])
                    all_listings.extend(nye)

                    if page_num % 10 == 0 or not nye:
                        log.info("  Part %d side %d: %d nye (totalt %d, %.0f/min)",
                                 pidx + 1, page_num, len(nye), len(all_listings),
                                 len(all_listings) / max(time.time() - t0, 1) * 60)

                    cp["listings"] = all_listings
                    save_checkpoint(cp)

                    if MAKS_ANNONSER is not None and len(all_listings) >= MAKS_ANNONSER:
                        all_listings = all_listings[:MAKS_ANNONSER]
                        log.info("★ TEST-GRENSE nådd (%d).", MAKS_ANNONSER)
                        stopp = True
                        break

                cp["fase1_part_index"] = pidx + 1
                cp["listings"] = all_listings
                save_checkpoint(cp, force=True)
                if stopp:
                    break
        finally:
            scraper.quit()

        lagre_til_db(conn, all_listings)
        cp["listings"] = []
        cp["listings_i_db"] = True
        cp["fase1_done"] = True
        save_checkpoint(cp, force=True)
        log.info("Fase 1 ferdig: %d unike annonser på %.1f min",
                 len(all_listings), (time.time() - t0) / 60)
        return all_listings

    # ══════════════════════════════════════════════
    # FASE 2
    # ══════════════════════════════════════════════
    def kjor_fase2(all_listings):
        kandidater = [l for l in all_listings
                      if l.get("finn_id") and l.get("url")
                      and (l.get("salgsoppgave_status") or "ikke_sjekket")
                      not in FASE2_FERDIG_STATUS]
        if MAKS_ANNONSER is not None:
            kandidater = kandidater[:MAKS_ANNONSER]

        # Rader som mistet PDF forrige runde prøves FØRST — de er mest
        # sannsynlig midlertidige 403-er som nå har roet seg.
        retry = [l for l in kandidater
                 if l.get("salgsoppgave_status") == "pdf_ikke_funnet"]
        resten = [l for l in kandidater
                  if l.get("salgsoppgave_status") != "pdf_ikke_funnet"]
        kandidater = retry + resten

        log.info("")
        log.info("╔═════════════════════════════════════════════╗")
        log.info("║  FASE 2: PDF + SETNINGSANALYSE + STED (v17) ║")
        log.info("║  %2d parallelle workers                      ║", NUM_WORKERS)
        log.info("║  Kandidater: %6d                         ║", len(kandidater))
        log.info("║  — derav retry (pdf_ikke_funnet): %5d     ║", len(retry))
        log.info("╚═════════════════════════════════════════════╝")

        if not kandidater:
            log.info("Ingen kandidater — Fase 2 allerede ferdig.")
            return all_listings

        chunks = [[] for _ in range(NUM_WORKERS)]
        for idx, l in enumerate(kandidater):
            chunks[idx % NUM_WORKERS].append(l)

        t0 = time.time()
        with ThreadPoolExecutor(max_workers=NUM_WORKERS) as ex:
            futures = {ex.submit(fase2_worker, wid, chunk): wid
                       for wid, chunk in enumerate(chunks) if chunk}
            ferdig = 0
            for fut in as_completed(futures):
                wid = futures[fut]
                try:
                    fut.result()
                except Exception as e:
                    log.error("Worker %d returnerte feil: %s", wid, e)
                ferdig += 1
                log.info("  Worker %d/%d ferdig.", ferdig, len(futures))
        log.info("Fase 2 ferdig på %.1f min (%.0f annonser/min)",
                 (time.time() - t0) / 60,
                 len(kandidater) / max(time.time() - t0, 1) * 60)
        return all_listings

    # ══════════════════════════════════════════════
    # KJØR
    # ══════════════════════════════════════════════
    log.info("╔══════════════════════════════════════════════╗")
    log.info("║  Finn Dødsbo/Tvangssalg-Scraper v18.1         ║")
    log.info("║  v17-deteksjon UENDRET + bedre PDF-henting   ║")
    log.info("╚══════════════════════════════════════════════╝")
    log.info("  Direkte PDF .......... %s", "PÅ" if BRUK_DIREKTE_PDF else "AV")
    log.info("  Utvidet lenkesøk ..... %s", "PÅ" if BRUK_UTVIDET_LENKESOK else "AV")
    log.info("  Innbygd PDF-søk ...... %s", "PÅ" if BRUK_INNBYGD_PDF_SOK else "AV")

    try:
        import fitz  # noqa: F401
    except ImportError:
        log.error("pymupdf mangler! Kjør: pip install pymupdf")
        return
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        log.warning("⚠ openpyxl mangler — installer: pip install openpyxl")

    Path(PDF_DIR).mkdir(exist_ok=True)
    try:
        conn = get_conn()
        init_db(conn)
    except RuntimeError as e:
        log.error("")
        for linje in str(e).splitlines():
            log.error(linje)
        return
    except sqlite3.DatabaseError as e:
        log.error("Databasefeil ved oppstart: %s", e)
        log.error("Prøv: slett finn_dodsbo.db-wal og finn_dodsbo.db-shm, "
                  "eller flytt prosjektet ut av OneDrive-mappa.")
        return
    cp = load_checkpoint()

    listings = []
    fullfort = False
    t_start = time.time()
    try:
        if not cp.get("fase1_done"):
            listings = kjor_fase1(cp, conn)
        elif cp.get("listings_i_db"):
            listings = last_listings_fra_db(conn)
            log.info("Fase 1 ferdig fra før — lastet %d annonser fra DB.", len(listings))
        else:
            listings = cp.get("listings", [])
            log.info("Fase 1 ferdig fra før (%d annonser i checkpoint).", len(listings))
        listings = kjor_fase2(listings)
        fullfort = True
    except KeyboardInterrupt:
        log.warning("⚠ Avbrutt av bruker. Fremdrift ligger i DB.")
        if not listings:
            listings = last_listings_fra_db(conn)
    except Exception as e:
        log.error("Uventet feil: %s", e)
        log.error(traceback.format_exc())
        if not listings:
            listings = last_listings_fra_db(conn)

    if listings:
        try:
            lagre_til_db(conn, listings)
        except Exception as e:
            log.error("DB-lagring feilet: %s", e)

        xl_path = eksporter_excel(listings, bare_treff=KUN_TREFF_I_EXCEL)
        if xl_path:
            log.info("📊 OUTPUT-FIL: %s", xl_path)

        if KUN_TREFF_I_EXCEL:
            today = datetime.now().strftime("%Y-%m-%d")
            komplett = eksporter_excel(
                listings, filnavn=f"finn_dodsbo_komplett_{today}.xlsx",
                stille=True, bare_treff=False)
            if komplett:
                log.info("🗄  Komplett backup: %s", komplett)

        save_pdf_stats()
        skriv_rapport(listings)

        if fullfort:
            try:
                Path(CHECKPOINT_PATH).unlink()
                log.info("Checkpoint slettet (fullført).")
            except Exception:
                pass
    else:
        log.warning("Ingen listings — recovery fra DB...")
        eksporter_fra_db()

    conn.close()
    log.info("Total kjøretid: %.1f min.", (time.time() - t_start) / 60)
finnDødsboScraperv18(maks_annonser=None)
