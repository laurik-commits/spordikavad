"""Jalgpall: Eesti koondiste mängud (jalgpall.ee/koondis/<id>/mangud).

Sama sait ja sama robots.txt mis jalgpall_ejl.py (`User-agent: *`, Crawl-Delay 5). Leht on serveris renderdatud:
kaks loendit, `national-upcoming-matches` (tulevased) ja `national-previous-matches` (mängitud), mõlemas plokid
  <div class="event-single"> <p class="title"><a href="/koondis/7/tournament/632">UEFA Rahvuste liiga 2027</a></p>
    <p>06.03.2027 kell 00:00 </p> <p>Bosnia ja Hertsegoviina</p> ... <div class="team">...<p>Eesti</p></div> ...
Kellaaeg "00:00" tähendab, et kell pole veel teada (time_tbc). Saali nimi on kirjas ainult koht, mis võib olla
välisriigi staadion: need jäävad geo-filtriga välja.

Võtame ainult mängud, kus esimene (kodu-) võistkond on Eesti koondis ("Eesti", "Eesti U21" jne), sest
võõrsil mängude väljak on välismaal ja tundmatu saali hoiatusi me ei tahaks. Eestis peetavad neutraalse
kodu-/võõrsil järjekorraga mängud (nt Balti turniir) võivad seetõttu puududa.
"""

from __future__ import annotations

import html
import re
from datetime import datetime

from .model import Event, new_event

NAME = "jalgpall_koondis"
SPORT = "jalgpall"
BASE = "https://jalgpall.ee"

_BLOCK = re.compile(r'<div class="event-single">')
_TITLE = re.compile(r'<p class="title">\s*(?:<a[^>]*>)?\s*([^<]+?)\s*(?:</a>)?\s*</p>', re.S)
_WHEN = re.compile(r"<p>\s*(\d{2}\.\d{2}\.\d{4})\s+(?:kell|Aeg)\s+(\d{1,2}:\d{2})")
_VENUE = re.compile(r"</p>\s*<p>\s*([^<]*?)\s*</p>\s*</div>\s*<div class=\"teams\">", re.S)
_TEAM = re.compile(r'<div class="team">.*?<p>\s*([^<]+?)\s*</p>\s*</div>', re.S)
_INFO = re.compile(r'href="(/koondis/\d+/matchinfo/match/\d+)"')


def url_for(team_id: int) -> str:
    return f"{BASE}/koondis/{team_id}/mangud"


def parse(page: str, team_name: str, *, sport: str = SPORT, source: str = NAME) -> list[Event]:
    marks = [m.start() for m in _BLOCK.finditer(page)] + [len(page)]
    events: list[Event] = []
    for a, b in zip(marks, marks[1:]):
        block = page[a:b]
        title, when, venue = _TITLE.search(block), _WHEN.search(block), _VENUE.search(block)
        teams, info = _TEAM.findall(block), _INFO.search(block)
        if not (title and when and len(teams) >= 2 and info):
            continue
        home, away = html.unescape(teams[0]), html.unescape(teams[1])
        if not home.startswith("Eesti"):
            continue  # võõrsil mäng, väljak on välismaal
        place = html.unescape(venue.group(1)).strip() if venue else ""
        if "," in place:
            continue  # välisriigi väljak on kirjas "Saal, Riik" (nt "Globall Football Park, Ungari"); Eesti saalidel koma pole
        day, hhmm = when.groups()
        events.append(
            new_event(
                source=source, sport=sport, league=f"{team_name}: {html.unescape(title.group(1))}",
                start=datetime.strptime(f"{day} {hhmm}", "%d.%m.%Y %H:%M"),
                home=home, away=away, venue=place, city="",
                url=BASE + info.group(1), time_tbc=hhmm == "00:00", level=5,
            )
        )
    return events


def fetch(fetcher, source: dict | None = None) -> list[Event]:
    events: list[Event] = []
    for comp in (source or {}).get("competitions", []):
        events.extend(parse(fetcher.get(url_for(comp["id"])), comp["league"]))
    return events
