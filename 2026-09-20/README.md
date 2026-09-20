# Rettelse 2026-09-20 — hent alt, si om det kom ned, handle uten kostnader

Denne mappen gjør fire ting du ba om, og retter to feil den fant på veien.

**Dette er den eneste mappen du trenger.** Den erstatter `2026-09-18`, som er
fjernet fra denne grenen — alt derfra som fortsatt gjelder ligger her, rettet.

---

## Slik bruker du den

### Før du kjører noe som helst: fire ting må ligge på plass

Alt dette ligger i **rotmappen** — der `master.py` ligger, altså mappen over
denne:

```text
ChatRepo\
├── master.py, Only_260820.py, ...      koden som fulgte med
├── 2026-09-20\                         denne mappen
├── ExcelData\                          DINE data  (1)
├── data\                               innsidedata (2)
├── mail_passord.txt                    Gmail-app-passord (3)
└── .venv\                              lages av SETUP.cmd (4)
```

1. **`ExcelData`** — kopier den inn hit, eller oppgi hvor den ligger med
   `--excel-dir "D:\Din\Sti\ExcelData"`. På den opprinnelige PC-en finnes den
   fortsatt automatisk. En lokal `ExcelData` har forrang.
2. **`data`** — innsidedataene. Lages av kjøringen hvis den ikke finnes, men
   har du den fra før, spar deg selv for en lang nedlasting og kopier den inn.
3. **`mail_passord.txt`** — hele fila er Gmail-app-passordet, de fire gruppene
   med mellomrom limt rett inn. Ikke ditt vanlige Gmail-passord; et app-passord
   lages under Google-kontoen din. Uten den bygges mailen, men sendes ikke.
   (Alternativt: miljøvariabelen `AKSJE_MAIL_APP_PASSWORD`.)
4. **`.venv`** — lages av `SETUP.cmd`. Ikke rør den.

### Én gang, på en ny maskin

```text
1.  SETUP.cmd          installerer Python-pakkene og Chromium. Tar noen minutter.
2.  CHECK_SETUP.cmd    sier om oppsettet er på plass.
```

`SETUP.cmd` trenger **Python 3.12 med Python Launcher** («py») installert
først. Uten den sier den fra og stopper.

### Hver gang du vil ha en rapport

```text
3.  2026-09-20\RUN.cmd --preflight     hva mangler akkurat nå?  (sekunder)
4.  2026-09-20\RUN.cmd --mail-kladd    full kjøring, men send ingen mail
5.  2026-09-20\RUN.cmd                 full kjøring, sender mailen
```

Du kan **dobbeltklikke** på `RUN.cmd` i Utforsker — da blir vinduet stående
åpent til slutt så du rekker å lese svaret. Vil du ha med et flagg, åpne
Ledetekst i rotmappen og skriv kommandoen.

**Punkt 3 er den du bør venne deg til.** Den bruker nøyaktig samme vurdering som
datastatusblokken i mailen, og svarer på sekunder. Uten den oppdager du først
etter halvannen time at en kursfil var gammel.

**Punkt 4 er verdt å ta første gang.** Mailen bygges og lagres som
`data\7_master\master_mail_<dato>_<klokkeslett>.html` — åpne den i nettleseren
— men ingenting sendes.

**Punkt 5 tar tid.** Første kjøring laster faktisk ned kurser, skraper artikler
og kjører språkmodellen. Regn med over en time. La vinduet stå.

### Bare se hvordan mailen ser ut, uten å kjøre noe

```text
.venv\Scripts\python.exe 2026-09-20\demo_mail.py
```

Lager `demo_mail.html` av **oppdiktede** tall, merket som demonstrasjon øverst
i selve mailen.

### Hva sluttkoden betyr

| Kode | Betyr | Hva du gjør |
|---|---|---|
| `0` | fullført uten feil | ingenting |
| `1` | rettelsene kunne ikke påføres | les meldingen; rotfilene er endret |
| `2` | ufullstendig | les datastatus øverst i mailen |
| `3` | mailen kunne ikke sendes | HTML-kopien ligger i `data\7_master` |

### Én ting å passe på

`RUN_ALL.cmd` i rotmappen finnes fortsatt og gjør nøyaktig det den alltid har
gjort — **uten** rettelsene i denne mappen. Bruk `2026-09-20\RUN.cmd`.

---

