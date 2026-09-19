"""Mail for four actual capital allocations and the insider comparison."""
from __future__ import annotations

from datetime import datetime
import math
import innsidehandel_pipeline as ip


def _number(value, digits=1, suffix=""):
    try:
        n = float(value)
        if not math.isfinite(n):
            return "—"
        return f"{n:,.{digits}f}{suffix}".replace(",", " ")
    except (TypeError, ValueError):
        return "—"


def _table(headers, rows):
    return ('<table><tr>' + ''.join('<th>'+ip.trygg(h)+'</th>' for h in headers)
            + '</tr>' + ''.join('<tr>'+''.join('<td>'+str(c)+'</td>' for c in row)
                               + '</tr>' for row in rows) + '</table>')


def _rules(rows):
    if isinstance(rows, dict):
        rows = rows.items()
    return _table(['Regel', 'Hva programmet gjør'],
                  [[ip.trygg(k), ip.trygg(v)] for k, v in rows])


def _insider_section(opp, insider):
    if not insider:
        return '<div class="kort"><h2>Innsidehandel</h2><p>Resultater mangler.</p></div>'
    from insider_selection import variant_rules
    selected = insider['maal'].get('Strategi', '')
    selection = insider['maal'].get('Selection', {})
    def historical_cagr(row):
        value = ip.tolk_maskin(row.get('CAGR_Pst'))
        return value if value is not None else -1e9
    variants = sorted(insider.get('varianter', []),key=lambda r: -historical_cagr(r))
    top3 = variants[:3]
    # The selected robust variant need not be one of the three gross winners.
    displayed = top3 + [r for r in variants[3:] if r.get('Strategi') == selected]
    rank = {r.get('Strategi'): i+1 for i, r in enumerate(top3)}
    headline = _table(
        ['Plass', 'Variant', 'CAGR hele historikken', 'Sharpe', 'Maks. fall', 'Valgt videre'],
        [[rank.get(r.get('Strategi'), '—'), ip.trygg(r.get('Strategi')),
          _number(r.get('CAGR_Pst'),1,' %'), _number(r.get('Sharpe'),2),
          _number(r.get('MaxDD_Pst'),1,' %'), 'Ja' if r.get('Strategi')==selected else '']
         for r in displayed])
    compared = {r.get('Variant') or r.get('Strategi'): r
                for r in selection.get('top3', [])}
    compared[selected] = selection
    cost_table = _table(
        ['Variant','Trening: 0,15 % per side','Senere: 0,15 % per side',
         'Trening: 0,80 % per side','Svakeste treningshalvdel: 0,80 %'],
        [[ip.trygg(r.get('Strategi')),
          _number(compared.get(r.get('Strategi'),{}).get('Train_Moderate_CAGR_Pst'),1,' %'),
          _number(compared.get(r.get('Strategi'),{}).get('Test_Moderate_CAGR_Pst'),1,' %'),
          _number(compared.get(r.get('Strategi'),{}).get('Train_Stress_CAGR_Pst'),1,' %'),
          _number(compared.get(r.get('Strategi'),{}).get('Train_Stress_Worst_Half_CAGR_Pst'),1,' %')]
         for r in displayed])
    detail = ''
    for r in displayed:
        name = r.get('Strategi', '')
        label = f"{rank[name]}. " if name in rank else 'Valgt utenfor topp tre: '
        detail += '<h3>'+ip.trygg(label+name)+'</h3>' + _rules(variant_rules(name, opp))
    why = selection.get('Reason') or selection.get('rationale') or 'Variantvalg ikke dokumentert.'
    heldout = _number(selection.get('Test_CAGR_Pst'),1,' %')
    training = _number(selection.get('Train_CAGR_Pst'),1,' %')
    holdings = insider.get('beholdning', [])
    hold_table = _table(['Aksje','Kjøpt','Gj.snittlig inngang','Siste kurs','Verdi','Vekt','Avkastning'],
        [[ip.trygg(b.get('Ticker')),ip.trygg(b.get('Inn_Dato')),_number(b.get('Inn_Kurs'),2),
          _number(b.get('Siste_Kurs'),2),_number(b.get('Verdi_NOK'),0),
          _number(b.get('Andel_Pst'),1,' %'),_number(b.get('Avk_Pst'),1,' %')]
         for b in holdings]) if holdings else '<p>Kontanter ved siste beregnede tidspunkt.</p>'
    last = sorted(insider.get('handler',[]),key=lambda x:str(x.get('Dato','')))[-10:][::-1]
    trades = _table(['Dato','Handling','Aksje','Beløp'],
        [[ip.trygg(r.get('Dato')),ip.trygg(r.get('Type')),ip.trygg(r.get('Ticker')),
          _number(r.get('Verdi_NOK'),0)] for r in last])
    date = holdings[0].get('Dato','') if holdings else insider['maal'].get('Periode','')
    return f'''<div class="kort"><h2>Innsidehandel: topp tre og valgt variant</h2>
<p>Rangeringen viser høyest historisk CAGR før den ekstra kostnadstesten.
Valget videre vurderer robusthet i den tidligere treningsperioden.
En høy plassering er ikke dokumentasjon på en varig konkurransefordel («MOAT»).</p>
{headline}<h3>Kostnadstest: CAGR etter modellerte kostnader</h3>
<p>Variantene kjøres på nytt med 0,15 % og 0,80 % kostnad per kjøp eller salg.
Dette er antakelser, ikke observerte utførelseskostnader. Tallene annualiseres etter
kalendertid; hovedtabellen beholder innsidermotorens 252 handelsdager per år.</p>{cost_table}
<h3>Valgt til de 25 % i samlet portefølje: {ip.trygg(selected)}</h3>
<p>{ip.trygg(why)}</p>
<p>Trening til {ip.trygg(selection.get('Selection_Cutoff','—'))}: {training} CAGR.
Senere periode: {heldout} CAGR. Den senere perioden brukes ikke til å velge variant.</p>
{detail}<h3>Beholdning for valgt variant, {ip.trygg(date)}</h3>{hold_table}
<h3>Siste ti handler for valgt variant</h3>{trades}</div>'''


