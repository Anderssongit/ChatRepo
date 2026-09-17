# Fire strategier — 17. september 2026

Denne utgaven fordeler **25 % kapital til hver strategi**, justerer vektene ved månedsslutt og sender én samlet mail når analysene er ferdige. Mailen forklarer kjøp, salg, posisjonsstørrelse og variantvalg. PB-ROE og Sentiment Momentum sine beregnings- og hentefunksjoner er uendret.

## Start

1. Pakk ut hele mappen. Behold undermappen `mail` og alle Python-filene sammen. Legg `mail_passord.txt` ved siden av `master.py`. Eksisterende mailinnstillinger og legitimasjon i kildekoden er beholdt.
2. Installer Python 3.12 med Python Launcher. Kjør `SETUP.cmd` én gang. Dette installerer pakkene og Chromium. Språkmodellen lastes ned når den først trengs.
3. Kopier eksisterende `ExcelData` inn i denne mappen, eller oppgi plasseringen: `RUN_ALL.cmd --excel-dir "D:\DinMappe\ExcelData"`. På den opprinnelige PC-en kan eksisterende ExcelData fortsatt finnes automatisk. En lokal ExcelData-mappe har forrang.
4. Kopier eventuelt eksisterende innsidedata som `data` i denne mappen. Kjør `CHECK_SETUP.cmd`, deretter `RUN_ALL.cmd`.

Normal kjøring oppdaterer analysene og sender mail etter beregningen. Nedlasting, teksttolking og 384 varianter av ledelsessentiment kan ta tid. En mislykket del gir en tydelig ufullstendig rapport med tilgjengelige delresultater. Mislykket maillevering gir en feilkode og beholder HTML-kopien lokalt.

Pakken skriver normalt innsidedata og masterrapporter i sin egen `data`-mappe og strategiresultater i valgt ExcelData. På en annen maskin trengs også dataene, Python-pakkene, nettforbindelse og gyldig mailtilgang. ZIP-filen inneholder ikke passordfilen eller datamappene. De gamle kodefilene er ikke endret.

## Eksisterende dataflyt

For å bevare de to fungerende strategiene må deres eksisterende dataflyt fortsatt levere følgende under ExcelData før masteren kjøres:

- `Data_BT/AllTickers_OSEBX_TW_260428.xlsx`
- `DataNLP/Step4_Sentiment_Changes_*.xlsx`
- `Data_BT1/FinancialData/Stock_Prices_*.xlsx`

Masteren kontrollerer at filene finnes. Den erstatter ikke den separate produsenten av de to siste filene. Behold planen som lager dem først. `protected_strategy_hashes.json` og testene bekrefter at `PBROE_All3` og `SentimentMomentumV31` har uendrede funksjonskropper; faste mappeplasseringer flyttes ved kjøring når det er nødvendig.

## Samlet portefølje

Den gamle masteren blandet aksjescorer og laget en ny aksjeportefølje. Det var ikke fire delporteføljer med 25 % kapital hver. Den nye kombinerer de fire eksporterte verdikurvene over samme periode. Hver måneds avkastning er gjennomsnittet av de fire månedsavkastningene; månedene forrentes etter hverandre. Kontanter beholdes i den strategien som holder dem. CAGR beregnes fra den samlede kurven, ikke som gjennomsnitt av CAGR-er fra forskjellige perioder.

PB-ROE eksporterer månedlige verdier. Samlet portefølje bruker derfor fullførte månedsslutter og månedlig rebalansering. Fremtidsdaterte og ufullstendige sluttmåneder utelates. Manglende måneder fylles ikke kunstig. Perioden begynner tidligst etter treningen som valgte variantene. Risiko måles på månedspunkter og kan overse fall inne i måneden. Den historiske kapitalfordelingen merkes med sluttdato; enkeltstrategiene viser sine egne siste beholdninger.

## Ledelsessentiment

En feil brukte kursendringen to ganger ved verdsetting av åpne posisjoner. Nå er verdien antall aksjer × siste observerte kurs. Salg utløser ikke et kunstig hopp tilbake i verdikurven. Korte kurshull beholder siste observerte verdi; lengre hull blokkerer publisering. Kurshentingen ber Yahoo om reparerte priser og kontrollerer fortsatt ekstreme prishopp. Den gjetter ikke en korreksjon av mistenkelige kurser.