1. **Masteren henter ned alt datagrunnlaget selv** — og skriver det med navnet
   strategiene faktisk leser.
2. **Mailen begynner med datastatus per strategi.** Kom dataene ned? Hvor
   ferske er de? Teller strategien i fellestallene?
3. **Ingen handelskostnader noe sted** — heller ikke i variantvalget, som var
   det siste stedet de levde.
4. **En strategi uten ferske data utelates og navngis**, i stedet for å stoppe
   hele mailen. De øvrige beregnes med lik vekt: tre gir 33 % hver.

Kapitalfordelingen er ellers uendret: lik vekt til hver strategi, justert ved
månedsslutt. `PBROE_All3` og `SentimentMomentumV31` er byte-identiske etter
patchen — det kontrolleres automatisk i testene.

---

## 0. To feil denne utgaven retter i forrige rettelse

**Tickerfila ble skrevet med et navn ingen leser.** `2026-09-18` bygget
`AllTickers_OSEBX_TW_<dagens dato>.xlsx`. Men `PBROE_All3` leser en **fast**
sti (`Only_260820.py` linje 278), og `SentimentManagement` gjør det samme fire
steder til:

```text
...\ExcelData\Data_BT\AllTickers_OSEBX_TW_260428.xlsx
```

Begge funksjonene er hash-beskyttet og kan ikke endres. Fila må altså bære
navnet de spør etter. Den dagsdaterte fila ville aldri blitt åpnet: PB-ROE
ville ha lest aprilfila videre, eller stoppet på at den manglet. Nå skrives
grunnlagsfila som `AllTickers_OSEBX_TW_260428.xlsx`, med en datert kopi ved
siden av for sporbarhet. `Stock_Prices_*.xlsx` og `Step4_Sentiment_Changes_*.xlsx`
leses derimot med glob og nyeste tidsstempel, så der virker daterte navn.

**Step4-patchen traff feil sted.** Den samme blokken er nå hentet ut av
rotfila på linjenummer, og ankerlinjene er frosset i `anchors.json`. Bommer et
linjenummer, feiler byggingen med en gang i stedet for å produsere kode som
kjører men gjør noe annet. Se «Hvordan patchene er bygget» nederst.

---

## 1. Datastatus øverst i mailen

Det første i mailen er en tabell med én linje per strategi:

| Strategi | Nedlasting | Siste observasjon | Alder | Status | Følge |
|---|---|---|---|---|---|
| PB-ROE-Momentum | ingen feil | 2026-08-31 | 20 dager | **OK** | Inngår |
| NLP Sentiment — ledelse | ingen feil | 2026-09-18 | 2 dager | **OK** | Inngår |
| Sentiment Momentum v3.1 | Kursdata: degradert — … | 2026-08-18 | 33 dager | **FORELDET** | Utelatt |
| Innsidehandel — Oslo Børs | ingen feil | 2026-09-18 | 2 dager | **OK** | Inngår |

Under den står nøyaktig hva som mangler og hva det betyr, og så en tabell over
grunnlagsfilene kjøringen bygde, med radantall og siste dato.

Statusverdiene:

| Status | Betyr |
|---|---|
| `OK` | eksporten kan leses, er gyldig, og siste observasjon er fersk nok |
| `FORELDET` | for gammel — eller datert i fremtiden, som er en merkelapp og ikke en kurs |
| `MANGLER` | ingen brukbare observasjoner |
| `FEIL` | kunne ikke leses, eller er erklært ugyldig |

Grensen er **7 dager** for de tre daglige strategiene og **45 dager** for
PB-ROE, som bare eksporterer månedsverdier. Det er denne forskjellen som gjør
at den samme alderen er grei for én strategi og diskvalifiserende for en annen.

**Dette er porten som manglet 2026-09-18.** Den gang sto Sentiment Momentum
som `OK` etter 0,9 minutter. Den hadde ikke hentet noe: den kjørte backtesten
på nytt over kurser som sluttet 2026-08-19, tretti dager før rapporten. `OK`
betydde «leste gamle data uten å feile».

`preflight_data.py` bruker **nøyaktig samme** vurdering, så preflight og mail
kan ikke være uenige om hva som er ferskt:

```text
2026-09-20\RUN.cmd --preflight
```

Vil du se hvordan mailen ser ut før du starter en kjøring på halvannen time:

```text
python 2026-09-20\demo_mail.py            tre av fire har ferske data
python 2026-09-20\demo_mail.py --alle-ok  alle fire har ferske data
```

Den lager `demo_mail.html` av **oppdiktede** tall, merket som demonstrasjon
øverst i selve mailen. Den leser ingen ExcelData og sender ingenting.

---

## 2. Masteren henter ned alt selv

`master.py` *kontrollerte* at tre filer fantes og avbrøt hvis de ikke gjorde
det. Ingenting i repoet lagde dem:

| Fil | Leses av | Ble laget av |
|---|---|---|
| `Data_BT/AllTickers_OSEBX_TW_260428.xlsx` | `PBROE_All3`, `SentimentManagement` | et annet program |
| `Data_BT1/FinancialData/Stock_Prices_*.xlsx` | `SentimentMomentumV31` | et annet program |
| `DataNLP/Step4_Sentiment_Changes_*.xlsx` | `SentimentMomentumV31` | et annet program |

Ingen hadde kjørt det siden 2026-08-19. Det er hele forklaringen på de måned
gamle kursene: fila var ikke gammel fordi noe feilet, den var gammel fordi
ingenting oppdaterte den.

**Alt som trengs lastes allerede ned av denne pakken:**

| Byggestein | Hentes allerede av |
|---|---|
| Euronext-aksjelista | `innsidehandel_pipeline.sikre_aksjeliste` |
| Daglige kurser (yfinance) | `innsidehandel_pipeline.steg4_kurser` |
| FinBERT-score per artikkel | `SentimentManagement` → `NLP_Sentiment_Detail_*.xlsx` |

De tre filene er altså omforminger av data masterkjøringen allerede har.
`data_acquisition.py` gjør omformingen, og masteren kaller den selv.

**Rekkefølgen er viktig.** Step4 bygges av scorene skrapingen nettopp skrev, så
den må ligge mellom skrapingen og `SentimentMomentumV31`. Masteren henter
derfor i to trinn: tickerliste og kurser *før* analysene, Step4 inne i
`kjor_alle` rett etter skrapingen.

### Tre ting som gjør hentingen robust

**Gjenforsøk med økende pause.** Euronext og Yahoo feiler forbigående. Tre
forsøk med 2, 4 og 8 sekunders pause; siste feil kastes videre og havner i
statusraden.

**En dårligere fil får aldri overskrive en god.** Halvveis nedlasting ga før en
tynn kursfil som så fersk ut. Nå sammenlignes den nye med den som ligger der.
Er den under 80 % så mange rader, eller slutter tidligere, beholdes den gamle
og statusen blir `DEGRADERT`. Da blir strategien utelatt **på alder** — som er
riktig utfall. En tynn fil som ser fersk ut er det ikke.

**Henting som feiler velter ikke en kjøring alene.** Feiler den mens filene
allerede ligger der og er ferske, er ingen skade skjedd — og datastatusen sier
det uansett. Unntaket er Step4: feiler den, stopper SentMom-analysen, for uten
fersk Step4 leser den den forrige.

Nye brytere: `--ingen-datahent` og `--tving-datahent`.

---

## 3. Ingen handelskostnader — heller ikke i valget

De fire strategiene handlet allerede uten kostnader. Innsidemotoren har
`spread_pst = 0.00` og `kurtasje_pst = 0.00` som standard, og de tre andre sier
«Kostnad er satt til 0 %» i sine egne regler. Kostnadene levde bare ett sted
igjen — i **valget** av innsidevariant:

| | Før | Nå |
|---|---|---|
| Krav | positiv trenings-CAGR etter 0,15 % per side | positiv trenings-CAGR **uten kostnader** |
| Mål | høyest CAGR i svakeste treningshalvdel etter 0,80 % per side | **høyest trenings-CAGR uten kostnader** |
| Likhet | lavere omsetning | best svakeste halvdel, så lavere omsetning |
| Minstekrav | 252 treningsdager, 20 innganger, 5 aksjer | **uendret** |
| Horisont | bare data til treningsslutt | **uendret** |

Den gamle regelen optimaliserte for et kostnadsregime som ikke gjelder.

**Horisonten er med vilje ikke endret.** Valget leser fortsatt bare data til og
med treningsslutt (standard `2025-06-30`). Å velge varianten med høyest CAGR
over hele historikken ville gitt et penere tall og vært verdiløst: varianten
ville da være valgt med data den etterpå rapporterer avkastning på.

