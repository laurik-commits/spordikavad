"""Hoolduslogi MAINTENANCE.md: kui palju hooldust leht tegelikult nõuab.

Automaatsete Issue'de (silt `allikas`, vt report_issues.py) iga avamine, uuendamine ja sulgemine lisatakse
faili tabelisse „Automaatsete Issue'de logi“; selle põhjal arvutatakse kokkuvõte (kuude kaupa avatud ja suletud,
praegu avatud, keskmine lahendusaeg). Tabelit „Käsitsi hooldus“ täidavad inimesed ja agendid (nt katkise allika
parandus pull request'iga): üks rida, mis oli katki ja mis parandus oli. Ainult standardteek.

Fail on ise andmebaas: read loetakse tagasi (`parse`), uued lisatakse (`add_events`, sama päeva sama sündmust
topelt ei lisata), kokkuvõte arvutatakse uuesti (`render`). Käitub korduvkäivitusel sama.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "MAINTENANCE.md"
DEFAULT_REPO = "laurik-commits/spordikavad"

INTRO = """# Hooldus

Siin on näha, kui palju käsitsi hooldust leht tegelikult nõuab. Tabel „Automaatsete Issue'de logi“ täitub ise
(`scripts/report_issues.py` igal ehitusel); tabelisse „Käsitsi hooldus“ lisab rea igaüks, kes katkist allikat või
muud asja parandab (inimene või agent, üks rida: mis oli katki, mis parandus oli ja PR). Kokkuvõte arvutatakse ridadest.
"""

AUTO_HEAD = "## Automaatsete Issue'de logi"
MANUAL_HEAD = "## Käsitsi hooldus"
SUMMARY_HEAD = "## Kokkuvõte"
_AUTO = re.compile(r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*(avatud|uuendatud|suletud)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$")
_REF = re.compile(r"\[#(\d+)\]")
_MANUAL = re.compile(r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$")


def parse(text: str) -> tuple[list[dict], list[dict]]:
    """(automaatsed read, käsitsi read) failist. Rida: {"date", "event", "what", "note"} / {"date", "what", "fix"}."""
    auto, manual, section = [], [], ""
    for line in text.splitlines():
        if line.startswith("## "):
            section = line.strip()
            continue
        if section == AUTO_HEAD and (m := _AUTO.match(line)):
            auto.append({"date": m.group(1), "event": m.group(2), "what": m.group(3), "note": m.group(4)})
        elif section == MANUAL_HEAD and (m := _MANUAL.match(line)):
            manual.append({"date": m.group(1), "what": m.group(2), "fix": m.group(3)})
    return auto, manual


def _ref(what: str) -> str:
    m = _REF.search(what)
    return m.group(1) if m else what


def add_events(rows: list[dict], events: list[dict]) -> list[dict]:
    """Lisab uued read; sama kuupäeva sama sündmus sama Issue'ga topelt ei lisata."""
    seen = {(r["date"], r["event"], _ref(r["what"])) for r in rows}
    out = list(rows)
    for e in events:
        key = (e["date"], e["event"], _ref(e["what"]))
        if key not in seen:
            seen.add(key)
            out.append(e)
    return sorted(out, key=lambda r: r["date"])   # stabiilne: sama päeva read jäävad lisamise järjekorda


def summary(auto: list[dict], manual: list[dict]) -> list[str]:
    opened = defaultdict(int)
    closed = defaultdict(int)
    last: dict[str, dict] = {}
    first_open: dict[str, str] = {}
    lead_days: list[int] = []
    for r in auto:
        ref, month = _ref(r["what"]), r["date"][:7]
        if r["event"] == "avatud":
            opened[month] += 1
            first_open.setdefault(ref, r["date"])
        elif r["event"] == "suletud":
            closed[month] += 1
            if ref in first_open:
                lead_days.append((date.fromisoformat(r["date"]) - date.fromisoformat(first_open.pop(ref))).days)
        last[ref] = r
    still_open = [r for r in last.values() if r["event"] != "suletud"]
    lines = ["| Kuu | Avatud | Suletud | Käsitsi parandusi |", "|---|---|---|---|"]
    months = sorted(set(opened) | set(closed) | {r["date"][:7] for r in manual})
    for m in months:
        lines.append(f"| {m} | {opened[m]} | {closed[m]} | {sum(1 for r in manual if r['date'][:7] == m)} |")
    lines.append(f"| **Kokku** | **{sum(opened.values())}** | **{sum(closed.values())}** | **{len(manual)}** |")
    avg = f"{sum(lead_days) / len(lead_days):.1f} päeva ({len(lead_days)} suletud Issue't)" if lead_days else "–"
    lines += ["", f"- Praegu avatud automaatseid Issue'sid: **{len(still_open)}**"
              + (": " + ", ".join(r["what"] for r in still_open) if still_open else ""),
              f"- Keskmine aeg avamisest sulgemiseni: {avg}"]
    return lines


def render(auto: list[dict], manual: list[dict]) -> str:
    out = [INTRO.rstrip("\n"), "", SUMMARY_HEAD, "", *summary(auto, manual), "", MANUAL_HEAD, "",
           "| Kuupäev | Mis oli katki | Parandus |", "|---|---|---|"]
    out += [f"| {r['date']} | {r['what']} | {r['fix']} |" for r in manual]
    out += ["", AUTO_HEAD, "", "| Kuupäev | Sündmus | Issue | Märkus |", "|---|---|---|---|"]
    out += [f"| {r['date']} | {r['event']} | {r['what']} | {r['note']} |" for r in auto]
    return "\n".join(out) + "\n"


def issue_link(number: int | str, title: str, repo: str = DEFAULT_REPO) -> str:
    return f"[#{number}](https://github.com/{repo}/issues/{number}) {title}"


def record(events: list[dict], path: Path = PATH) -> bool:
    """Lisab sündmused faili (kui miski muutus). Tagastab True, kui faili kirjutati."""
    path = Path(path)
    auto, manual = parse(path.read_text(encoding="utf-8")) if path.exists() else ([], [])
    new = add_events(auto, events)
    text = render(new, manual)
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.write_text(text, encoding="utf-8")
    return True
