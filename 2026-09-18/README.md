# Fire strategier — rettet utgave, 2026-09-18

Dette er en **komplett, frittstående pakke**. Alt som trengs ligger her: alle
kodefilene, testene og oppsettskriptene. Du kan kjøre den herfra, eller flytte
hele mappen et annet sted.

Ingenting i repo-roten er endret. `ENDRINGER.diff` viser nøyaktig hva som
skiller denne pakken fra koden som lå der fra før:

| Fil | Endring |
|---|---|
| `master.py` | +116 / −2 |
| `Only_260820.py` | +30 / −5 |
| `portfolio_blend.py` | +68 / −7 |

Alt annet er kopiert uendret. `PBROE_All3` og `SentimentMomentumV31` har samme
SHA-256 som før — verifisert av testene.

## Kom i gang

```text
SETUP.cmd        én gang: lager .venv her, installerer pakkene og Chromium
CHECK_SETUP.cmd  sjekker at alt er på plass
RUN_ALL.cmd      full kjøring
```

Nye flagg i denne utgaven:

```text
RUN_ALL.cmd --tving-datahent    bygg alle tre grunnlagsfilene på nytt
RUN_ALL.cmd --ingen-datahent    bruk filene som allerede ligger i ExcelData
python preflight_data.py        hva blokkerer akkurat nå?
```

---

## Hva som er rettet

### 1. Ledelsessentiment stoppet på prisvalidering

`kontroller_priser` flagger enhver endring på 4x eller mer mellom to
observasjoner, og `hent_kurser` avbrøt hele kjøringen på hvilken som helst av
dem. Den behandlet to helt ulike ting likt:

| Observasjon | Hva det er | Bevisbart fra dataene? |
|---|---|---|
| BSP.OL 0,101440 → 10,144007 (ratio 100,000) | provider endret enhet | **ja** |
| ratio 4,7 eller 0,21 | ekte kursbevegelse, eller ukjent | nei |

Åtte tickere ble flagget, og alle åtte stoppet analysen — også de som ikke
hadde et eneste signal.

`price_repair.py` skiller dem. Et sprang innenfor 0,5 % av en tierpotens
behandles som et denominasjonsavvik og rettes; alt annet blokkerer fortsatt
publisering, akkurat som før.

Rettingen går **bakover**: segmentet *før* bruddet skaleres opp til å møte
segmentet etter. De nyeste kursene — de åpne posisjoner verdsettes mot —
endres aldri. Hver endring skrives til `management_price_issues.csv` med
faktor, dato og før/etter-kurs.

Egenskapen som gjør dette trygt, og som testes: **ingen daglig avkastning
endres, bortsett fra den ene som er artefakten.** En omskalering av et helt
segment er en enhetskonvertering, ikke en kursjustering.

Ingenting klippes, interpoleres eller gjettes. Klarer ikke regelen å bevise at
et sprang er et enhetsavvik, stopper kjøringen som før — men nå med en liste
over hvilke tickere som faktisk må sjekkes manuelt.

### 2. Masteren hentet aldri ned sitt eget datagrunnlag

`master.py` *kontrollerte* at tre filer fantes og avbrøt hvis ikke. Ingenting i
repoet lagde dem:

| Fil | Leses av |
|---|---|
| `Data_BT/AllTickers_OSEBX_TW_*.xlsx` | `PBROE_All3.load_tickers()` |
| `Data_BT1/FinancialData/Stock_Prices_*.xlsx` | `SentimentMomentumV31` |
| `DataNLP/Step4_Sentiment_Changes_*.xlsx` | `SentimentMomentumV31` |

De kom fra et annet program. Ingen hadde kjørt det siden 2026-08-19. Det er
hele forklaringen på at Sentiment Momentum backtestet måned gamle kurser og
likevel ble rapportert `OK`: filen var ikke gammel fordi noe feilet, den var
gammel fordi ingenting oppdaterte den.

**Alt som trengs lastes allerede ned av pakken:**

| Byggestein | Hentes av |
|---|---|
| Euronext-aksjelista | `innsidehandel_pipeline.sikre_aksjeliste` |
| Daglige kurser (yfinance) | `innsidehandel_pipeline.steg4_kurser` |
| FinBERT-score per artikkel | `SentimentManagement` → `NLP_Sentiment_Detail_*.xlsx` |

De tre filene er altså omforminger av data kjøringen allerede har.
`data_acquisition.py` gjør omformingen, og masteren kaller den selv.

Skjemaene er lest ut av koden som leser dem:

- **Tickerlista** — `Company` er den bare tickeren, fordi PB-ROE bygger
  `tradingview.com/symbols/OSL-<Company>/` av den. Skrives med `index=True`,
  fordi `load_tickers()` dropper første kolonne før den leser `Company`.
- **Kursfila** — lang form med `Date`, `Company`, `Ticker`, `Close`. `Company`
  hentes fra samme selskapsliste som Step4, slik at `_map_tickers` treffer.
