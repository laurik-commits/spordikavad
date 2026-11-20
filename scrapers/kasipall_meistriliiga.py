"""Käsipall: meeste Meistriliiga (kasipall.ee).

Liiga leht https://kasipall.ee/league/359 näitab hooaja mänge (ka tulevasi mitu
nädalat ette): kuupäev, kell, võistkonnad ja protokolli link. Saali nime liiga
lehel pole, see on mängu protokolli lehel (ikoon "location_on").
Protokolli lehti küsitakse ainult lähipäevade mängude kohta.
"""

from __future__ import annotations

import html
import logging
import re
from datetime import date, datetime, timedelta

from .http import FetchError
from .model import TALLINN, Event, new_event

log = logging.getLogger(__name__)

NAME = "kasipall_meistriliiga"
SPORT = "kasipall"
LEAGUE = "Meistriliiga (mehed)"
BASE = "https://kasipall.ee"
URL = BASE + "/league/359"
WINDOW_DAYS = 15

_ROW = re.compile(r'id="calendar_row_(\d+)"')
_DATE = re.compile(r"<strong>(\d{2}\.\d{2}\.\d{4})</strong>")
_TIME = re.compile(r'<span class="text align-middle align-middle">\s*(\d{1,2}:\d{2})\s*</span>')
_TEAM = re.compile(r'<img src="[^"]*/image/club/[^"]*"\s+alt="\s*([^"]+?)\s*"')
_VENUE = re.compile(r"location_on\s*</span>.*?<strong>([^<]+)</strong>", re.S)


def parse_list(page: str) -> list[dict]:
    """Mängud liiga lehelt (ilma saalita). Sama rida on lehel kaks korda, võetakse esimene."""
    starts = [(m.start(), m.group(1)) for m in _ROW.finditer(page)] + [(len(page), "")]
    seen: set[str] = set()
    games: list[dict] = []
    for (a, gid), (b, _) in zip(starts, starts[1:]):
        if gid in seen:
            continue
        block = page[a:b]
        d, t, teams = _DATE.search(block), _TIME.search(block), _TEAM.findall(block)
        if not d or len(teams) < 2:
            continue
        seen.add(gid)
        games.append({
            "id": gid,
            "start": datetime.strptime(f"{d.group(1)} {t.group(1) if t else '00:00'}", "%d.%m.%Y %H:%M"),
            "time_tbc": t is None,
            "home": html.unescape(teams[0]),
            "away": html.unescape(teams[1]),
        })
    return games


def parse_venue(page: str) -> str:
    m = _VENUE.search(page)
    return html.unescape(m.group(1)).strip() if m else ""


def to_event(g: dict, venue: str) -> Event:
    return new_event(
        source=NAME, sport=SPORT, league=LEAGUE, start=g["start"], home=g["home"], away=g["away"],
        venue=venue, city="", url=f"{BASE}/protocol/{g['id']}", time_tbc=g["time_tbc"],
    )


def fetch(fetcher, today: date | None = None) -> list[Event]:
    today = today or datetime.now(TALLINN).date()
    last = today + timedelta(days=WINDOW_DAYS)
    events = []
    for g in parse_list(fetcher.get(URL)):
        venue = ""
        if today <= g["start"].date() <= last:
            try:
                venue = parse_venue(fetcher.get(f"{BASE}/protocol/{g['id']}"))
            except FetchError as exc:
                log.warning("%s: protokolli %s ei saanud: %s", NAME, g["id"], exc)
        events.append(to_event(g, venue))
    return events