**Minstekravene står igjen av samme grunn.** Uten dem vinner en variant med tre
heldige handler over en med tre hundre, og «høyest CAGR» blir en måling av
flaks i stedet for av regelen.

Kostnadsreplayene ved 0,15 % og 0,80 % er nå **ren opplysning**, ikke en regel.
De koster to ekstra fulle backtester per variant og er av som standard. Slå dem
på med `--kostnadstest`. Mailen viser i stedet trening, senere periode og de to
treningshalvdelene uten kostnader — tallene kjøringen faktisk bygger på.

`POLICY_VERSION` er byttet til `insider-zero-cost-v1`, så et lagret valg fra den
gamle regelen bygges på nytt i stedet for å bli gjenbrukt i stillhet.

---

## 4. Én strategi som feiler stopper ikke de tre andre

Før gikk enhver analysefeil, manglende grunnlagsfil eller avvist eksport rett i
`errors`, og `errors` blokkerte hele kapitalberegningen. Én foreldet kursfil ga
«Analysis incomplete» og ingen tall i det hele tatt.

Nå vurderes hver strategi for seg:

* problemet havner i **datastatusen**, ikke i `errors`;
* strategien **utelates** fra fellestallene og navngis øverst i mailen;
* de øvrige blandes med **lik vekt** — fire gir 25 % hver, tre gir 33 %;
* `N_Strategier` og `Andel_Per_Strategi_Pst` følger med, så mailen ikke kan
  skrive «25 % hver» over tre delporteføljer;
* strategiens egen seksjon lenger nede viser fortsatt det den faktisk har.

En utelatt strategi erstattes **ikke** med null avkastning, og den gamle verdien
videreføres ikke som om den var dagens.

Under to strategier med ferske data gir ingen samlet portefølje. Da sier mailen
det i klartekst i stedet for å kaste en stakksporing.

---

## 5. To eldre feil som følger med

**Ledelsessentimentets prisvakt** (fra 2026-09-18, uendret her).
`kontroller_priser` flagger ethvert sprang på 4× eller mer, og `hent_kurser`
avbrøt hele kjøringen på hvilket som helst av dem — også for tickere uten ett
eneste signal. Et sprang som ligger innenfor 0,5 % av en tierpotens
(BSP.OL: 0,101440 → 10,144007, forhold 100,000) er et enhetsavvik fra
datakilden, beviselig fra tallene alene. Det rettes **bakover**, så de nyeste
kursene — de åpne posisjoner verdsettes mot — aldri endres. Alt annet blokkerer
fortsatt publisering. Hver endring skrives til `management_price_issues.csv`.

**`mail_strategier.py` ble ikke funnet.** `master.py` lette etter
`mail/mail_strategier.py`, men fila ligger flatt i roten i dette repoet. De tre
enkeltstrategiene falt ut av mailen uten annen grunn enn plasseringen. Nå
brukes roten når `mail/`-mappen ikke finnes; undermappen har forrang når den
gjør det.

---

## Slik tar du det i bruk

```text
2026-09-20\RUN.cmd                     full kjøring, sender mail
2026-09-20\RUN.cmd --mail-kladd        bygg mailen, ikke send
2026-09-20\RUN.cmd --preflight         hva blokkerer akkurat nå?
2026-09-20\RUN.cmd --tving-datahent    bygg grunnlagsfilene på nytt
2026-09-20\RUN.cmd --kostnadstest      ta med kostnadstabellen som opplysning
2026-09-20\RUN.cmd --vis-patcher       list patchene, kjør ingenting
2026-09-20\RUN.cmd --selvtest          kjør testene
```

Uten Windows: `python 2026-09-20/run.py` med de samme flaggene. Alle flagg
`master.py` tar virker her.

`RUN.cmd` bruker samme `.venv` som `SETUP.cmd` lagde. Første kjøring tar lengre
tid enn før — kursene hentes faktisk. `RUN_ALL.cmd` finnes fortsatt og gjør
nøyaktig det den alltid har gjort, uten rettelsene.

**Rekkefølge på en fersk maskin:** `SETUP.cmd` → `CHECK_SETUP.cmd` →
`2026-09-20\RUN.cmd --preflight` → `2026-09-20\RUN.cmd`.

---

## Ingenting i repoet er endret

Alt ligger i denne mappen. Ingen kildefil som fantes fra før er endret.

