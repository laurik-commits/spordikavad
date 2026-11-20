"""Jalgpall: Eesti Jalgpalli Liidu liigad (jalgpall.ee).

Liigade nimekiri on config.toml-is (`competitions`), nt Premium liiga (id 52) ja naiste meistriliiga (id 63).
Leht https://jalgpall.ee/voistlused/<id>/liigad/calendar?season=YYYY näitab terve hooaja mänge:
plokk "event-single" (data-field = staadion), kuupäev ja kell ("DD.MM.YYYY HH:MM"),
võistkonnad ja link /voistlused/match_info/N.
Hooaeg on kalendriaasta (märts–november), seega season = tänane aasta.
robots.txt: Crawl-Delay 5 (vt config.toml host_delays).
"""

from __future__ import annotations

import html
import re
from datetime import date, datetime

from .model import TALLINN, Event, new_event

NAME = "jalgpall_ejl"
SPORT = "jalgpall"
BASE = "https://jalgpall.ee"


def url_for(league_id: int, season: int) -> str:
    return f"{BASE}/voistlused/{league_id}/liigad/calendar?season={season}"


_BLOCK = re.compile(r'<div class="event-single" data-field="([^"]*)"')
_WHEN = re.compile(r'<p class="title">\s*(\d{2}\.\d{2}\.\d{4})(?:\s+(\d{1,2}:\d{2}))?\s*</p>')
_TEAM = re.compile(r'<div class="team">\s*<p>\s*<a\s[^>]*>\s*([^<]+?)\s*</a>')
_INFO = re.compile(r'href="(/voistlused/match_info/\d+)"')


def parse(page: str, league: str, *, sport: str = SPORT, source: str = NAME, team_prefix: str = "") -> list[Event]:
    """team_prefix: eemaldatav eesliide võistkonna nimest (saalijalgpallis "S. ")."""

    def team(name: str) -> str:
        name = html.unescape(name)
        return name[len(team_prefix):] if team_prefix and name.startswith(team_prefix) else name

    marks = [(m.start(), m.group(1)) for m in _BLOCK.finditer(page)] + [(len(page), "")]
    events: list[Event] = []
    for (a, field), (b, _) in zip(marks, marks[1:]):
        block = page[a:b]
        when, teams, info = _WHEN.search(block), _TEAM.findall(block), _INFO.search(block)
        if not when or len(teams) < 2 or not info:
            continue
        time = when.group(2)
        events.append(
            new_event(
                source=source, sport=sport, league=league,
                start=datetime.strptime(f"{when.group(1)} {time or '00:00'}", "%d.%m.%Y %H:%M"),
                home=team(teams[0]), away=team(teams[1]),
                venue=html.unescape(field).strip(), city="", url=BASE + info.group(1), time_tbc=not time,
            )
        )
    return events


def fetch(fetcher, source: dict | None = None, today: date | None = None) -> list[Event]:
    today = today or datetime.now(TALLINN).date()
    events: list[Event] = []
    for comp in (source or {}).get("competitions", []):
        events.extend(parse(fetcher.get(url_for(comp["id"], today.year)), comp["league"]))
    return events
