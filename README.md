# Fire strategier — korrigert 20. september 2026

Automatisk datanedlasting, **simulerte handler** og én samlet e-post.
PB-ROE/Momentum, ledelsessentiment, Sentiment Momentum og innsidehandel får
**25 % kapital hver**, med månedlig rebalansering. Ingen meglerordre sendes.
Alle aktive standardberegninger bruker **0 % kurtasje, spread og slippage**.

## Start fra en ny kopi

1. Installer Python 3.12 med Python Launcher på Windows.
2. Kjør `SETUP.cmd`: Python-pakker, Chromium og NLTK-data installeres.
   FinBERT-modellen lastes ned ved første sentimentkjøring.
3. Sett `AKSJE_MAIL_USER`, `AKSJE_MAIL_TO` og `AKSJE_MAIL_APP_PASSWORD`, eller
   legg app-passordet i `mail_passord.txt` ved siden av `master.py`.
   Eksisterende avsender/mottaker brukes hvis miljøvariablene ikke er satt.
4. Kjør `CHECK_SETUP.cmd`, så `RUN_ALL.cmd --mail-kladd` for lokal forhåndsvisning.
   `RUN_ALL.cmd` beregner og sender samlet e-post.

En eksisterende ExcelData-mappe er **ikke nødvendig for å starte nedlastingen**.
Manglende inputfiler bygges automatisk. Historiske arkiver kan beholdes i
`ExcelData` og `data`, eller velges med `--excel-dir` og `--mappe`.
ExcelData velges ikke automatisk fra gamle Desktop-mapper.

På macOS/Linux: opprett og aktiver et Python 3.12-miljø, installer
`requirements.txt`, kjør `python -m playwright install chromium`,
`python -m nltk.downloader punkt punkt_tab`, så `python master.py --mail-kladd`.

## Data som hentes

| Strategi | Kilder |
|---|---|
| PB-ROE/Momentum | Euronext-aksjeliste, TradingView-statistikk og observerte finansielle versjoner, Yahoo-kurser og referanseindeks. |
| Ledelsessentiment | Finansielle Euronext-meldinger, tilgjengelig artikkel/PDF-tekst, FinBERT og Yahoo-kurser. |
| Sentiment Momentum | Samme artikkelarkiv, avledede sentimentendringer og justert Yahoo-kurshistorikk. |
| Innsidehandel | Euronext-meldinger, tekstuttrekk/klassifisering, Yahoo-kurser, volum og referanse. |

Normal kjøring forsøker nye nedlastinger selv om gamle filer finnes.
Sentimentendringer bygges **etter** artikkelhentingen. Selskapsidentiteter bruker
samme ticker i tickerlisten, sentimentfilen og kursfilen. `Close` i den felles
kursfilen er justert kurs; opprinnelig kurs beholdes som `RawClose`.
Inneværende ufullstendige handelsdag tas ikke med i denne filen.

«Alle data» betyr tilgjengelige data for det konfigurerte universet og
historikkvinduet. Kildene kan mangle eldre meldinger, avnoterte selskaper eller
en ticker. Mangler og eksplisitte artikkel-/pagineringgrenser skal rapporteres.
Stor førstegangsnedlasting og språkmodellkjøring kan ta flere timer.

## Først i e-posten: nedlastingsstatus

Hver strategi får en egen rad helt først, også når resten feiler:

- **JA — lastet ned og kontrollert:** nødvendige nedlastinger er bekreftet.
- **DELVIS:** minst én kilde er mangelfull eller bare delvis oppdatert.
- **NEI — lagrede data:** gjenbruk; ingen ny nedlasting påstås.
- **NEI — feilet / ikke bekreftet:** datagrunnlaget kunne ikke bekreftes.

Tabellen viser kilder, dekning, siste observerte dato når kjent, og forklaringer.
Detaljene lagres i `data/7_master/download_status.json`. En ferdig backtest eller
nylig skrevet Excel-fil teller ikke i seg selv som vellykket nedlasting.
Ufullstendige nødvendige data blokkerer en ny samlet avkastningsrapport;
tilgjengelige historiske delresultater merkes.

## Handelsregler og realisme