Den eneste endringen utenfor mappen er at `2026-09-18` er **fjernet** fra denne
grenen. Den er erstattet, ikke bare supplert: alt derfra som fortsatt gjelder
ligger her — `price_repair.py`, `freshness.py`, importkroken og alle
patchblokkene — og to av rettelsene derfra var feil (se avsnitt 0). Den gamle
mappen ligger fortsatt i historikken og på `main`.

```text
git diff c4fb146 -- . ":!2026-09-20" ":!2026-09-18"     # tom
```

Fem av rettelsene gjelder likevel filer som allerede fantes:

| Fil | Blokker | Hva |
|---|---|---|
| `master.py` | 12 | henter grunnlagsdata, bygger datastatus, lar én strategi feile alene |
| `portfolio_blend.py` | 13 | lik vekt til N strategier, ikke alltid fire |
| `capital_mail.py` | 7 | datastatus øverst; all tekst teller strategiene |
| `insider_selection.py` | 6 | valg uten kostnader, uendret horisont |
| `Only_260820.py` | 1 | prisvakten retter enhetsavvik, blokkerer resten |

De endres **ikke på disk**. `patched_import.py` installerer en importkrok: når
en av dem importeres, leses kildekoden fra roten, patchene i `patches.json`
påføres **teksten i minnet**, og resultatet kompileres og kjøres som modulen.

Kjør `run.py` og du får rettet oppførsel. Kjør `master.py` direkte og du får
nøyaktig det som lå der før. Filene åpnes aldri for skriving.

Det skrives ingen `.pyc` for en patchet modul — en bytekodefil nøklet til den
originale kilden ville ellers blitt servert til et senere, upatchet import.
`linecache` fylles med den patchede kilden, så tracebacks og
`inspect.getsource()` viser koden som faktisk kjører.

### Hvordan patchene er bygget

`build_patches.py` lager `patches.json` av rotfilene. Hver redigering oppgir et
**linjeintervall**, ikke en avskrift, så originalblokken hentes ut av fila selv
og kan ikke skrives feil. Fire kontroller kjøres på hver blokk:

1. blokken finnes **nøyaktig én gang** i fila;
2. **ankerlinja stemmer** med `anchors.json` — en frosset kopi av første linje;
3. **innrykket** på første linje er det samme i blokk og erstatning;
4. den ferdig patchede fila **parser som Python**.

Punkt 2 og 3 finnes fordi punkt 1 og 4 ikke er nok: Step4-patchen traff først
kommentaren over `analyser`, var unik, og ga gyldig Python — men den
opprinnelige tilordningen rett under overskrev den, og Step4 ville aldri ha
blitt bygget.

Blokkene lagres med filas **egne linjeskift**. Det er nødvendig:
`Only_260820.py` blander 12 373 CRLF-linjer med 151 rene LF, og
`insider_selection.py` 269 mot 37. Å sette en blokk sammen igjen med én
konvensjon ville ikke ha truffet.

```text
python 2026-09-20/build_patches.py --sjekk    kontroller uten å skrive
python 2026-09-20/build_patches.py            skriv patches.json
python 2026-09-20/build_patches.py --frys     frys ankerlinjene på nytt
```

---

## Hva som er verifisert, og hva som ikke er det

### Verifisert her, uten pandas og uten nett

* **174 tester i `tests/` passerer.**
* Alle 39 patchblokker treffer de urørte rotfilene; ankerlinjene stemmer;
  `patch(patch(x)) == patch(x)`; hver patchet fil parser.
* `patches.json` er nøyaktig det `build_patches.py` lager av dagens rotfiler.
* **`PBROE_All3` og `SentimentMomentumV31` har identiske abstrakte syntakstrær
  før og etter patchen.** Bare prisvakten i `SentimentHendelseLab` er rørt i
  `Only_260820.py`.
* Rotfilene er byte-identiske (SHA-256) etter at patchene er bygget og påført.
* Repoets egne `test_portfolio_blend` (15), `test_capital_mail` (3) og
  `test_master` (24) passerer **mot de patchede modulene**.
* `test_insider_selection` passerer uendret mot den **upatchede** rotfila
  (16/16). Mot den patchede feiler fem tester, ved navn og med vilje — de
  beskriver kostnadsregelen vi erstattet, og fixturen deres oppgir ingen
  `Train_CAGR_Pst` i det hele tatt. `tests/test_repo_suites.py` fastslår at det
  er nøyaktig disse fem.
