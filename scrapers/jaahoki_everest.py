"""Jäähoki: HC Everesti (Kohtla-Järve) mängud klubi avalehelt (hceverest.ee).

Eesti Jäähokiliidu ajakava (ehs.eestihoki.ee) laaditakse hockeydata.net-ist liidu API-võtmega, mida me ei kasuta
(SOURCES.md). HC Everesti avaleht on serveris renderdatud ja robots.txt lubab kõik (`Disallow:` tühi). Avalehel on
kõigi Everesti võistkondade tulevased mängud kaartidena, igaühel oma toimumiskohaga:

  <div class="card" ...>
    <a href="https://ehs.eestihoki.ee/" target="_blank" class="card-header">UNIBET HOKILIIGA</a>
    <div class="card-body">
      <h5 class="card-title">05.12.2026 16:00</h5>
      <h6 class="card-subtitle mb-2 text-muted">Kohtla-Järve jäähall</h6>
      <p class="card-text">HC Everest - Tartu Välk 494</p>

Erinevalt HC Vipersi lehest on koht igal mängul õige (Kohtla-Järve, Narva, Tartu Astri Arena, Haabersti,
Tondiraba), seepärast võtame nii kodu- kui ka võõrsil mängud. Liigad: Unibet Hokiliiga ja naiste hokiliiga
(kõrgliigad) ning noorte U19 ja U16 (level 4). Nooremad (U12, U10, U8) on lastevõistlused ja jäävad välja.
Kuupäevata kaardid ("TBD 14:30") jäetakse vahele. Lehel on ainult tulevased mängud, tulemusi pole.
"""

from __future__ import annotations

import html
import re
from dataclasses import replace
from datetime import datetime

from .model import Event, make_id, new_event

NAME = "jaahoki_everest"
SPORT = "jaahoki"
URL = "https://hceverest.ee/"

# kaardi päis (suurtähtedega võrreldes) → (liiga, tase)
LEAGUES = {
    "UNIBET HOKILIIGA": ("Unibet Hokiliiga", 1),
    "NAISTE HOKILIIGA": ("Naiste hokiliiga", 1),
    "NOORED U19": ("U19 noorteliiga", 4),
    "NOORED U16": ("U16 noorteliiga", 4),
}

_CARD = re.compile(
    r'class="card-header">([^<]*)</a>\s*<div class="card-body">\s*'
    r'<h5 class="card-title">([^<]*)</h5>\s*<h6 class="card-subtitle[^"]*">([^<]*)</h6>\s*'
    r'<p class="card-text">([^<]*)</p>', re.S)
_WHEN = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})(?:\s+(\d{1,2}):(\d{2}))?$")


def _clean(text: str) -> str:
    return " ".join(html.unescape(text).split())


def parse(page: str) -> list[Event]:
    page = re.sub(r"<!--.*?-->", "", page, flags=re.S)  # välja kommenteeritud osad ei ole mängud
    events: list[Event] = []
    seen: set[tuple] = set()
    ids: set[str] = set()
    for header, when_text, venue, teams in _CARD.findall(page):
        league = LEAGUES.get(_clean(header).upper())
        when = _WHEN.match(_clean(when_text))
        home, sep, away = _clean(teams).partition(" - ")
        if not league or not when or not sep:
            continue
        day, month, year, hour, minute = when.groups()
        start = datetime(int(year), int(month), int(day), int(hour or 0), int(minute or 0))
        key = (start, home, away)
        if key in seen:
            continue
        seen.add(key)
        event = new_event(
            source=NAME, sport=SPORT, league=league[0], start=start, home=home, away=away,
            venue=_clean(venue), city="", url=URL, time_tbc=hour is None, level=league[1],
        )
        if event.id in ids:  # noortel võib samal päeval olla kaks mängu samade võistkondade vahel
            event = replace(event, id=make_id(NAME, start, f"{home} {start:%H:%M}", away))
        ids.add(event.id)
        events.append(event)
    return events


def fetch(fetcher) -> list[Event]:
    return parse(fetcher.get(URL))
