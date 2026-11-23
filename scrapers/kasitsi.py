"""Käsitsi lisatud mängud ja üritused (kasitsi.toml).

Automaatsed allikad ei kata sõprusmänge, turniire, eriüritusi ega osa koondiste kodumänge. Otsingu agent
(või inimene) lisab need faili kasitsi.toml pull request'iga. Agendi PR-i merge'ib automaatne kontroll
(scripts/automerge_check.py), kui kõik kontrollid läbivad. Muidu vaatab omanik selle üle.
Iga kirje peab põhinema ametlikul avalikul allikal (`url`). Isikuandmeid (mängijate nimesid) ei lisata.

Kontroll enne PR-i:  python -m scrapers.kasitsi
"""

from __future__ import annotations

import sys
import tomllib
from datetime import date, datetime, time
from pathlib import Path
from urllib.parse import urlparse

from .model import LEVELS, SPORTS, TALLINN, Event, new_event, parse_score

NAME = "kasitsi"
DEFAULT_PATH = Path(__file__).resolve().parent.parent / "kasitsi.toml"

KINDS = ("mäng", "sõprusmäng", "turniir", "eriüritus", "võistlus")
REQUIRED = ("sport", "league", "level", "start", "home", "venue", "url", "added", "kind")
OPTIONAL = ("away", "time_tbc", "result", "note", "end")
# tasemed, mida saab lisada: valikus nähtavad päris tasemed (mitte 0 = "kõik" ega peidetud 3)
ALLOWED_LEVELS = tuple(k for k, v in LEVELS.items() if not v.get("all") and not v.get("hidden"))
# sotsiaalmeedia ei ole lubatud allikas (VISION.md)
BANNED_HOSTS = ("facebook.com", "fb.com", "fb.me", "instagram.com", "tiktok.com", "x.com", "twitter.com")


def _start(value, time_tbc: bool) -> tuple[datetime, bool]:
    """TOML-i kuupäev või kuupäev+kellaaeg → Tallinna aeg. Ainult kuupäev tähendab "kellaaeg täpsustamisel"."""
    if isinstance(value, datetime):
        start = value if value.tzinfo else value.replace(tzinfo=TALLINN)
        return start.astimezone(TALLINN), time_tbc
    if isinstance(value, date):
        return datetime.combine(value, time(12, 0), tzinfo=TALLINN), True
    raise ValueError("start peab olema kuupäev (2026-12-05) või kuupäev ja kellaaeg (2026-12-05T18:00:00)")


def _check(item: dict) -> list[str]:
    errors = [f"puudub {k!r}" for k in REQUIRED if k not in item or item[k] in ("", None)]
    errors += [f"tundmatu väli {k!r}" for k in item if k not in REQUIRED + OPTIONAL]
    if item.get("sport") and item["sport"] not in SPORTS:
        errors.append(f"tundmatu ala {item['sport']!r} (lubatud: {', '.join(SPORTS)})")
    if "level" in item and item["level"] not in ALLOWED_LEVELS:
        errors.append(f"tase {item['level']!r} pole lubatud (lubatud: {', '.join(map(str, ALLOWED_LEVELS))})")
    if item.get("kind") and item["kind"] not in KINDS:
        errors.append(f"tundmatu liik {item['kind']!r} (lubatud: {', '.join(KINDS)})")
    if item.get("url"):
        host = (urlparse(str(item["url"])).hostname or "").lower()
        if not str(item["url"]).startswith(("https://", "http://")) or not host:
            errors.append("url peab algama https://")
        elif any(host == b or host.endswith("." + b) for b in BANNED_HOSTS):
            errors.append(f"sotsiaalmeedia ({host}) pole lubatud allikas")
    if "added" in item and not isinstance(item["added"], date):
        errors.append("added peab olema kuupäev (2026-11-22)")
    if "time_tbc" in item and not isinstance(item["time_tbc"], bool):
        errors.append("time_tbc peab olema true või false")
    if "end" in item:
        start = item.get("start")
        start_day = start.date() if isinstance(start, datetime) else start
        if isinstance(item["end"], datetime) or not isinstance(item["end"], date):
            errors.append("end peab olema kuupäev (2026-12-06), mitmepäevase ürituse viimane päev")
        elif isinstance(start_day, date) and item["end"] <= start_day:
            errors.append("end peab olema hilisem kui start (ühepäevasel jäta end ära)")
    if item.get("result") and not parse_score(str(item["result"])):
        errors.append("result peab olema kujul \"3-1\"")
    return errors


def parse(text: str) -> list[Event]:
    """Loeb kasitsi.toml sisu. Vigase kirje korral ValueError, mis loetleb kõik vead (kirje number ja võistkond)."""
    data = tomllib.loads(text)
    unknown = [k for k in data if k != "event"]
    problems = [f"tundmatu jaotis {k!r} (kirjed on [[event]] all)" for k in unknown]
    events: list[Event] = []
    for n, item in enumerate(data.get("event", []), start=1):
        errors = _check(item)
        if not errors:
            try:
                start, tbc = _start(item["start"], bool(item.get("time_tbc", False)))
            except ValueError as exc:
                errors.append(str(exc))
        if errors:
            problems.append(f"kirje {n} ({item.get('home', '?')}): " + "; ".join(errors))
            continue
        events.append(new_event(
            source=NAME, sport=item["sport"], league=item["league"].strip(), start=start,
            home=item["home"], away=item.get("away", ""), venue=item["venue"].strip(), city="",
            url=item["url"], time_tbc=tbc, level=item["level"], result=parse_score(str(item.get("result", ""))),
            end=item.get("end"),
        ))
    if problems:
        raise ValueError("kasitsi.toml: " + " | ".join(problems))
    return events


def load(path: Path = DEFAULT_PATH) -> list[Event]:
    path = Path(path)
    return parse(path.read_text(encoding="utf-8")) if path.exists() else []


def fetch(fetcher=None, source: dict | None = None) -> list[Event]:
    """Võrgupäringuid pole: loeb repo faili. Saali nimi ja linn tulevad venues.toml-ist (build.only_estonia)."""
    return load()


def main() -> int:
    """`python -m scrapers.kasitsi`: kontrollib faili ja saalid, prindib kirjed. Vea korral väljumiskood 1."""
    from .config import load as load_config
    from .geo import Geo
    from .venues import Venues

    try:
        events = load()
    except ValueError as exc:
        print(f"VIGA: {exc}")
        return 1
    venues, geo = Venues.load(), Geo(load_config())
    bad = 0
    for e in sorted(events, key=lambda e: e.start):
        v = venues.lookup(e.venue)
        where = f"{v.name}, {v.city}" if v else "TUNDMATU SAAL (lisa venues.toml faili)"
        if v is None or not geo.is_estonian(v.city):
            bad += 1
            if v is not None:
                where += " – EI OLE EESTIS (geo.foreign või puudub config.toml-ist)"
        when = f"{e.start:%d.%m.%Y}" + (" kell ?" if e.time_tbc else f" {e.start:%H:%M}")
        title = f"{e.home} – {e.away}" if e.away else e.home
        print(f"{when}  {SPORTS[e.sport]}  {title}  ({e.league}, tase {e.level})  {where}")
    print(f"Kokku {len(events)} kirjet" + (f", {bad} saaliga probleem" if bad else ", kõik korras"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
