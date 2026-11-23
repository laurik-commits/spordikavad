"""Kergejõustik: Eesti Kergejõustikuliidu võistluskalender (ekjl.ee/kalender/).

robots.txt lubab (keelab ainult ühe pluginafaili). Leht on serveris renderdatud, kogu hooaeg ühel lehel, iga
võistlus on kaart:
  <div class="competition-info d-flex-info"><h6 …>Eesti talvised meistrivõistlused 2027</h6>
  <div class="competition-info-date …">20.02.2027 - 21.02.2027</div>   (või "25.11.2026 (11:00)")
  <div class="competition-info-location" …>Lasnamäe Kergejõustikuhall</div>
  <div class="competition-info-location">Kategooria: <a …>D</a></div></div>
Iga kaardi järel on modaalaken kontaktisikutega; neid ei loeta.

Kategooria on World Athletics'i kalendri tase (A–F; GL/GW/OW = tiitlivõistlused välismaal) või "Muu"/"Koolitus".
Tase lehel:
  - noorte võistlused (U14…U23, TV 10 olümpiastart, koolid, lastevõistlused) → 4 „Noored“
  - kategooria A–E või Eesti meistri-/karikavõistlused → 1 (täiskasvanute tippvõistlused)
  - ülejäänud (klubide ja maakondade võistlused) → 3 (peidetud tase)
Välja jäävad koolitused, koosolekud, auhinnagala ja välismaa tiitlivõistlused. Välismaal toimuvatel on koha asemel
linn ("Kaunas", "Valencia"); need jäävad välja geo.foreign kaudu (build.only_estonia).
"""

from __future__ import annotations

import html
import re
from datetime import date, datetime

from .model import Event, new_event

NAME = "kergejoustik_ekjl"
SPORT = "kergejoustik"
URL = "https://www.ekjl.ee/kalender/"

TOP, YOUTH, LOCAL = "Täiskasvanute võistlused", "Noorte võistlused", "Kohalikud võistlused"

_CARD = re.compile(r'<div class="competition-info d-flex-info">(.*?)(?=<div class="modal|<div class="col-|<div class="competition d-flex|<h4>|\Z)', re.S)
_TITLE = re.compile(r"<h6[^>]*>(.*?)</h6>", re.S)
_DATE = re.compile(r'class="competition-info-date[^"]*"[^>]*>(.*?)</div>', re.S)
_PLACE = re.compile(r'class="competition-info-location"[^>]*>(.*?)</div>', re.S)
_CATEGORY = re.compile(r"Kategooria:\s*<a[^>]*>(.*?)</a>", re.S)
_WHEN = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})(?:\s*-\s*(\d{2})\.(\d{2})\.(\d{4}))?(?:\s*\((\d{1,2}):(\d{2})\))?")
_TAGS = re.compile(r"<[^>]+>")

SKIP = re.compile(r"koolitus|koosolek|seminar|auhinnad|kohtunike", re.I)
YOUTH_WORDS = re.compile(r"\bU-?\d{2}\b|noor|\bTV ?10\b|olümpiastart|\bOS\b|laste|kooli|järelkasv|daikin cup", re.I)
NATIONAL = re.compile(r"eesti\b.*(meistri|karika)võistlus", re.I)
TOP_CATEGORIES = {"A", "B", "C", "D", "E"}


def _text(fragment: str) -> str:
    return " ".join(html.unescape(_TAGS.sub(" ", fragment)).split())


def level_of(title: str, category: str) -> int:
    if YOUTH_WORDS.search(title):
        return 4
    if category in TOP_CATEGORIES or NATIONAL.search(title):
        return 1
    return 3


def parse(page: str) -> list[Event]:
    events: list[Event] = []
    for card in _CARD.findall(page):
        title_m, date_m = _TITLE.search(card), _DATE.search(card)
        if not title_m or not date_m:
            continue
        title = _text(title_m.group(1)).rstrip(".")
        when = _WHEN.search(_text(date_m.group(1)))
        cat_m = _CATEGORY.search(card)
        category = _text(cat_m.group(1)) if cat_m else ""
        places = [_text(p) for p in _PLACE.findall(card) if "Kategooria" not in p]
        if not when or SKIP.search(title) or category == "Koolitus" or category[:1] in ("G", "O"):
            continue  # G*/O* = maailma- ja Euroopa tiitlivõistlused, olümpiamängud (välismaal)
        d1, m1, y1, d2, m2, y2, hh, mm = when.groups()
        start = datetime(int(y1), int(m1), int(d1), int(hh or 0), int(mm or 0))
        end = date(int(y2), int(m2), int(d2)) if y2 else None
        level = level_of(title, category)
        events.append(new_event(
            source=NAME, sport=SPORT, league={1: TOP, 4: YOUTH}.get(level, LOCAL), start=start,
            home=title, away="", venue=places[0] if places else "", city="", url=URL,
            time_tbc=hh is None, level=level, end=end,
        ))
    return events


def fetch(fetcher) -> list[Event]:
    return parse(fetcher.get(URL))