- **Step4** — `Sentiment_Change` er bevegelsen fra selskapets **forrige**
  rapport, som er nøyaktig det strategien handler på.

**Rekkefølgen er viktig.** Step4 bygges av scorene skrapingen nettopp skrev, så
den må ligge mellom skrapingen og `SentimentMomentumV31`. Hentingen går derfor
i to trinn: tickerliste og kurser *før* analysene, Step4 inne i `kjor_alle`
rett etter skrapingen.

**Henting velter aldri en kjøring alene.** Feiler den mens filene allerede
ligger der og er ferske, er ingen skade skjedd. Portene som avgjør er
`protected_input_errors` (fil mangler) og nye `foreldede_grunnlagsdata` (fil
finnes, men er for gammel: kurser 7 dager, Step4 14, tickerliste 90). Unntaket
er Step4: feiler den, stopper analysen, for uten fersk Step4 leser SentMom den
forrige.

### 3. Den skjulte andreeffekten av gamle kurser

`portfolio_blend` godtar bare en månedsslutt hvis siste observasjon er innenfor
fem børsdager. Fra 2026-08-19 til 2026-08-31 er åtte børsdager, så august ble
forkastet for Sentiment Momentum — i stillhet.

Det betyr at **selv om ledelsessentimentet hadde blitt fikset samme kveld,
ville den felles perioden fortsatt stoppet 2026-07-31.** Rapporten nevnte det
ikke med ett ord. Det var to blokkeringer, ikke én.

`_monthly_observations` returnerer nå hvilke månedsslutter som ble forkastet og
hvorfor, `build_capital_portfolio` navngir strategien som *binder* perioden, og
`preflight_data.py` svarer på to sekunder i stedet for etter 106 minutter.

### 4. To pakkefeil som fulgte med

- `master.py` leter etter `mail/mail_strategier.py`. I det flate repoet fantes
  ikke den mappen, så strategikortene falt stille ut av mailen. Her ligger fila
  der masteren faktisk leter.
- Testene forventer å ligge i en `tests/`-undermappe (`parents[1]`). I det
  flate repoet gjorde de ikke det, og hash-testen feilet på en filsti som ikke
  fantes. Her ligger de riktig, og testen kjører.

---

## Hva som er verifisert

Kjørt i et miljø **uten** pandas, numpy og nettilgang:

- **186 tester** kjører, 2 feiler — begge fordi pandas/numpy ikke er installert
  her, ingen av dem på logikk.
- `PBROE_All3` og `SentimentMomentumV31` har uendret SHA-256.
- Repo-roten er byte-identisk med originalen (`git diff 7c21574` er tom).
- Pakken importerer og kjører frittstående: `master.py --help` viser de nye
  flaggene, og `data_acquisition`, `price_repair` og `freshness` løses ved
  siden av masteren.
- De nye masterfunksjonene er røyktestet med `build_all` mocket: henting som
  feiler gir ikke fatal kjøring, mens Step4 som feiler stopper analysen.

```text
python -m unittest discover -s tests -t tests
```

## Hva som IKKE er verifisert

- **Ingen av de tre grunnlagsfilene er faktisk skrevet.** Radbyggingen er
  testet rad for rad, men `write_workbook`, `read_nlp_detail`,
  `ensure_stock_list` og `ensure_prices` krever pandas, yfinance og nett.
  Skjemaene er lest ut av koden som leser dem, ikke sammenlignet med en ekte
  fil — det finnes ingen original i repoet å sammenligne med.
- **Ingen ekte kursfil er rettet.** Om alle åtte flaggede tickere faktisk *er*
  tierpotens-artefakter vet vi først ved kjøring mot ekte nedlastede kurser.
  Bare BSP.OL er dokumentert som en.
- **`Sentiment_Change` er utledet**, ikke gjenskapt, fra det strategien selv
  sier den handler på. Det originale programmet finnes ikke her, så skalaen kan
  avvike fra den SentMom opprinnelig ble kalibrert på. Sammenlign første
  kjøring mot den gamle Step4-fila før tallene brukes.
- Hele masterkjøringen, Euronext-skrapingen, Yahoo-nedlastingen og SMTP er ikke
  kjørt.

---

## Nye filer i denne utgaven

| Fil | Hva den gjør |
|---|---|
| `data_acquisition.py` | Bygger de tre grunnlagsfilene. Radlogikk i ren Python. |
| `price_repair.py` | Klassifiserer og retter tierpotens-artefakter. Ren Python. |
| `freshness.py` | Ferskhetsport og månedsslutt-dekning. Ren Python. |
| `preflight_data.py` | Sjekker alle fire strategier og oppstrømsfiler før en lang kjøring. |
| `ENDRINGER.diff` | Nøyaktig hva som skiller pakken fra originalkoden. |
| `tests/test_price_repair.py` m.fl. | 67 nye tester, i tillegg til repoets egne. |

Alt annet er repoets egne filer, kopiert uendret. Se `VALIDATION.md` for den
opprinnelige valideringen.
