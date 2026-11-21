"""Võrkpall: kõik DataProjecti süsteemis olevad võistlused (Balti liiga, Eesti meistriliigad, karikad).

Võistluste nimekiri on config.toml-is (`competitions`), sest DataProjecti ID-d muutuvad igal hooajal:
    competitions = [{ host = "bvl-web", id = 29, pid = 30, league = "Balti liiga (mehed)" }, ...]

Leht https://<host>.dataproject.com/CompetitionMatches.aspx?ID=..&PID=.. on ASP.NET leht, iga mäng
on plokk, mille elementide id lõpud on püsivad: LB_DataOra (kuupäev "DD/MM/YYYY - HH:MM"),
LB_Palasport (saal), Label6 (kodumeeskond), Label7 (külalismeeskond). Mängu link:
MatchStatistics.aspx?mID=... Kõik saalid on Ida-Euroopa ajavööndis (EET), sama mis Tallinnas.
"""

from __future__ import annotations

import html
import re
from datetime import datetime

from .model import Event, new_event

NAME = "vorkpall_dataproject"
SPORT = "vorkpall"

_ROW_START = re.compile(r'id="[^"]*RADLIST_Matches_ctrl\d+_MatchRow"')


def base_url(comp: dict) -> str:
    return f"https://{comp['host']}.dataproject.com/"


def comp_query(comp: dict) -> str:
    return f"ID={comp['id']}" + (f"&PID={comp['pid']}" if comp.get("pid") else "")


def matches_url(comp: dict) -> str:
    return f"{base_url(comp)}CompetitionMatches.aspx?{comp_query(comp)}"


def _field(block: str, suffix: str) -> str:
    m = re.search(r'id="[^"]*RADLIST_Matches_ctrl\d+_' + suffix + r'"[^>]*>(.*?)</span>', block, re.S)
    if not m:
        return ""
    return html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()


def _hidden(block: str, suffix: str) -> str:
    m = re.search(r'RADLIST_Matches_ctrl\d+_' + suffix + r'"[^>]*\svalue="([^"]*)"', block)
    return m.group(1).strip() if m else ""


def _result(block: str) -> str:
    """Võidetud setid "kodu-võõras" (nt "3-1"). Mängimata mängul on mõlemad 0 või puuduvad: tulemus tühi."""
    home, guest = _hidden(block, "HF_WonSetHome"), _hidden(block, "HF_WonSetGuest")
    if home.isdigit() and guest.isdigit() and int(home) + int(guest) > 0:
        return f"{int(home)}-{int(guest)}"
    return ""


def parse(page: str, comp: dict) -> list[Event]:
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
        start = datetime.strptime(f"{dm.group(1)} {dm.group(2) or '00:00'}", "%d/%m/%Y %H:%M")
        events.append(
            new_event(
                source=NAME, sport=SPORT, league=comp["league"], start=start, home=home, away=away,
                venue=_field(block, "LB_Palasport"), city="",
                url=f"{base_url(comp)}MatchStatistics.aspx?mID={mid.group(1)}&{comp_query(comp)}",
                time_tbc=dm.group(2) is None, level=comp.get("level", 1), result=_result(block),
            )
        )
    return events


def fetch(fetcher, source: dict | None = None) -> list[Event]:
    events: list[Event] = []
    for comp in (source or {}).get("competitions", []):
        events.extend(parse(fetcher.get(matches_url(comp)), comp))
    return events
