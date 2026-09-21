"""Run-scoped download evidence and the first section of every email.

No file or network access occurs here. Each downloader records evidence; a
successful backtest is never used as evidence that its inputs were downloaded.
"""
from __future__ import annotations

from datetime import datetime, timezone
from html import escape

SOURCES = {
    "PB-ROE-Momentum": ("tickers", "pbroe_data", "pbroe_prices"),
    "NLP Sentiment — ledelse": ("articles", "management_prices"),
    "Sentiment Momentum v3.1": ("articles", "prices", "step4"),
    "Innsidehandel Oslo Børs": ("tickers", "insider_announcements", "insider_prices"),
}
LABELS = {
    "tickers": "Aksjeliste", "pbroe_data": "PB/ROE og fundamentaler", "pbroe_prices": "PB-ROE: kurser og referanse",
    "articles": "Artikler og sentiment", "management_prices": "Ledelsessentiment: kurser",
    "prices": "Felles kurshistorikk", "step4": "Sentimentendringer",
    "insider_announcements": "Innsidemeldinger", "insider_prices": "Innsidekurser",
}
_sources = {}


def reset():
    _sources.clear()


def record_source(key, status="FAILED", detail="", **metadata):
    status = str(status).upper()
    if status not in {"DOWNLOADED", "CACHED", "PARTIAL", "FAILED", "DERIVED", "NOT_RUN"}:
        raise ValueError(f"Unknown download status: {status}")
    row = {**metadata, "source": key, "status": status, "detail": str(detail),
           "checked_at": datetime.now(timezone.utc).isoformat()}
    _sources[key] = row
    return dict(row)


def get_source(key):
    return dict(_sources.get(key, {"source": key, "status": "NOT_RUN",
                                  "detail": "Ingen nedlasting bekreftet i denne kjøringen."}))


def snapshot():
    return {key: dict(row) for key, row in _sources.items()}


def strategy_rows(sources=None, *, cached_run=False):
    sources = snapshot() if sources is None else sources
    rows = []
    for strategy, keys in SOURCES.items():
        components = [dict(sources.get(key, {"source": key, "status": "NOT_RUN"})) for key in keys]
        states = {item.get("status", "NOT_RUN") for item in components}
        if cached_run:
            status = "CACHED"
        elif states <= {"DOWNLOADED", "DERIVED"} and "DOWNLOADED" in states:
            status = "DOWNLOADED"
        elif "FAILED" in states:
            status = "FAILED"
        elif states == {"NOT_RUN"}:
            status = "NOT_RUN"
        elif states <= {"CACHED", "DERIVED"}:
            status = "CACHED"
        else:
            status = "PARTIAL"
        rows.append({"strategy": strategy, "status": status, "sources": components})
    return rows


def render_download_summary(rows):
    labels = {"DOWNLOADED": "JA — lastet ned og kontrollert",
              "CACHED": "NEI — lagrede data", "PARTIAL": "DELVIS — se detaljer",
              "FAILED": "NEI — nedlasting eller kontroll feilet",
              "NOT_RUN": "NEI — ikke bekreftet", "DERIVED": "Beregnet fra kildedata"}
    body = []
    for row in rows:
        details = []
        for source in row.get("sources", []):
            key = source.get("source", "")
            parts = [LABELS.get(key, key), labels.get(source.get("status"), source.get("status", ""))]
            expected, usable = source.get("expected_count"), source.get("usable_count")
            if expected is not None and usable is not None:
                parts.append(f"dekning {usable}/{expected}")
            if source.get("latest_observation"):
                parts.append("siste observasjon " + str(source["latest_observation"]))
            if source.get("detail"):
                parts.append(str(source["detail"]))
            issues = source.get("issues") or []
            if isinstance(issues, str):
                issues = [issues]
            parts.extend(str(x) for x in issues[:8])
            details.append(escape(" · ".join(parts)))
        body.append("<tr><td>" + escape(row["strategy"]) + "</td><td>"
                    + escape(labels.get(row["status"], row["status"]))
                    + "</td><td>" + "<br>".join(details) + "</td></tr>")
    return ('<div class="kort" id="download-status"><h2>Ble data lastet ned riktig?</h2>'
            '<p>Status gjelder denne kjøringen. Lagrede filer og fullført analyse er ikke '
            'bekreftelse på ny nedlasting. Dekning gjelder det konfigurerte universet; '
            'kildene garanterer ikke komplett historikk for avnoterte selskaper.</p>'
            '<table><tr><th>Strategi</th><th>Nedlasting</th><th>Kontroll og detaljer</th></tr>'
            + ''.join(body) + '</table></div>')


def prepend_summary(html, rows):
    """Also covers minimal failure emails; do not duplicate the normal header."""
    if 'id="download-status"' in html:
        return html
    section = render_download_summary(rows)
    import re
    return re.sub(r'(<body\b[^>]*>)', lambda match: match[0] + section,
                  html, count=1, flags=re.I) if re.search(r'<body\b', html, re.I) else section + html
