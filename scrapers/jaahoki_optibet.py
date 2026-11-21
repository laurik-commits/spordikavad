"""Jäähoki: Optibet Hokiliiga (lhf.lv).

Leht: https://www.lhf.lv/en/tournaments/optibet-hokeja-liga/schedule
Lehel on kogu hooaja tabel. Iga rida sisaldab täisnimesid, kohta, aega
(data-order="YYYYMMDDHHMMSS") ja mängukeskuse linki. Kinnitamata ajaga mängudel
on kellaosa 000000 ja tekst "TBA".
"""

from __future__ import annotations

import html
import re
from datetime import datetime

from .model import Event, new_event, parse_score

NAME = "jaahoki_optibet"
SPORT = "jaahoki"
LEAGUE = "Optibet Hokiliiga"
BASE = "https://www.lhf.lv"
URL = BASE + "/en/tournaments/optibet-hokeja-liga/schedule"

_ROW = re.compile(r"<tr>(.*?)</tr>", re.S)
_TEAM = re.compile(
    r'<td class="desktop" data-order="[^"]*"><div class="team"><div class="image">.*?</div>([^<]+)</div></td>', re.S
)
_VENUE = re.compile(r'<td class="ta-l desktop" data-order="([^"]*)"')
_WHEN = re.compile(r'<td class="desktop" data-order="(\d{14})"')
# tulemuse lahter on enne tegevusnuppude lahtrit: "5:2", pikendusega "4:5 OT", karistusviskedega "2:3 SO"; mängimata: tühi
_SCORE = re.compile(r'<td>\s*([^<]*?)\s*</td>\s*<td class="ta-r">')
_OVERTIME = re.compile(r"\b(OT|SO)\b")
_LINK = re.compile(r'href="(/en/tournaments/[^"]+/schedule/[^"]+)"')


def parse(page: str) -> list[Event]:
    events: list[Event] = []
    for row in _ROW.findall(page):
        teams = _TEAM.findall(row)
        when = _WHEN.search(row)
        link = _LINK.search(row)
        if len(teams) != 2 or not when or not link:
            continue  # päise- või muu tabeli rida
        stamp = when.group(1)
        tbc = stamp.endswith("000000") and "TBA" in row
        venue = _VENUE.search(row)
        cell = _SCORE.search(row)
        result = parse_score(cell.group(1)) if cell else ""
        if result and (ot := _OVERTIME.search(cell.group(1))):
            result += f" {ot.group(1)}"
        events.append(
            new_event(
                source=NAME,
                sport=SPORT,
                league=LEAGUE,
                start=datetime.strptime(stamp, "%Y%m%d%H%M%S"),
                home=html.unescape(teams[0]),
                away=html.unescape(teams[1]),
                venue=html.unescape(venue.group(1)).strip() if venue else "",
                city="",
                url=BASE + html.unescape(link.group(1)),
                time_tbc=tbc,
                result=result,
            )
        )
    return events


def fetch(fetcher) -> list[Event]:
    return parse(fetcher.get(URL))
