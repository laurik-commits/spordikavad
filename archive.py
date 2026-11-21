"""Ajalooarhiiv: iga mäng, mille allikas on kunagi näidanud, koos muutuste ajalooga.

Miks: allikad näitavad ainult praegust seisu. Ümberpandud kellaaeg, vahetunud saal või ära jäänud mäng
kaovad liidu lehelt jäljetult. Arhiiv hoiab need alles.

Kuju: `archive/<aasta>/<allikas>.json` = {mängu id: kirje}. Aasta on mängu alguse aasta.
Kirje: `first_seen`, `event` (viimane teadaolev seis), `changes` (muutuste loend),
`missing_since` (kuupäev, millest alates tulevane mäng allikast puudub, nt ära jäänud).

Faili ei puudutata, kui midagi pole muutunud: ei kasutata "viimati nähtud" kuupäeva (see muudaks igapäevast
iga rida ja paisutaks git'i ajalugu). Ainult lisamine: kirjeid ei kustutata.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from scrapers.model import Event

ROOT = Path(__file__).parent
ARCHIVE = ROOT / "archive"

# väljad, mille muutumine on ajaloo mõttes oluline (id ja allikas ei muutu)
TRACKED = ("start", "home", "away", "venue", "city", "league", "time_tbc", "url", "result")


def _path(year: int, source: str, root: Path) -> Path:
    return root / str(year) / f"{source}.json"


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    # rikutud fail annab vea (ei kirjutata üle): arhiivi ei tohi vaikselt kaotada, ehitus logib vea ja jätkab
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: arhiivi fail pole sõnastik")
    return data


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8")


def update(source: str, events: list[Event], today: date, *, complete: bool = True,
           root: Path = ARCHIVE) -> int:
    """Lisab arhiivi uued mängud, märgib muutused. Tagastab muudetud kirjete arvu.

    `complete=False` (osa võistlusi ei vastanud): puuduvaid mänge ei märgita kadunuks.
    """
    by_year: dict[int, list[Event]] = {}
    for e in events:
        by_year.setdefault(e.start.year, []).append(e)
    # varasemate aastate failid, kus on selle allika tulevasi mänge (aastavahetus), vaatame ka läbi
    years = set(by_year) | {y for y in (today.year, today.year + 1) if _path(y, source, root).exists()}
    touched = 0
    for year in sorted(years):
        path = _path(year, source, root)
        data = _load(path)
        before = json.dumps(data, sort_keys=True)
        seen = set()
        for e in by_year.get(year, []):
            seen.add(e.id)
            now = e.to_dict()
            rec = data.get(e.id)
            if rec is None:
                data[e.id] = {"first_seen": today.isoformat(), "event": now, "changes": []}
                continue
            old = rec["event"]
            # vanemas kirjes puudub "result" (lisati hiljem): puudumine = tühi tulemus, mitte muutus
            diff = [{"on": today.isoformat(), "field": f, "from": old.get(f, ""), "to": now.get(f, "")}
                    for f in TRACKED if old.get(f, "" if f == "result" else None) != now.get(f)]
            if diff:
                rec["changes"].extend(diff)
                rec["event"] = now
            else:
                rec["event"] = now  # sisu sama, aga hoiab kuju (nt uus väli) ühtlasena
            rec.pop("missing_since", None)
        if complete:
            for eid, rec in data.items():
                if eid in seen or "missing_since" in rec:
                    continue
                if rec["event"]["start"][:10] >= today.isoformat():
                    rec["missing_since"] = today.isoformat()
        if json.dumps(data, sort_keys=True) != before:
            _write(path, data)
            touched += 1
    return touched
