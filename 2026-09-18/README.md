# Rettelse 2026-09-18 — de to feilende strategiene

Denne mappen retter de to problemene i kjøringen 2026-09-18: ledelsessentimentet
som stoppet på prisvalidering, og Sentiment Momentum som rapporterte `OK` mens
den kjørte på måned gamle kurser.

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

## 2. Sentiment Momentum — KAN IKKE FIKSES MED KODE

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

**Hva som er gjort.** Faktumet gjøres synlig, og det blir mulig å oppdage det på
to sekunder i stedet for etter 106 minutter:

- `freshness.py` gir ferskhetsport og månedsslutt-dekning per strategi.
- `portfolio_blend.py` returnerer nå hvilke månedsslutter som ble forkastet og
  hvorfor, navngir strategien som *binder* den felles perioden, og sier det i
  feilmeldingen når for få måneder er igjen.
- `preflight_data.py` sjekker alle fire strategier og deres oppstrømsfiler før
  en lang kjøring starter.

---

## Slik tar du det i bruk

```text
python 2026-09-18/apply_patch.py          # patcher Only_260820.py
python 2026-09-18/preflight_data.py       # hva blokkerer akkurat nå?
```

`apply_patch.py` er nøyaktig, idempotent og reversibel: den nekter å kjøre hvis
originalblokken ikke finnes ordrett, verifiserer at filen fortsatt parser og at
de beskyttede hashene er uendret før den lagrer, og legger originalen i
`2026-09-18/backup/`. `--revert` gir byte-identisk fil tilbake. `--check`
rapporterer status uten å endre noe.

Deretter, i denne rekkefølgen:

1. **Oppdater oppstrømsfilene** som preflight flagger — særlig
   `Stock_Prices_*.xlsx` og `Step4_Sentiment_Changes_*.xlsx`. Uten dette forblir
   Sentiment Momentum gammel uansett hva annet du gjør.
2. `python run_strategy.py --strategy sentmom`
3. `python run_strategy.py --strategy management` — prisvakten retter nå
   enhetsavvik og blokkerer resten.
4. `python 2026-09-18/preflight_data.py` — skal si OK.
5. `RUN_ALL.cmd`

Bruk `portfolio_blend.py` fra denne mappen ved å legge den først i `PYTHONPATH`,
eller kopier den over rotversjonen når du er fornøyd. Den består alle 15
eksisterende tester i `test_portfolio_blend.py` uendret.

---

## Hva som er verifisert, og hva som ikke er det

**Verifisert her, kjørbart uten pandas eller nett:**

- 38 tester i `tests/` passerer.
- Repoets egne `test_portfolio_blend` (15), `test_insider_selection` (16),
  `test_capital_mail` (3) og `test_master` (24) passerer uendret.
- De beskyttede hashene til `PBROE_All3` og `SentimentMomentumV31` er uendret
  etter patchen, sjekket med repoets egen hash-logikk.
- `Only_260820.py` parser, og diffen er 30 linjer inn / 5 ut. CRLF er bevart —
  filen har blandede linjeskift, og patcheren matcher konvensjonen lokalt der
  blokken står.
- `apply_patch.py --revert` gir en byte-identisk fil (tom `git diff`).

**Ikke verifisert — og det kan ikke verifiseres i dette miljøet:**

- `repair_price_frames` er pandas-adapteren. Beslutningslogikken under den er
  testet i detalj, men selve adapteren er ikke kjørt: pandas og numpy er ikke
  installert her, og det finnes ingen `ExcelData`- eller `data`-mappe.
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
| `price_repair.py` | Klassifiserer og retter tierpotens-artefakter. Ren Python. |
| `freshness.py` | Ferskhetsport og månedsslutt-dekning. Ren Python. |
| `portfolio_blend.py` | Som roten, men forkastede månedsslutter rapporteres og bindende strategi navngis. |
| `apply_patch.py` | Patcher `Only_260820.py`. Verifisert, idempotent, reversibel. |
| `preflight_data.py` | Sjekker alle fire strategier og oppstrømsfiler før en lang kjøring. |
| `tests/` | 38 tester, kjører uten pandas og uten nett. |

```text
python -m unittest discover -s 2026-09-18/tests -t 2026-09-18/tests
```
