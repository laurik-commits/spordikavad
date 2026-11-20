"""Käsipall: Balti Käsipalliliiga ja naiste Eesti-Läti liiga (baltichandball.eu).

Leht https://baltichandball.eu/season/<season>/league/<league>/fixtures näitab tulevasi mänge:
kuu päis ("December, 2026"), päeva päis ("Saturday, December 5") ja iga mängu plokk
(kaks võistkonda, "HH:MM · Saal" ning link .../game/<id>/overview).
Võistlused (hooaja ja liiga ID, muutuvad igal hooajal) on config.toml-is (`competitions`).
robots.txt puudub (404) – piiranguid pole. Kõik saalid on EET ajavööndis (Eesti, Läti, Leedu).

Eesti klubide omavahelised mängud on sageli ka kasipall.ee-s (lähevad arvesse meistriliigas);
topelt mängud eemaldab build.py (dedupe).
"""

from __future__ import annotations

import html
import re
from datetime import datetime

from .model import Event, new_event

NAME = "kasipall_bhl"
SPORT = "kasipall"
BASE = "https://baltichandball.eu"

MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"], start=1)}

_MONTH = re.compile(r'<div class="h5 mb-0">\s*([A-Z][a-z]+), (\d{4})\s*</div>')
_DAY = re.compile(r'<div class="h6 mb-0">\s*[A-Z][a-z]+, ([A-Z][a-z]+) (\d{1,2})\s*</div>')
_BLOCK = re.compile(r'<div class="mb-4 px-3 py-4 shadow-sm">')
_TEAM = re.compile(r'<div class="h6 ms-3">\s*([^<]+?)\s*</div>')
_WHEN_WHERE = re.compile(r'fw-light">\s*(\d{1,2}:\d{2})?\s*<span class="px-2">·</span>\s*([^<]*)</div>')
_GAME = re.compile(r'href="(https://baltichandball\.eu/season/\d+/league/\d+/game/\d+)')


def fixtures_url(comp: dict) -> str:
    return f"{BASE}/season/{comp['season']}/league/{comp['id']}/fixtures"


def parse(page: str, comp: dict) -> list[Event]:
    marks = sorted(
        [(m.start(), "month", m) for m in _MONTH.finditer(page)]
        + [(m.start(), "day", m) for m in _DAY.finditer(page)]
        + [(m.start(), "game", m) for m in _BLOCK.finditer(page)],
        key=lambda x: x[0],
    )
    year = month = day = None
    events: list[Event] = []
    games = [pos for pos, kind, _ in marks if kind == "game"] + [len(page)]
    for pos, kind, m in marks:
        if kind == "month":
            year = int(m.group(2))
        elif kind == "day":
            month, day = MONTHS.get(m.group(1)), int(m.group(2))
        elif year and month and day:
            block = page[pos:games[games.index(pos) + 1]]
            teams, ww, link = _TEAM.findall(block), _WHEN_WHERE.search(block), _GAME.search(block)
            if len(teams) < 2 or not link:
                continue
            time = ww.group(1) if ww else None
            venue = html.unescape(ww.group(2)).strip().strip(",").strip() if ww else ""
            hh, mm = (int(x) for x in (time or "0:00").split(":"))
            events.append(
                new_event(
                    source=NAME, sport=SPORT, league=comp["league"], level=comp.get("level", 1),
                    start=datetime(year, month, day, hh, mm),
                    home=html.unescape(teams[0]), away=html.unescape(teams[1]),
                    venue=venue, city="", url=link.group(1), time_tbc=time is None,
                )
            )
    return events


def fetch(fetcher, source: dict | None = None) -> list[Event]:
    events: list[Event] = []
    for comp in (source or {}).get("competitions", []):
        events.extend(parse(fetcher.get(fixtures_url(comp)), comp))
    return events
