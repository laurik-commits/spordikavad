"""Uisutamine: Eesti Uisuliidu iluuisutamise kalenderplaan (uisuliit.ee).

robots.txt lubab (keelab /files/ ja /admin/). Hooaja kalender on serveris renderdatud tabel:
  <tr><td>16.-22.11.2026</td><td><a …>ISU Challenger seeria võistlus Tallinn Trophy 2026</a></td>
      <td>Tondiraba jäähall</td><td>Tallinna Uisuklubide Liit …</td>
      <td><b>ISU kalenderplaani võistlus</b> : Seenorid, juuniorid: …</td></tr>
Kuupäev: "11.-12.08.2026", "30.10-01.11.2026", "05.12.2026" või "TBA" (siis jääb välja).
Lehe aadressis on hooaeg ("eul-kalenderplaan-2026-2027"): uut hooaega otsitakse iluuisutamise võistluste lehelt.

Leht on kohapeal vaatamiseks. Tase:
  - ISU kalenderplaani võistlused (Tallinn Trophy, Tallinn Open, Lõunakeskus Trophy …) ja Eesti meistrivõistlused → 1
  - noorte MV, juunioride karikas, Kids/Novice võistlused → 4 „Noored“
  - klubide Interclub-võistlused → 3 (peidetud)
Katsevõistlused ja kontrollstardid jäävad välja. Kiiruisutamise kalendris on ainult Härma ovaali väikesed
võistlused ja eelmine hooaeg, seda ei loeta.
"""

from __future__ import annotations

import html
import re
from datetime import date, datetime

from .model import Event, new_event

NAME = "uisutamine_eul"
SPORT = "uisutamine"
BASE = "https://www.uisuliit.ee"
INDEX = f"{BASE}/iluuisutamine/voistlused"

_SEASON_LINK = re.compile(r'href="(/iluuisutamine/voistlused/eul-kalenderplaan-(\d{4})-(\d{4}))"')
_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
_WHEN = re.compile(r"(\d{1,2})\.(?:(\d{1,2})\.?)?\s*-\s*(\d{1,2})\.(\d{1,2})\.(\d{4})|(\d{1,2})\.(\d{1,2})\.(\d{4})")
_LINK = re.compile(r"<a[^>]*>(.*?)</a>", re.S)
_TAGS = re.compile(r"<[^>]+>")

SKIP = re.compile(r"katsevõistlus|kontrollstart", re.I)
YOUTH = re.compile(r"noorte|juunioride|\bkids\b|novice", re.I)
NATIONAL = re.compile(r"eesti meistrivõistlused", re.I)
INTERNATIONAL = re.compile(r"ISU kalenderplaan|challenger", re.I)


def _text(fragment: str) -> str:
    return " ".join(html.unescape(_TAGS.sub(" ", fragment)).split())


def level_of(title: str, category: str) -> int:
    if YOUTH.search(title):
        return 4
    if INTERNATIONAL.search(category) or INTERNATIONAL.search(title) or NATIONAL.search(title):
        return 1
    return 3


def parse_dates(text: str) -> tuple[date, date | None] | None:
    """"11.-12.08.2026" / "30.10-01.11.2026" / "05.12.2026" → (algus, lõpp)."""
    m = _WHEN.search(text)
    if not m:
        return None
    d1, m1, d2, m2, y, sd, sm, sy = m.groups()
    if sd:
        return date(int(sy), int(sm), int(sd)), None
    last = date(int(y), int(m2), int(d2))
    month = int(m1 or m2)
    start = date(int(y) - (month > last.month), month, int(d1))  # "28.12-02.01.2027": algus eelmisel aastal
    return start, (last if last > start else None)


def parse(page: str, url: str = INDEX) -> list[Event]:
    events: list[Event] = []
    table = page[page.find("<table"):page.find("</table>")]
    for row in _ROW.findall(table):
        cells = _CELL.findall(row)
        if len(cells) < 3:
            continue
        when, place = _text(cells[0]), _text(cells[2])
        link = _LINK.search(cells[1])  # mitu linki ühes lahtris ("… Cup 2027 … Cup Interclub"): esimene on nimi
        title = _text(link.group(1)) if link else _text(cells[1])
        category = _text(cells[4]) if len(cells) > 4 else ""
        dates = parse_dates(when)
        if not dates or not title or SKIP.search(title):
            continue
        start, end = dates
        level = level_of(title, category)
        events.append(new_event(
            source=NAME, sport=SPORT, league="Iluuisutamine", start=datetime(start.year, start.month, start.day),
            home=title, away="", venue=place, city="", url=url, time_tbc=True, level=level, end=end,
        ))
    return events


def season_url(index_page: str) -> str:
    """Uusim kalenderplaani leht iluuisutamise võistluste lehelt (hooaeg on aadressis)."""
    links = sorted(set(_SEASON_LINK.findall(index_page)), key=lambda x: int(x[1]))
    return f"{BASE}{links[-1][0]}" if links else ""


def fetch(fetcher) -> list[Event]:
    url = season_url(fetcher.get(INDEX))
    if not url:
        raise ValueError("Iluuisutamise kalenderplaani linki ei leitud (lehe ülesehitus muutunud?)")
    return parse(fetcher.get(url), url)
