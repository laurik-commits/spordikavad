"""Võitlusspordid: Eesti Judoliidu tulevased võistlused (judo.ee).

robots.txt lubab (keelab ainult /wp-admin/). Igal lehel on külgribal „Upcoming events“ nimekiri:
  <li><a href="https://judo.ee/event/zen-jouluturniir-6/" title="Zen Jõuluturniir">
      <span class="post_date">05 Dec</span><span class="event_text">Zen Jõuluturniir</span>
      <span class="post_location">A. Le Coq Spordihoone</span></a></li>
Aastat pole: tuletatakse tänasest. Mitmepäevasel on ainult alguspäev (lehel vaatamiseks piisab).
Täielik kalender on PDF-is ja ürituste lehtedel; järgmise aasta üritused lisab liit tavaliselt alles veebruaris,
nii et külgribast piisab lähinädalate jaoks.

Leht on kohapeal vaatamiseks. Tase:
  - rahvusvahelised (European Open, European Cup, Baltic …) ja täiskasvanute Eesti meistrivõistlused → 1
  - noorte meistrivõistlused (U14, U16, U18, U21) → 4
  - klubide turniirid ja karikasarja etapid → 3 (peidetud)
Laagrid, eksamid, koolitused, judopäevad ja veteranide võistlused välismaal jäävad välja.
"""

from __future__ import annotations

import html
import re
from datetime import date, datetime, timedelta

from .model import Event, new_event

NAME = "voitlusspordid_judo"
SPORT = "voitlusspordid"
URL = "https://judo.ee/voistlused/"

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}

_BLOCK = re.compile(r"Upcoming events.*?<ul>(.*?)</ul>", re.S)
_ITEM = re.compile(r'<a href="([^"]+)"[^>]*>\s*<span class="post_date">([^<]*)</span>\s*'
                   r'<span class="event_text">([^<]*)</span>\s*<span class="post_location">([^<]*)</span>', re.S)
_DAY = re.compile(r"(\d{1,2})\s+([A-Za-z]{3})")

SKIP = re.compile(r"laager|camp|eksam|koolitus|seminar|judopäev|treening|veteranide (maailma|euroopa)", re.I)
YOUTH = re.compile(r"\bU-?\d{2}\b|noorte|kadett|laste", re.I)
INTERNATIONAL = re.compile(r"european|open|baltic|international|rahvusvaheline", re.I)
NATIONAL = re.compile(r"eesti meistrivõistlused", re.I)


def level_of(title: str) -> int:
    if YOUTH.search(title):
        return 4
    if INTERNATIONAL.search(title) or NATIONAL.search(title):
        return 1
    return 3


def _date(text: str, today: date) -> date | None:
    m = _DAY.search(text)
    if not m or m.group(2).lower() not in MONTHS:
        return None
    month, day = MONTHS[m.group(2).lower()], int(m.group(1))
    d = date(today.year, month, day)
    return date(today.year + 1, month, day) if d < today - timedelta(days=60) else d


def parse(page: str, today: date | None = None) -> list[Event]:
    today = today or date.today()
    block = _BLOCK.search(page)
    events: list[Event] = []
    for url, when, title, place in _ITEM.findall(block.group(1) if block else ""):
        title, place = html.unescape(title).strip(), html.unescape(place).strip()
        d = _date(when, today)
        if not d or SKIP.search(title):
            continue
        events.append(new_event(
            source=NAME, sport=SPORT, league="Judo", start=datetime(d.year, d.month, d.day),
            home=title, away="", venue=place, city="", url=url, time_tbc=True, level=level_of(title),
        ))
    return events


def fetch(fetcher) -> list[Event]:
    page = fetcher.get(URL)
    if "Upcoming events" not in page:
        raise ValueError("judo.ee külgriba „Upcoming events“ puudub (lehe ülesehitus muutunud?)")
    return parse(page)
