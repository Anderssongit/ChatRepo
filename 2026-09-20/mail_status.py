# -*- coding: utf-8 -*-
"""Datastatusblokken som ligger ØVERST i mailen.

Det første du skal se er om dataene kom ned, for hver av de fire strategiene,
før ett eneste avkastningstall. Blokken svarer på tre spørsmål per strategi:

    hentet den noe?  hvor langt går dataene?  teller den i fellestallene?

Ren stdlib: ingen pandas, ingen import av innsidehandel_pipeline. Blokken kan
dermed bygges og testes uten at noe av det tunge er installert, og den kan
rendres selv når resten av mailen feiler.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, Iterable, Sequence

GRONN = "#2e7d32"
ROD = "#c62828"
GUL = "#ef6c00"

FARGE = {"OK": GRONN, "FORELDET": GUL, "MANGLER": ROD, "FEIL": ROD}

HANDLING_TEKST = {
    "SKREVET": "lastet ned og skrevet",
    "GJENBRUKT": "gjenbrukt (fersk nok)",
    "DEGRADERT": "beholdt forrige fil",
    "HOPPET": "hoppet over",
    "FEIL": "feilet",
    "OK": "hentet",
}


def _escape(value) -> str:
    return "" if value is None else _html.escape(str(value), quote=True)


def _cell(value, *, color: str = "", bold: bool = False) -> str:
    style = []
    if color:
        style.append(f"color:{color}")
    if bold:
        style.append("font-weight:600")
    attribute = f' style="{";".join(style)}"' if style else ""
    return f"<td{attribute}>{_escape(value)}</td>"


def _table(headers: Sequence[str], rows: Iterable[Sequence[str]]) -> str:
    head = "".join(f"<th>{_escape(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(cells) + "</tr>" for cells in rows)
    return f"<table><tr>{head}</tr>{body}</table>"


def _age(row: Dict[str, Any]) -> str:
    alder = row.get("Alder_Dager")
    if alder is None:
        return "—"
    if alder < 0:
        return f"{-int(alder)} dager FREM I TID"
    return f"{int(alder)} dager"


def _download_text(row: Dict[str, Any]) -> str:
    problems = row.get("Nedlasting") or []
    if not problems:
        return "ingen feil"
    return "; ".join(str(p) for p in problems)


def status_rows_html(rows: Sequence[Dict[str, Any]]) -> str:
    """Hovedtabellen: én linje per strategi."""
    body = []
    for row in rows:
        status = str(row.get("Status") or "")
        color = FARGE.get(status, "")
        body.append([
            _cell(row.get("Strategi"), bold=True),
            _cell(_download_text(row)),
            _cell(row.get("Siste") or "—"),
            _cell(_age(row)),
            _cell(status, color=color, bold=True),
            _cell(row.get("Konsekvens"), color="" if row.get("I_Portefolje") else color),
        ])
    return _table(["Strategi", "Nedlasting", "Siste observasjon", "Alder",
                   "Status", "Følge for fellestallene"], body)


def acquisition_html(acquisition: Sequence[Dict[str, Any]]) -> str:
    """Grunnlagsfilene denne kjøringen bygde eller gjenbrukte."""
    if not acquisition:
        return ""
    body = []
    for row in acquisition:
        handling = str(row.get("Handling") or "").upper()
        color = ROD if handling in ("FEIL",) else (GUL if handling in ("DEGRADERT", "HOPPET") else "")
        rader = row.get("Rader")
        body.append([
            _cell(row.get("Kilde"), bold=True),
            _cell(HANDLING_TEKST.get(handling, handling or "—"), color=color),
            _cell("—" if rader in (None, "") else f"{int(rader):,}".replace(",", " ")),
            _cell(row.get("Siste") or "—"),
            _cell(row.get("Merknad") or ""),
        ])
    return ("<h3>Grunnlagsfilene kjøringen bygde</h3>"
            "<p>Disse tre filene kom før fra et annet program. Masteren bygger dem "
            "nå selv, av data den allerede laster ned.</p>"
            + _table(["Kilde", "Handling", "Rader", "Siste", "Merknad"], body))


def problems_html(rows: Sequence[Dict[str, Any]]) -> str:
    """Én punktliste med nøyaktig hva som er galt, for hver strategi som ikke er OK."""
    daarlige = [r for r in rows if not r.get("I_Portefolje")]
    if not daarlige:
        return ""
    punkter = "".join(
        f"<li><b>{_escape(r.get('Strategi'))}</b> — {_escape(r.get('Status'))}: "
        f"{_escape(r.get('Begrunnelse'))}."
        + (f" Nedlasting: {_escape(_download_text(r))}." if r.get("Nedlasting") else "")
        + "</li>"
        for r in daarlige)
    return ("<h3>Hva som mangler, og hva det betyr</h3><ul>" + punkter + "</ul>"
            "<p>En strategi uten ferske data utelates fra den samlede porteføljen. "
            "Den erstattes ikke med null avkastning, og den gamle verdien videreføres "
            "ikke som om den var dagens. Strategiens egen seksjon lenger nede viser "
            "fortsatt det den faktisk har, med sine egne datoer.</p>")


def render(status: Dict[str, Any]) -> str:
    """Hele blokken. Tåler et tomt eller halvt utfylt statusobjekt."""
    if not status:
        return ('<div class="kort"><h2>Datastatus</h2><p>Datastatus kunne ikke '
                'bygges for denne kjøringen. Tallene nedenfor er dermed ikke '
                'kontrollert for ferskhet.</p></div>')
    rows = list(status.get("rows") or ())
    if not rows:
        return ('<div class="kort"><h2>Datastatus</h2><p>Ingen strategier ble '
                'vurdert. Ingen fellestall kan bygges av dette.</p></div>')
    alle_ok = bool(status.get("all_ok"))
    farge = GRONN if alle_ok else ROD
    overskrift = ("Datastatus: alle fire strategier har ferske data"
                  if alle_ok else "Datastatus: ikke alle strategier har ferske data")
    return (
        '<div class="kort">'
        f'<h2 style="color:{farge}">{_escape(overskrift)}</h2>'
        f'<p style="font-weight:600">{_escape(status.get("summary") or "")}</p>'
        f'<p>Vurdert mot rapportdato {_escape(status.get("as_of") or "")}. '
        'En strategi er OK bare når eksporten kan leses, er gyldig og siste '
        'observasjon er innenfor grensen for den strategien — 45 dager for den '
        'månedlige PB-ROE-kurven, 7 dager for de tre daglige.</p>'
        + status_rows_html(rows)
        + problems_html(rows)
        + acquisition_html(list(status.get("acquisition") or ()))
        + '</div>')