def render_capital_mail(m, run_status, portfolio, sections, insider, errors=()):
    """Portfolio is the calculation result; sections contain individual model cards."""
    problems = list(dict.fromkeys(str(x) for x in errors if x))
    warnings = list((portfolio or {}).get('warnings', []))
    metrics = (portfolio or {}).get('metrics', {})
    if problems:
        status = '<div class="kort"><h2>Beregningen er ufullstendig</h2><ul>' + ''.join(
            '<li>'+ip.trygg(e)+'</li>' for e in problems) + '</ul><p>Tilgjengelige delresultater vises nedenfor med sine egne datoer.</p></div>'
    else:
        status = ''
    if metrics:
        period = metrics.get('Periode','—')
        summary = _table(['Felles periode','Samlet totalavkastning','Samlet CAGR','Sharpe','Maks. fall'],
             [[ip.trygg(period), _number(metrics.get('Total_Pst'),1,' %'),
               _number(metrics.get('CAGR_Pst'),1,' %'),_number(metrics.get('Sharpe'),2),
               _number(metrics.get('MaxDD_Pst'),1,' %')]])
        components = portfolio.get('components',[])
        comparison = _table(['Strategi','Total, samme periode','CAGR, samme periode','Maks. fall'],
             [[ip.trygg(r.get('Strategi') or r.get('name')),
               _number(r.get('Total_Pst'),1,' %'),_number(r.get('CAGR_Pst'),1,' %'),
               _number(r.get('MaxDD_Pst'),1,' %')] for r in components])
        holdings = _table(['Delportefølje','Verdi ved periodens slutt','Kapitalvekt','Målvekt'],
             [[ip.trygg(r.get('Strategi')),_number(r.get('Verdi_NOK'),0),
               _number(r.get('Andel_Pst'),1,' %'),_number(r.get('Target_Pst',25),0,' %')]
              for r in portfolio.get('holdings',[])])
        transfer_names = {'INITIAL_ALLOCATION':'Startfordeling','ALLOCATE':'Tilført','WITHDRAW':'Trukket ut'}
        transfers = _table(['Dato','Delportefølje','Justering','Beløp'],
             [[ip.trygg(r.get('Dato')),ip.trygg(r.get('Strategi')),ip.trygg(transfer_names.get(r.get('Type'),r.get('Type'))),
               _number(r.get('Verdi_NOK'),0)] for r in portfolio.get('trades',[])[-12:][::-1]])
        rebalance = metrics.get('Rebalance', portfolio.get('rebalance','monthly'))
        frequency = {'monthly':'månedlig','daily':'daglig','none':'kun ved start'}.get(rebalance,rebalance)
        main = f'''<div class="kort"><h2>Samlet portefølje: 25 % i hver strategi</h2>{summary}
<p>Hver strategi får en fjerdedel av kapitalen. Vi kombinerer verdiene til de fire
faktiske delporteføljene over samme observerte periode. Ingen ny aksjeliste lages av scorene.</p>
{_rules([
('Kjøp og salg','Hver delportefølje følger sine egne kjøps- og salgsregler, forklart nedenfor.'),
('Kapitalfordeling',f'Kapitalen fordeles likt ved start og justeres {frequency}. Ved månedlig justering får hver del 25 % ved månedsslutt; mellom disse tidspunktene kan vektene drive.'),
('Kontanter','Når en strategi går i kontanter, blir pengene i den strategiens del. De flyttes ikke automatisk til de andre.'),
('Avkastning','Ved månedlig justering er hver måneds samlede avkastning gjennomsnittet av de fire månedsavkastningene. Månedene forrentes deretter etter hverandre. CAGR er beregnet fra denne samlede kurven.'),
('Sammenligning','Bare fullførte måneder med observerte verdier for alle fire brukes. Daglige PB-ROE-verdier blir ikke funnet på. Risiko er derfor målt på månedspunkter og kan undervurdere fall innenfor måneden.'),
('Innsidevalg','De 25 % til innsidehandel følger den dokumenterte robusthetsvurderingen nedenfor, ikke et gjennomsnitt av alle innsidevariantene.')])}
<h3>De fire delene, målt over samme periode</h3>{comparison}
<h3>Kapital ved slutten av den felles perioden</h3>{holdings}
<h3>Siste justeringer mellom strategiene</h3><p>Dette er kapitaloverføringer mellom
delporteføljene. Aksjehandlene står i hver strategis egen rapport.</p>{transfers}</div>'''
    else:
        main = '<div class="kort"><h2>Samlet portefølje: avkastning ikke tilgjengelig</h2><p>En gyldig felles kurve for alle fire strategier er nødvendig. Et manglende resultat erstattes ikke med null avkastning.</p></div>'
    if warnings:
        main += '<div class="kort"><h3>Perioder og datagrunnlag</h3><ul>'+''.join(
            '<li>'+ip.trygg(x)+'</li>' for x in warnings)+'</ul></div>'
    cards = sections.get('kort',{})
    def card(name):
        html = cards.get(name,'')
        return '<div class="strategier">'+html+'</div>' if html else ''
    detail = (card('PB-ROE-Momentum') + _insider_section(m.insider_oppsett(),insider)
              + card('NLP Sentiment — ledelse') + card('Sentiment Momentum v3.1'))
    runs = _table(['Analyse','Status','Minutter','Merknad'],
                 [[ip.trygg(r.get('Analyse')),ip.trygg(r.get('Status')),
                   _number(r.get('Minutter'),1),ip.trygg(r.get('Feil'))] for r in run_status])
    return f'''<!doctype html><html lang="nb"><head><meta charset="utf-8"><style>
{ip.EPOST_STIL}{sections.get('stil','')} table td{{vertical-align:top;}}</style></head>
<body><div class="beholder"><div class="topp"><h1>Fire strategier med 25 % kapital hver</h1>
<p>Bygget {datetime.now():%Y-%m-%d %H:%M}</p></div>{status}{main}
<div class="kort"><h2>Enkeltstrategiene og deres handelsregler</h2><p>Detaljene under
viser hver strategis egen historikk og siste registrerte beholdning. Datoene kan være
nyere eller eldre enn den felles perioden over. Alle tall gjelder simulert handel.</p></div>
{detail}<div class="kort"><h2>Kjøringen</h2>{runs}</div>
{sections.get('ekstra','')}<div class="fot"><p>Historisk avkastning dokumenterer ikke
fremtidig avkastning. Opprinnelige kostnadsforutsetninger beholdes i modellkurvene;
ekstra kapitaljusteringer har ikke modellerte handelskostnader. Innsidevariantene har en separat kostnadstest.</p></div>
</div></body></html>'''
