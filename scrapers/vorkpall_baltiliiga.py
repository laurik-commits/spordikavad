"""Võrkpall: Elme Messer meeste Balti liiga (DataProject).

Leht: https://bvl-web.dataproject.com/CompetitionMatches.aspx?ID=29&PID=30
ASP.NET leht, iga mäng on plokk, mille elementide id lõpud on püsivad:
LB_DataOra (kuupäev "DD/MM/YYYY - HH:MM"), LB_Palasport (saal),
Label6 (kodumeeskond), Label7 (külalismeeskond). Mängu link: MatchStatistics.aspx?mID=...
Kõik liiga saalid on Ida-Euroopa ajavööndis (EET), sama mis Tallinnas.
"""

from __future__ import annotations

import html
import re
from datetime import datetime

from .model import Event, new_event

NAME = "vorkpall_baltiliiga"
SPORT = "vorkpall"
LEAGUE = "Balti liiga (mehed)"
BASE = "https://bvl-web.dataproject.com/"
URL = BASE + "CompetitionMatches.aspx?ID=29&PID=30"

_ROW_START = re.compile(r'id="[^"]*RADLIST_Matches_ctrl\d+_MatchRow"')


def _field(block: str, suffix: str) -> str:
    m = re.search(r'id="[^"]*RADLIST_Matches_ctrl\d+_' + suffix + r'"[^>]*>(.*?)</span>', block, re.S)
    if not m:
        return ""
    return html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()


def parse(page: str) -> list[Event]:
    starts = [m.start() for m in _ROW_START.finditer(page)] + [len(page)]
    events: list[Event] = []
    for a, b in zip(starts, starts[1:]):
        block = page[a:b]
        when = _field(block, "LB_DataOra")
        # Label6/Label7 on olemas igas plokis, Label2/Label4 ainult osades
        home = _field(block, "Label6") or _field(block, "Label2")
        away = _field(block, "Label7") or _field(block, "Label4")
        mid = re.search(r"MatchStatistics\.aspx\?mID=(\d+)", block)
        dm = re.match(r"(\d{2}/\d{2}/\d{4})(?:\s*-\s*(\d{1,2}:\d{2}))?", when)
        if not (dm and home and away and mid):
            continue  # edasilükatud või määramata mäng
        tbc = dm.group(2) is None
        start = datetime.strptime(f"{dm.group(1)} {dm.group(2) or '00:00'}", "%d/%m/%Y %H:%M")
        events.append(
            new_event(
                source=NAME, sport=SPORT, league=LEAGUE, start=start, home=home, away=away,
                venue=_field(block, "LB_Palasport"), city="",
                url=f"{BASE}MatchStatistics.aspx?mID={mid.group(1)}&ID=29&PID=30", time_tbc=tbc,
            )
        )
    return events


def fetch(fetcher) -> list[Event]:
    return parse(fetcher.get(URL))