* Blandingen med 2, 3 og 4 kurver: lik vekt, full startkapital fordelt, og
  månedsavkastningen er nøyaktig gjennomsnittet av delenes. N kopier av samme
  kurve gir kurvens egen avkastning, uansett N.
* Hele mailen, inkludert datastatusblokken, rendres av `demo_mail.py`.

### Ikke verifisert — og det kan ikke verifiseres i dette miljøet

Miljøet rettelsene ble skrevet i **har ingen nettilgang** til Yahoo Finance,
`live.euronext.com` eller `newsweb.oslobors.no`; utgående forbindelser til alle
tre avvises av en proxy. Derfor:

* **Ingen ekte nedlasting er kjørt.** Verken Euronext-lista, yfinance-kursene
  eller artikkelskrapingen. Gjenforsøkslogikken er testet med oppdiktede feil,
  ikke mot en ekte kilde som er nede.
* **Ingen av de tre grunnlagsfilene er faktisk skrevet.** Radbyggingen er testet
  rad for rad, men `write_workbook`, `workbook_shape`, `read_nlp_detail`,
  `ensure_stock_list` og `ensure_prices` krever pandas, yfinance og nett.
  At skjemaene stemmer er lest ut av koden som leser dem (`load_tickers`,
  `DataLoader.load_all`, `PriceBook`), ikke bekreftet mot en ekte fil.
* **`Sentiment_Change` er utledet** av hva strategien sier den handler på
  («kjøper på endringen fra forrige rapport»). Det originale programmet finnes
  ikke her, så skalaen kan avvike fra den SentMom ble kalibrert på. Første
  kjøring bør sammenlignes mot den gamle `Step4`-fila før tallene brukes.
* **`repair_price_frames` er pandas-adapteren.** Beslutningslogikken under den
  er testet i detalj, men selve adapteren er ikke kjørt. Om alle åtte flaggede
  tickere faktisk *er* tierpotens-artefakter vet vi først når den kjøres mot
  ekte nedlastede kurser. BSP.OL er bekreftet fra tallene i `VALIDATION.md`;
  de sju andre er ikke dokumentert noe sted i repoet.
* **Ingen ekte masterkjøring, ingen SMTP.** Playwright/Chromium,
  FinBERT-nedlasting og Gmail-autentisering er urørt.
* **Ingen ekte avkastningstall er produsert.** Tallene i `demo_mail.py` er
  oppdiktet og merket som det i mailen den lager.

Kjør `--preflight` først på din egen maskin. Den svarer på sekunder hva som
faktisk kom ned.

### Kjente feil som fantes fra før og ikke er rørt

`test_corrections` (1 feil), `test_pipeline` (1) og `test_management_accounting`
(10) feiler likt med og uten patchen — manglende pandas, og at testene forventer
å ligge i en `tests/`-undermappe (`parents[1]`), slik README i roten beskriver.

---

## Filer

| Fil | Hva den gjør |
|---|---|
| `data_acquisition.py` | Bygger de tre grunnlagsfilene. Radlogikk i ren Python. |
| `data_status.py` | Kom dataene ned, per strategi — og hvem som blandes. |
| `mail_status.py` | Datastatusblokken øverst i mailen. Ren stdlib. |
| `zero_cost.py` | Variantvalg uten kostnader, uendret horisont. |
| `price_repair.py` | Klassifiserer og retter tierpotens-artefakter. |
| `freshness.py` | Ferskhetsport og månedsslutt-dekning. |
| `preflight_data.py` | Samme vurdering som mailen, før en lang kjøring. |
| `demo_mail.py` | Rendrer mailen av oppdiktede tall, uten å sende noe. |
| `patches.json` | Selve redigeringene, én post per blokk. |
| `anchors.json` | Frosne ankerlinjer, så et linjenummer ikke kan bomme stille. |
| `build_patches.py` | Bygger `patches.json` av rotfilene, med fire kontroller. |
| `patched_import.py` | Importkrok. Påfører blokkene i minnet, skriver aldri til disk. |
| `run.py`, `RUN.cmd` | Inngangspunkt. |
| `tests/` | 174 tester, kjører uten pandas og uten nett. |

```text
python -m unittest discover -s 2026-09-20/tests -t 2026-09-20/tests
```
