"""Käsipall: Eesti Käsipalliliidu võistlused (kasipall.ee).

Võistluste nimekiri on config.toml-is (`competitions`), nt meeste meistriliiga (359),
naiste meistriliiga (361) ja meeste karikas (362). ID-d võivad uuel hooajal muutuda.

Liiga leht https://kasipall.ee/league/<id> näitab hooaja mänge (ka tulevasi mitu nädalat ette):
kuupäev, kell, võistkonnad ja protokolli link. Saali nime liiga lehel pole, see on mängu
protokolli lehel (ikoon "location_on"). Protokolli lehti küsitakse ainult lähipäevade mängude kohta.
Tulevaste mängude protokollis on saal sageli veel määramata – siis kasutatakse kodumeeskonna
lehe välja "Koduväljak" (üks päring meeskonna kohta).
"""

from __future__ import annotations

import html
import logging
import re
from datetime import date, datetime, timedelta

from .http import FetchError
from .model import TALLINN, Event, new_event, parse_score

log = logging.getLogger(__name__)

NAME = "kasipall_liigad"
SPORT = "kasipall"
BASE = "https://kasipall.ee"
WINDOW_DAYS = 15

_ROW = re.compile(r'id="calendar_row_(\d+)"')
_DATE = re.compile(r"<strong>(\d{2}\.\d{2}\.\d{4})</strong>")
_TIME = re.compile(r'<span class="text align-middle align-middle">\s*(\d{1,2}:\d{2})\s*</span>')
_TEAM = re.compile(r'<img src="[^"]*/image/club/[^"]*"\s+alt="\s*([^"]+?)\s*"')
_VENUE = re.compile(r"location_on\s*</span>.*?<strong>([^<]+)</strong>", re.S)
_HOME_FIELD = re.compile(r"Koduväljak</h6>.*?<strong>([^<]+)</strong>", re.S)
_SCORE = re.compile(r'id="calendar_score_text_\d+"[^>]*>\s*([^<]*?)\s*</strong>')  # mängitud: "24 : 33"
_TEAM_LINK =re.compile(r'href="(https://kasipall\.ee/team/\d+/\d+)"')
# Võistkonna nime lõpus olev " N" (naised) või " K" (karikas) – liiga nimi ütleb sama
_SUFFIX = re.compile(r"\s+[NK]$")


def league_url(league_id: int) -> str:
    return f"{BASE}/league/{league_id}"


def _team(name: str) -> str:
    return _SUFFIX.sub("", html.unescape(name)).strip()


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
        team_link = _TEAM_LINK.search(block)
        score = _SCORE.search(block)
        games.append({
            "result": parse_score(score.group(1)) if score else "",
            "home_team_url": team_link.group(1) if team_link else "",
            "id": gid,
            "start": datetime.strptime(f"{d.group(1)} {t.group(1) if t else '00:00'}", "%d.%m.%Y %H:%M"),
            "time_tbc": t is None,
            "home": _team(teams[0]),
            "away": _team(teams[1]),
        })
    return games


def parse_venue(page: str) -> str:
    m = _VENUE.search(page)
    return html.unescape(m.group(1)).strip() if m else ""


def parse_home_field(page: str) -> str:
    m = _HOME_FIELD.search(page)
    return html.unescape(m.group(1)).strip() if m else ""


def to_event(g: dict, venue: str, league: str, level: int = 1) -> Event:
    return new_event(
        source=NAME, sport=SPORT, league=league, start=g["start"], home=g["home"], away=g["away"],
        venue=venue, city="", url=f"{BASE}/protocol/{g['id']}", time_tbc=g["time_tbc"], level=level,
        result=g.get("result", ""),
    )


def fetch(fetcher, source: dict | None = None, today: date | None = None) -> list[Event]:
    today = today or datetime.now(TALLINN).date()
    last = today + timedelta(days=WINDOW_DAYS)
    events = []
    home_fields: dict[str, str] = {}  # meeskonna leht → koduväljak (üks päring meeskonna kohta)

    def home_field(url: str) -> str:
        if url and url not in home_fields:
            try:
                home_fields[url] = parse_home_field(fetcher.get(url))
            except FetchError as exc:
                log.warning("%s: meeskonna lehte %s ei saanud: %s", NAME, url, exc)
                home_fields[url] = ""
        return home_fields.get(url, "")

    for comp in (source or {}).get("competitions", []):
        for g in parse_list(fetcher.get(league_url(comp["id"]))):
            venue = ""
            if today <= g["start"].date() <= last:
                try:
                    venue = parse_venue(fetcher.get(f"{BASE}/protocol/{g['id']}"))
                except FetchError as exc:
                    log.warning("%s: protokolli %s ei saanud: %s", NAME, g["id"], exc)
                if not venue:
                    venue = home_field(g["home_team_url"])
            events.append(to_event(g, venue, comp["league"], comp.get("level", 1)))
    return events
