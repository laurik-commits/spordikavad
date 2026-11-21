"""Korvpall: Tartu Ülikool Maks & Moorits kodumängud klubi kodulehelt (basket.ut.ee/kalender-26-27/).

Korvpalliliidu lehed (basket.ee, estlatbl.com) keelavad robotid, aga basket.ut.ee on klubi enda WordPressi sait:
robots.txt keelab ainult /wp-admin/ (admin-ajax.php lubatud), crawl-delay'd pole. Leht ei lae andmeid basket.ee-st,
tabelid on serveris renderdatud (TablePress, iga kuu oma tabel).

Rea kuju (veerud AEG | LIIGA | KODU | KÜLALINE | KOHT | TULEMUS):
  <td>L, 24.10.2026, 19.00</td><td>EST-LAT</td><td>TÜ MM</td><td>TalTech/ALEXELA</td><td>TÜ sph</td><td>65:41</td>
Kellaaeg on kirjutatud eri viisil ("19:00", "19.00", "16,00") ja võõrsil mängudel sageli puudub.
Mitmepäevased read ("R-L, 04.-05.09.2026" turniir, "15.02 – 20.02.2027" karikavõistlus) jäävad välja.

Võõrsil mängude KOHT on ainult linn ("Keila", "Riia"), mida ei saa saaliga siduda. Seetõttu võtame ainult
Tartu kodumängud (KODU = "TÜ MM"). Kalevi vastu mängud tulevad ka Kalevi lehelt, topelt eemaldab build.py (dedupe).
"""

from __future__ import annotations

import html
import logging
import re
from datetime import datetime

from .model import Event, new_event

log = logging.getLogger(__name__)

NAME = "korvpall_ut"
SPORT = "korvpall"
URL = "https://basket.ut.ee/kalender-26-27/"

TEAM_SHORT = "TÜ MM"
TEAM = "Tartu Ülikool Maks&Moorits"  # sama kirjapilt mis Kalevi lehel (dedupe)

LEAGUES = {
    "EST-LAT": "Eesti-Läti Korvpalliliiga",
    "FEC": "FIBA Europe Cup",
    "PRESEASON GAME": "Eelhooaja mäng",
}

_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
_TAGS = re.compile(r"<[^>]+>")
# nädalapäev, kuupäev, valikuline kellaaeg; vahemikud ("R-L, 04.-05.09.2026") ei sobi
_WHEN = re.compile(r"^[^\W\d_]+,\s*(\d{1,2})\.(\d{2})\.(\d{4})(?:,\s*(\d{1,2})[:.,](\d{2}))?")


def _text(fragment: str) -> str:
    return " ".join(html.unescape(_TAGS.sub(" ", fragment)).split())


def parse(page: str) -> list[Event]:
    events: list[Event] = []
    for row in _ROW.findall(page):
        cells = [_text(c) for c in _CELL.findall(row)]
        if len(cells) < 5:
            continue
        when = _WHEN.match(cells[0])
        if not when or cells[2] != TEAM_SHORT:
            continue
        day, month, year, hour, minute = when.groups()
        start = datetime(int(year), int(month), int(day), int(hour or 0), int(minute or 0))
        events.append(
            new_event(
                source=NAME, sport=SPORT, league=LEAGUES.get(cells[1], cells[1].title()),
                start=start, home=TEAM, away=cells[3].rstrip("*").strip(),
                venue=cells[4], city="", url=URL, time_tbc=hour is None,
            )
        )
    return events


def fetch(fetcher) -> list[Event]:
    return parse(fetcher.get(URL))