**Kjør analysen på nytt:** gamle ledelsessentimentfiler mangler den nye regnskapsversjonen og kan ikke brukes til ny samlet avkastning. Lagrede BSP.OL-kurser hadde også et separat, nøyaktig 100-gangers prishopp. Dersom ny nedlasting ikke løser det, viser `management_price_issues.csv` hvilket kursgrunnlag som må avklares. Kjøringen gir da en ufullstendig rapport fremfor å presentere kursfeilen som avkastning.

Automatikken sammenligner fortsatt de eksisterende 384 inngangs-/utgangskombinasjonene og velger høyest kvalifisert trenings-CAGR, med krav til historikk og handler. Senere resultater brukes ikke til dette valget. Mailen viser faktisk valgt inngangs- og salgsregel, konsistente risikotall og samlet beholdning for aksjer med flere innganger.

## Innsidehandel

Mailen viser de tre høyeste historiske CAGR-ene, presise regler for hver og varianten som brukes videre. Automatisk valg krever minst 252 treningsobservasjoner, 20 nye innganger og fem forskjellige aksjer. Kvalifiserte varianter må ha positiv trenings-CAGR med 0,15 % kostnad per kjøp/salg. Blant dem velges høyest CAGR i den svakeste treningshalvdelen med 0,80 % per kjøp/salg; lavere omsetning avgjør ved likhet. Hvis ingen kvalifiserer, brukes daglig baseline med tydelig forbehold. Topp-tre-rangeringen over hele historikken bestemmer ikke valget.

På siste lagrede datagrunnlag ble scorevektet valgt. Alle variantene tapte under den høye kostnadsantakelsen. Dette opplyses i mailen og dokumenterer ingen bevist MOAT. Neste normale kjøring kan velge annerledes hvis datagrunnlaget endres. De originale kostnadene beholdes i verdikurvene som kombineres; kostnadsstressen vises separat. Ekstra kapitaloverføringer mellom strategiene har ingen modellerte kostnader.

Gjennomsnittlig inngangskurs ved påfyll er rettet, slik at beholdningen viser faktisk avkastning. Tidligere rettelser for ufullstendige nedlastinger, kronologiske signaler og faktisk sluttbeholdning er beholdt.

## Kjøring og filer

```text
RUN_ALL.cmd
RUN_ALL.cmd --mail-kladd
RUN_ALL.cmd --ingen-nlp-hent
RUN_ALL.cmd --ikke-kjor --mail-kladd
RUN_ALL.cmd --bare-mail
```

`--mail-kladd` lagrer mail uten å sende. `--ingen-nlp-hent` bruker lagrede ledelsesartikler, men gjennomfører den øvrige analysen. `--ikke-kjor` beregner samlet portefølje fra gyldige lagrede resultater. `--bare-mail` bruker siste fullførte kapitalberegning når kildefilene fortsatt stemmer. Gamle beregninger basert på scoreblanding avvises.

Standard treningsslutt er `2025-06-30`. `--selection-cutoff YYYY-MM-DD` endrer den; fastsett datoen før du vurderer senere resultater. `--innside-valg daglig` og `--sent-valg "S1|F21"` overstyrer variantvalg manuelt og merkes som overstyring.

Rapport og kapitalhistorikk: `data/7_master`. Innsidevalg, kostnadstester og regler: `data/6_backtest/selected_variant.json`, `insider_selection.json` og `variant_comparison.csv`. Ledelsessentimentets sammenligning og kursdiagnostikk: `ExcelData/StrategyResults_v5_Sentiment_Exit`.

Enkeltstrategier kan kjøres fra samme mappe:

```text
.venv\Scripts\python.exe run_strategy.py --strategy management
.venv\Scripts\python.exe run_strategy.py --strategy insider
.venv\Scripts\python.exe run_strategy.py --strategy pbroe
.venv\Scripts\python.exe run_strategy.py --strategy sentmom
```

Bruk `RUN_ALL.cmd` for samlet mail. Innsidepipelinen kan sende sin egen rapport; de øvrige enkeltinngangene kjører analysefunksjonene. `Only_260820.py` starter masterløpet når den kjøres direkte, men starter ingenting ved import.

Masterens feilkoder: `0` fullført, `2` ufullstendig beregning, `3` mislykket maillevering. Se `VALIDATION.md` for tester og begrensninger.