- De fire strategifamiliene og kapitalfordelingen beholdes. Ledelsessentiment
  sammenligner de eksisterende 384 variantene, innsidehandel de eksisterende fem.
  Kvalifiserte varianter velges på høyest **trenings-CAGR uten handelskostnader**,
  med krav til historikk og handler. Senere resultater brukes bare til evaluering.
  Dette maksimerer det valgte historiske målet, ikke garantert fremtidig profitt.
- Standard treningsslutt er `2025-06-30`. Bruk `--selection-cutoff YYYY-MM-DD`
  bare når datoen er bestemt før senere resultater vurderes.
- Nyheter må være tilgjengelige før handelsdagen. Prisbaserte signaler bruker
  tidligere observerte kurser; handler bruker senere tilgjengelig sluttkurs.
  Stopper har ingen garantert utførelseskurs ved store kursgap.
- PB-ROE bruker finansielle versjoner fra deres faktiske innsamlingsdato.
  Regnskapsperiodens sluttdato beviser ikke når tallene ble publisert.
  En ny installasjon kan mangle nok verifiserbar PB-ROE-historikk til en samlet
  backtest. Programmet lager ikke historiske publiseringsdatoer eller profitt.
- PB-ROE bruker fullførte måneder med faktiske observasjonsdatoer, håndhever
  vekttaket, selger før kjøp finansieres, og holder kontanter uten kvalifiserte aksjer.
- Manglende kurser og ekstreme sprang krever kontroll. Historikk omskaleres
  ikke bare fordi et sprang er nær 10 eller 100 ganger.
- Samlet kurve bruker felles fullførte månedsslutter etter variantvalg.
  Månedsmålt risiko kan overse tap inne i måneden. Hver beholdning har egen dato.
- Null handelskostnader er en modellforenkling. Historisk selskapsutvalg,
  likviditet, revisjoner, utførelse og datadekning kan endre faktisk avkastning.

## Kommandoer og filer

```text
RUN_ALL.cmd
RUN_ALL.cmd --mail-kladd
RUN_ALL.cmd --excel-dir "D:\ExcelData" --mappe "D:\Innsidedata"
RUN_ALL.cmd --ikke-kjor --mail-kladd
RUN_ALL.cmd --bare-mail --mail-kladd
```

`--ingen-nlp-hent` og `--ingen-datahent` er eksplisitte forskningsvalg for
gjenbruk; dette merkes og kan gi ufullstendig status. `--ikke-kjor` og
`--bare-mail` krever resultater validert med denne utgavens utførelsespolicy.
Eldre resultater må kjøres på nytt. `--innside-valg` og `--sent-valg` er
manuelle overstyringer og merkes som det.

`master.py`, `RUN_ALL.cmd` og `2026-09-18/RUN.cmd` starter samme implementasjon.
Importpatcher brukes ikke. De gamle patchfilene er historisk referanse.

- `data/7_master/master_mail_*.html`: lokal e-postkopi.
- `data/7_master/download_status.json`: denne kjøringens datakontroller.
- `data/7_master/completed_run.json`: siste komplette porteføljerapport.
- `data/7_master/validated_outputs.json`: policy og kildefiler for gjenbruk.
- `data/7_master/samlet_*.csv`: kapitalhistorikk og sammenligning.
- `data/6_backtest/selected_variant.json`: innsidevalg og treningsgrunnlag.
- `ExcelData/StrategyResults_v5_Sentiment_Exit`: variant- og kursdiagnostikk.

Masterens returkoder: **0** fullført, **2** ufullstendig, **3** e-postfeil.
Lokal HTML beholdes ved leveringsfeil.

## Tester og legitimasjon

```text
python -m pip install -r requirements-test.txt
python -m playwright install chromium
python run_tests.py
```

Testkjøreren blokkerer eksterne Python-socketforbindelser og ekte SMTP.
Nettlesertesten bruker lokale testsider. Se `VALIDATION.md`.
Gamle credential-lignende kommentarer er fjernet. Gyldige nøkler derfra må
tilbakekalles/roteres, siden tidligere Git-historikk fortsatt kan inneholde dem.
Passord og genererte data er utelukket fra nye commits med `.gitignore`.
