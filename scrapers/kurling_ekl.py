"""Kurling: Eesti Curlingu Liidu kalender (kurling.ee/kalender/).

robots.txt lubab kõike (Yoasti vaikimisi). Kalender on The Events Calendar (WordPress), mille REST-voog on avalik:
  https://kurling.ee/wp-json/tribe/events/v1/events?per_page=100&start_date=2026-11-19
Kuju: {"events": [{"title": "Eesti meistrivõistlused 2027 naised/mehed", "start_date": "2027-02-01 00:00:00",
  "end_date": "2027-02-07 23:59:59", "all_day": true, "url": "https://kurling.ee/kalender/…/",
  "venue": {"venue": "Tondiraba Jäähall", "city": "Tallinn", "country": "Eesti"}, …}]}
Kellaaega pole (terve päev), mitmepäevasel võistlusel on algus- ja lõpukuupäev.

Lehel on ka välismaa võistlused (koondised: Östersund, Lohja, Genf, …), neil on koha väljal linn ja riik ilma
`country` väljata või teise riigiga: ainult `country == "Eesti"` jääb alles.
Tase lehel:
  - Eesti meistrivõistlused ja maailmakarika (MK) etapid Eestis → 1
  - muud Eestis toimuvad (MM-kvalifikatsioonimängud, turniirid) → 2
"""

from __future__ import annotations

import html
import json
import re
from datetime import date, datetime, timedelta

from .model import TALLINN, Event, new_event

NAME = "kurling_ekl"
SPORT = "kurling"
API = "https://kurling.ee/wp-json/tribe/events/v1/events?per_page=100&start_date={start}"
TOP, OTHER = "Eesti MV ja MK-etapid", "Muud võistlused"

TOP_WORDS = re.compile(r"meistrivõistlus|\bMK\b|maailmakarika", re.I)


def level_of(title: str) -> int:
    return 1 if TOP_WORDS.search(title) else 2


def parse(text: str) -> list[Event]:
    events: list[Event] = []
    for item in (json.loads(text) or {}).get("events", []):
        venue = item.get("venue") or {}
        if not isinstance(venue, dict) or venue.get("country") != "Eesti":
            continue
        title = html.unescape(item.get("title") or "").strip()
        try:
            start = datetime.fromisoformat((item.get("start_date") or "").strip())
            end = datetime.fromisoformat((item.get("end_date") or "").strip()).date()
        except ValueError:
            continue
        if not title or item.get("status", "publish") != "publish":
            continue
        level = level_of(title)
        events.append(new_event(
            source=NAME, sport=SPORT, league=TOP if level == 1 else OTHER, start=start, home=title, away="",
            venue=html.unescape(venue.get("venue") or ""), city="", url=item.get("url") or "https://kurling.ee/kalender/",
            time_tbc=bool(item.get("all_day", True)), level=level, end=end if end > start.date() else None,
        ))
    return events


def fetch(fetcher) -> list[Event]:
    start = (datetime.now(TALLINN).date() - timedelta(days=7)).isoformat()   # käimasolevad võistlused ka
    return parse(fetcher.get(API.format(start=start)))
