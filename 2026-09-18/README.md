# Rettelse 2026-09-18 — de to feilende strategiene, og datahentingen

Denne mappen retter tre ting: ledelsessentimentet som stoppet på prisvalidering,
Sentiment Momentum som rapporterte `OK` mens den kjørte på måned gamle kurser,
og den egentlige årsaken bak den andre — at **masteren aldri hentet ned sitt
eget datagrunnlag.**

Ingenting i mappen laster ned, sender mail eller endrer de hash-beskyttede
strategiene. `PBROE_All3` og `SentimentMomentumV31` er byte-identiske etter
patchen — det verifiseres automatisk før noe lagres.

---

## 1. Ledelsessentiment — FIKSET I KODE

**Hva som var galt.** `kontroller_priser` flagger enhver endring på 4x eller mer
mellom to observasjoner, og `hent_kurser` avbrøt hele kjøringen på hvilken som
helst av dem. Den behandlet to helt ulike ting likt:

| Observasjon | Hva det er | Kan det bevises fra dataene? |
|---|---|---|
| BSP.OL 0,101440 → 10,144007 (ratio 100,000) | Provider endret enhet (øre/krone) | **Ja** |
| Ratio 4,7 eller 0,21 | Ekte kursbevegelse, eller ukjent | Nei |

Åtte tickere ble flagget, og alle åtte stoppet hele analysen — også de som ikke
hadde et eneste signal.

**Hva som er gjort.** `price_repair.py` skiller de to. Et sprang som ligger
innenfor 0,5 % av en tierpotens behandles som et denominasjonsavvik og rettes;
alt annet blokkerer fortsatt publisering, akkurat som før.

Rettingen går **bakover**: segmentet *før* bruddet skaleres opp til å møte
segmentet etter. De nyeste kursene — de åpne posisjoner verdsettes mot — endres
aldri. Hver eneste endring skrives til `management_price_issues.csv` med faktor,
dato, før- og etterkurs.

Egenskapen som gjør dette trygt, og som testes: **ingen daglig avkastning endres,
bortsett fra den ene som er artefakten.** En omskalering av et helt segment er
en enhetskonvertering, ikke en kursjustering.

Ingenting klippes, interpoleres eller gjettes. Klarer ikke regelen å bevise at et
sprang er et enhetsavvik, stopper kjøringen som før — men nå med en liste over
hvilke tickere som faktisk må sjekkes manuelt, ikke alle åtte.

## 2. Masteren henter nå ned alt selv — FIKSET I KODE

**Hva som var galt.** `master.py` *kontrollerte* at tre filer fantes og avbrøt
hvis de ikke gjorde det. Ingenting i repoet lagde dem:

| Fil | Leses av | Ble laget av |
|---|---|---|
| `Data_BT/AllTickers_OSEBX_TW_*.xlsx` | `PBROE_All3.load_tickers()` | et annet program |
| `Data_BT1/FinancialData/Stock_Prices_*.xlsx` | `SentimentMomentumV31` | et annet program |
| `DataNLP/Step4_Sentiment_Changes_*.xlsx` | `SentimentMomentumV31` | et annet program |

README-en i roten sa «behold planen som lager dem først». Ingen hadde kjørt den
siden 2026-08-19. Det er hele forklaringen på at Sentiment Momentum backtestet
måned gamle kurser: filen var ikke gammel fordi noe feilet, den var gammel fordi
ingenting oppdaterte den.

**Poenget: alt som trengs lastes allerede ned av denne pakken.**

| Byggestein | Hentes allerede av |
|---|---|
| Euronext-aksjelista | `innsidehandel_pipeline.sikre_aksjeliste` |
| Daglige kurser (yfinance) | `innsidehandel_pipeline.steg4_kurser` |
| FinBERT-score per artikkel | `SentimentManagement` → `NLP_Sentiment_Detail_*.xlsx` |

De tre filene er altså omforminger av data masterkjøringen allerede har.
`data_acquisition.py` gjør omformingen, og masteren kaller den selv.

- **Tickerlista** — `Company` er den bare tickeren, fordi PB-ROE bygger
  `tradingview.com/symbols/OSL-<Company>/` av den. Skrives med `index=True`,
  fordi `load_tickers()` dropper den første kolonnen før den leser `Company`.
- **Kursfila** — lang form med `Date`, `Company`, `Ticker`, `Close`. `Company`
  hentes fra samme selskapsliste som Step4, slik at `_map_tickers` treffer.
- **Step4** — `Sentiment_Change` er bevegelsen fra selskapets **forrige**
  rapport, som er nøyaktig det strategien handler på. Første artikkel per
  selskap har ingen forgjenger og får 0,0.

