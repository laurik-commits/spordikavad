"""Sulgpall: Eesti Sulgpalliliidu võistluskalender (badminton.ee/voistle/kalender/voistluskalender/).

robots.txt lubab (keelatud ainult WooCommerce'i failid ja ostukorv). Leht on serveris renderdatud, iga võistlus plokis
  <div class="calendar_competition …"> … <h4>RSL Estonian Junior 2026</h4>
    <div class="comp_date">10. <span class="triple_dash">---</span> 12.12.2026</div>
    <div class="comp_location"><img …>A.Le Coq spordihoone</div> …
    <div class="comp_buttons"><a href="…/Invitation-RSL-Estonian-Junior-2026.pdf">…Juhend…</a> …
Kuupäev: „05.12.2026“ või „10. --- 12.12.2026“ (üle kuu vahetuse „31. --- 01.11.2026“). Kellaaega pole.
Link: võistluse juhend (PDF), kui see on olemas, muidu kalendri leht.

Tase lehel (kohapeal vaatamiseks):
  - rahvusvahelised täiskasvanute võistlused (International, European … Championships), Eesti MV, klubide karikas → 1
  - täiskasvanute GP-sari (RSL GP-1 …) → 2
  - noorte MV, rahvusvahelised noorteturniirid (Junior, U17, Youth International), noorte klubide karikas → 4
  - muud (noorte GP, YOUNG Eliit, harrastajate paarismängu- ja üksikmänguturniirid) → 3 (peidetud, osalemiseks)
Seenioride võistlused ja edasi lükatud võistlused jäävad välja.
"""

from __future__ import annotations

import html
import re
from datetime import date, datetime

from .model import Event, new_event

NAME = "sulgpall_esl"
SPORT = "sulgpall"
URL = "https://badminton.ee/voistle/kalender/voistluskalender/"

_BLOCK = re.compile(r'<div class="calendar_competition', re.S)
_TITLE = re.compile(r"<h4>(.*?)</h4>", re.S)
_DATE = re.compile(r'<div class="comp_date">(.*?)</div>', re.S)
_PLACE = re.compile(r'<div class="comp_location">(.*?)</div>', re.S)
_GUIDE = re.compile(r'<a href="([^"]+)"[^>]*>(?:(?!</a>).)*?Juhend', re.S)
_TAGS = re.compile(r"<[^>]+>")
_RANGE = re.compile(r"^(\d{1,2})\.(?:(\d{1,2})\.)?\s*(?:-+\s*(\d{1,2})\.(\d{1,2})\.(20\d\d))?$")
_SINGLE = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(20\d\d)$")

SKIP = re.compile(r"edasi lükatud|tühistatud|\bseenior(?!ide ja juunior)|\bsenior\b", re.I)
YOUTH = re.compile(r"noor|junior|juunior|\bU-?\d{2}\b|youth|young", re.I)
YOUTH_TOP = re.compile(r"meistrivõistlus|international|junior\b|klubide karikas", re.I)
TOP = re.compile(r"international|european|championships|meistrivõistlus|klubide karikas", re.I)
SERIES = re.compile(r"\bGP\b|grand prix", re.I)


def _text(fragment: str) -> str:
    return " ".join(html.unescape(_TAGS.sub(" ", fragment)).split())


def dates_of(text: str) -> tuple[date, date | None] | None:
    """„05.12.2026“ → (5.12.2026, None); „10. --- 12.12.2026“ → (10.12, 12.12); „31. --- 01.11.2026“ → (31.10, 1.11)."""
    t = text.replace(" ", "")
    m = _SINGLE.match(t)
    if m:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1))), None
    m = re.match(r"^(\d{1,2})\.(?:(\d{1,2})\.)?-+(\d{1,2})\.(\d{1,2})\.(20\d\d)$", t)
    if not m:
        return None
    d1, m1, d2, m2, y = m.group(1), m.group(2), m.group(3), m.group(4), int(m.group(5))
    end = date(y, int(m2), int(d2))
    month = int(m1) if m1 else (end.month if int(d1) <= int(d2) else (end.month - 2) % 12 + 1)
    start = date(y - (1 if month > end.month else 0), month, int(d1))
    return start, end


def level_of(title: str) -> int:
    if YOUTH.search(title) and not re.search(r"seenioride ja juunioride", title, re.I):
        return 4 if YOUTH_TOP.search(title) else 3
    if re.search(r"seenioride ja juunioride", title, re.I):
        return 4  # juunioride MV (seeniorid samas võistluses)
    if TOP.search(title):
        return 1
    if SERIES.search(title):
        return 2
    return 3


def parse(page: str) -> list[Event]:
    starts = [m.start() for m in _BLOCK.finditer(page)] + [len(page)]
    events: list[Event] = []
    for a, b in zip(starts, starts[1:]):
        block = page[a:b]
        title_m, date_m, place_m = _TITLE.search(block), _DATE.search(block), _PLACE.search(block)
        if not (title_m and date_m and place_m):
            continue
        title, place = _text(title_m.group(1)), _text(place_m.group(1))
        when = dates_of(_text(date_m.group(1)))
        if not title or not when or SKIP.search(title):
            continue
        guide = _GUIDE.search(block)
        start, end = when
        events.append(new_event(
            source=NAME, sport=SPORT, league="Sulgpall", start=datetime(start.year, start.month, start.day),
            home=title, away="", venue=place, city="", url=html.unescape(guide.group(1)).strip() if guide else URL,
            time_tbc=True, level=level_of(title), end=end,
        ))
    return events


def fetch(fetcher) -> list[Event]:
    return parse(fetcher.get(URL))
