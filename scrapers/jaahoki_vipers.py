"""Jäähoki: Unibet Hokiliiga, HC Vipersi kodumängud klubi kodulehelt (hcvipers.ee/?page=games).

Eesti Jäähokiliidu ajakava (ehs.eestihoki.ee) laaditakse hockeydata.net-ist liidu API-võtmega, mida me ei kasuta
(SOURCES.md). HC Vipersi leht on serveris renderdatud, robots.txt-i pole (404). Lehel on kõigi Vipersi võistkondade
tulevased mängud, iga mäng kahes vaates: nimekirjas (<article class="gc10-game-row">) ja kalendriruudus
(<article class="gc10-tile">). Loeme ainult nimekirja:

  <article class="gc10-game-row" data-team="unibet" data-month="2026-11" data-date="2026-11-28"
           data-title="HC Vipers Unibet — HC Everest">
    <div class="gc10-date-box"><b>28</b><span>NOV</span><small>16:35</small></div>
    ... <div class="gc10-venue"><span class="gc10-pin">⌖</span><span>Tondiraba Jäähall</span></div>
    ... <a href="https://ehs.eestihoki.ee/statistika/maengu-aruanne/?divisionId=…&amp;gameId=…">Mäng ↗</a>

Koht on lehel IGAL mängul "Tondiraba Jäähall", ka võõrsil (nt Viru Sputniku kodumäng). Seepärast võtame ainult
Vipersi kodumängud: kodumeeskond on pealkirjas esimene. Vipersi kodusaal on Tondiraba jäähall.
Noorte võistkonnad (U19 kuni U8) jäävad praegu välja, sest nende kodumängud võivad olla ka teistes jäähallides ja
lehe koha väli pole usaldusväärne. Lehel on ainult tulevased mängud, tulemusi pole.
Mängu link viib Eesti Hoki Statistika mängulehele (kui see on lehel), muidu Vipersi mängude lehele.
"""

from __future__ import annotations

import html
import re
from datetime import date, datetime

from .model import Event, new_event

NAME = "jaahoki_vipers"
SPORT = "jaahoki"
URL = "https://hcvipers.ee/?page=games&lang=et"

# data-team → (liiga, tase). Noorte võistkonnad lisa siia (level = 4), kui nende mängupaik on kindel.
TEAMS = {"unibet": ("Unibet Hokiliiga", 1)}
OWN = "HC Vipers"
# meeskonna nimi lehel → nimi meie lehel (liiga nimes on sponsor juba olemas)
TEAM_NAMES = {"HC Vipers Unibet": "HC Vipers"}

_ROW = re.compile(r'<article\s+class="gc10-game-row"(.*?)</article>', re.S)
_ATTR = re.compile(r'data-(team|date|title)="([^"]*)"')
_TIME = re.compile(r'class="gc10-date-box">.*?<small>\s*(\d{1,2})[:.](\d{2})\s*</small>', re.S)
_VENUE = re.compile(r'class="gc10-venue">.*?class="gc10-pin">.*?</span>\s*<span>([^<]*)</span>', re.S)
_LINK = re.compile(r'class="gc10-action">.*?href="(https://[^"]+)"', re.S)


def _clean(text: str) -> str:
    return " ".join(html.unescape(text).split())


def parse(page: str) -> list[Event]:
    events: list[Event] = []
    seen: set[tuple] = set()
    for block in _ROW.findall(page):
        tag, _, body = block.partition(">")
        attrs = dict(_ATTR.findall(tag))
        team = TEAMS.get(attrs.get("team", ""))
        home, sep, away = _clean(attrs.get("title", "")).partition(" — ")
        if not team or not sep or not home.startswith(OWN):
            continue
        try:
            day = date.fromisoformat(attrs.get("date", ""))
        except ValueError:
            continue
        when = _TIME.search(body)
        start = datetime(day.year, day.month, day.day,
                         int(when.group(1)) if when else 0, int(when.group(2)) if when else 0)
        key = (start, home, away)
        if key in seen:
            continue
        seen.add(key)
        venue = _VENUE.search(body)
        link = _LINK.search(body)
        league, level = team
        events.append(
            new_event(
                source=NAME, sport=SPORT, league=league, start=start,
                home=TEAM_NAMES.get(home, home), away=away,
                venue=_clean(venue.group(1)) if venue else "", city="",
                url=html.unescape(link.group(1)) if link else URL,
                time_tbc=when is None, level=level,
            )
        )
    return events


def fetch(fetcher) -> list[Event]:
    return parse(fetcher.get(URL))