**Rekkefølgen er viktig.** Step4 bygges av scorene skrapingen nettopp skrev, så
den må ligge mellom skrapingen og `SentimentMomentumV31`. Masteren gjør derfor
hentingen i to trinn: tickerliste og kurser *før* analysene, Step4 inne i
`kjor_alle` rett etter skrapingen.

**Henting velter aldri en kjøring alene.** Feiler den mens filene allerede
ligger der og er ferske, er ingen skade skjedd. Portene som faktisk avgjør er
`protected_input_errors` (fil mangler) og den nye `foreldede_grunnlagsdata`
(fil finnes, men er for gammel: kurser 7 dager, Step4 14, tickerliste 90).
Unntaket er Step4: feiler den, stopper analysen, for uten fersk Step4 leser
SentMom den forrige — og da er vi tilbake i 2026-09-18.

Nye brytere: `--ingen-datahent` og `--tving-datahent`.

## 3. Sentiment Momentum — RESTEN KAN IKKE FIKSES MED KODE

**Hva som var galt.** Strategien brukte 0,9 minutter og ble rapportert `OK`.
Den hentet ingenting: den kjørte backtesten på nytt over kursfiler som slutter
2026-08-19, tretti dager før rapporten. `OK` betydde «leste gamle data uten å
feile», ikke «dette er ferskt».

Årsaken ligger utenfor denne pakken. `SentimentMomentumV31` leser
`Data_BT1/FinancialData/Stock_Prices_*.xlsx`, som et **annet** program lager.
Funksjonen er dessuten hash-beskyttet. Ingen kodeendring her kan skaffe ferske
kurser — bare det som produserer den filen kan det.

**Den skjulte andreeffekten.** `portfolio_blend` godtar bare en månedsslutt hvis
siste observasjon er innenfor fem børsdager. Fra 2026-08-19 til 2026-08-31 er
åtte børsdager, så august ble forkastet for Sentiment Momentum — i stillhet.

Det betyr at **selv om ledelsessentimentet hadde blitt fikset samme kveld, ville
den felles perioden fortsatt stoppet 2026-07-31.** Rapporten nevnte ikke dette
med ett ord. Du hadde to blokkeringer, ikke én.

**Hva som er gjort.** Kursfila bygges nå av masteren selv (punkt 2 over), så
den normale årsaken til at den er gammel er borte. I tillegg gjøres faktumet
synlig, og det blir mulig å oppdage på to sekunder i stedet for etter 106
minutter:

- `freshness.py` gir ferskhetsport og månedsslutt-dekning per strategi.
- `portfolio_blend.py` returnerer nå hvilke månedsslutter som ble forkastet og
  hvorfor, navngir strategien som *binder* den felles perioden, og sier det i
  feilmeldingen når for få måneder er igjen.
- `preflight_data.py` sjekker alle fire strategier og deres oppstrømsfiler før
  en lang kjøring starter.

---

## Slik tar du det i bruk

```text
python 2026-09-18/apply_patch.py          # patcher de tre filene i roten
python 2026-09-18/preflight_data.py       # hva blokkerer akkurat nå?
```

`apply_patch.py` er nøyaktig, idempotent og reversibel: den nekter å kjøre hvis
originalblokken ikke finnes ordrett, verifiserer at filen fortsatt parser og at
de beskyttede hashene er uendret før den lagrer, og legger originalen i
`2026-09-18/backup/`. `--revert` gir byte-identisk fil tilbake. `--check`
rapporterer status uten å endre noe.

Deretter er `RUN_ALL.cmd` nok: masteren bygger nå grunnlagsfilene selv før den
kjører analysene. Første kjøring tar lengre tid, fordi kursene faktisk hentes.

Vil du gjøre det stegvis:

1. `RUN_ALL.cmd --tving-datahent` — bygger alle tre grunnlagsfilene på nytt.
2. `python 2026-09-18/preflight_data.py` — skal si OK.

Kjører du bare enkeltstrategier, husk at Step4 bygges av artikkelscorene:
`run_strategy.py --strategy management` må ha kjørt skrapingen først.

---

## Hvor koden ligger

Ny kode ligger i denne mappen. Endringer i filer som allerede fantes gjøres
**på plass i roten**, gjennom `apply_patch.py`:

| Fil | Hvor | Hvorfor |
|---|---|---|
| `price_repair.py`, `freshness.py`, `data_acquisition.py`, `preflight_data.py` | `2026-09-18/` | ny kode, ingen konflikt |
| `master.py` | roten, patchet | det er inngangspunktet `RUN_ALL.cmd` kaller |
| `Only_260820.py` | roten, patchet | prisvakten ligger inne i `SentimentHendelseLab` |
| `portfolio_blend.py` | roten, patchet | se under |

`portfolio_blend.py` lå først som en **kopi** i denne mappen. Det var feil: to
filer med samme modulnavn betyr at hvilken versjon du får avhenger av
importrekkefølgen — og `_fikspakke()` legger denne mappen først i `sys.path`
først når datahentingen kjører. Med `--ingen-datahent` fikk du rotversjonen,
uten den fikk du kopien. Samme kommando, to kodeveier. Kopien er slettet, og
endringene er patchet inn i rotfila som alt annet.

---

## Hva som er verifisert, og hva som ikke er det

**Verifisert her, kjørbart uten pandas eller nett:**

- 58 tester i `tests/` passerer.
- Repoets egne `test_portfolio_blend` (15), `test_insider_selection` (16),
  `test_capital_mail` (3) og `test_master` (24) passerer uendret — også mot den
  patchede `portfolio_blend.py` i roten.
- De beskyttede hashene til `PBROE_All3` og `SentimentMomentumV31` er uendret
  etter patchen, sjekket med repoets egen hash-logikk.
- `Only_260820.py` parser, og diffen er 30 linjer inn / 5 ut. CRLF er bevart —
  filen har blandede linjeskift, og patcheren matcher konvensjonen lokalt der
  blokken står.
- `apply_patch.py --revert` gir byte-identiske filer (tom `git diff`).
- `master.py` parser, CRLF bevart, og de nye funksjonene er røykttestet med
  `build_all` mocket: henting som feiler gir ikke fatal kjøring, mens Step4 som
  feiler stopper analysen.

**Ikke verifisert — og det kan ikke verifiseres i dette miljøet:**

- `repair_price_frames` er pandas-adapteren. Beslutningslogikken under den er
  testet i detalj, men selve adapteren er ikke kjørt: pandas og numpy er ikke
  installert her, og det finnes ingen `ExcelData`- eller `data`-mappe.
- **Ingen av de tre grunnlagsfilene er faktisk skrevet.** Radbyggingen er testet
  rad for rad, men `write_workbook`, `read_nlp_detail`, `ensure_stock_list` og
  `ensure_prices` krever pandas, yfinance og nettilgang. At skjemaene stemmer er
  lest ut av koden som leser dem (`load_tickers`, `DataLoader.load_all`,
  `PriceBook`), ikke bekreftet mot en ekte fil — det finnes ingen original i
  repoet å sammenligne med.
- `Sentiment_Change` er utledet av hva strategien sier den handler på
  («kjøper på endringen fra forrige rapport»). Det originale programmet finnes
  ikke her, så skalaen kan avvike fra den SentMom opprinnelig ble kalibrert på.
  Første kjøring bør sammenlignes mot den gamle `Step4`-fila før tallene brukes.
- Ingen ekte kursfil er rettet. Om alle åtte flaggede tickere faktisk *er*
  tierpotens-artefakter vet vi først når patchen kjøres mot ekte nedlastede
  kurser. BSP.OL er bekreftet fra tallene i `VALIDATION.md`; de sju andre er
  ikke dokumentert noe sted i repoet.
- Hele masterkjøringen, Euronext-skrapingen, Yahoo-nedlastingen og SMTP er ikke
  kjørt.

**Kjente feil som fantes fra før og ikke er rørt:** `test_corrections` (2) og
`test_pipeline` (1) feiler likt med og uten patchen — manglende pandas, og at
testene forventer å ligge i en `tests/`-undermappe (`parents[1]`), slik README i
roten beskriver. Samme grunn til at `master.py` leter etter
`mail/mail_strategier.py` i en `mail/`-mappe som ikke finnes i dette flate
opplastede repoet.

---

## Filer

| Fil | Hva den gjør |
|---|---|
| `data_acquisition.py` | Bygger de tre grunnlagsfilene. Radlogikk i ren Python. |
| `patches.json` | Selve redigeringene, én post per blokk — lesbare uten å lese patcheren. |
| `price_repair.py` | Klassifiserer og retter tierpotens-artefakter. Ren Python. |
| `freshness.py` | Ferskhetsport og månedsslutt-dekning. Ren Python. |
| `apply_patch.py` | Patcher `Only_260820.py`, `master.py` og `portfolio_blend.py` (12 blokker). Verifisert, idempotent, reversibel. |
| `preflight_data.py` | Sjekker alle fire strategier og oppstrømsfiler før en lang kjøring. |
| `tests/` | 58 tester, kjører uten pandas og uten nett. |

```text
python -m unittest discover -s 2026-09-18/tests -t 2026-09-18/tests
```
