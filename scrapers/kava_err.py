"""Ülekannete kava: ERR telekava (ETV, ETV2).

err.ee telekava leht laeb päeva kava JSON-ina:
  https://www.err.ee/api/tvSchedule/getTimelineSchedule?day=D&month=M&year=Y&channel=etv2
Iga saade: {"name": "Korvpalli MM-valikmäng. Eesti - Prantsusmaa", "startTime": <unix>, "url":
"https://jupiter.err.ee/…", …}. Kava on olemas umbes kaks nädalat ette, loeme DAYS päeva (kanal × päev = päring).
robots.txt: err.ee keelab ainult nimelised robotid (AhrefsBot, GPTBot …), `User-agent: *` gruppi pole.

Spordiülekande tunneb ära nime algusest (ala omastavas: "Korvpalli", "Võrkpalli", "Laskesuusatamise" …).
Pallimängul on pärast esimest punkti "Kodu - Võõras". Ürituse aladel (suusatamine, ralli …) võistkondi pole:
siis home = kogu nimi, away tühi, ja mänguga seotakse nime sõnade järgi (vt ulekanded.match).
See EI OLE mängude allikas: kava ridu ei lisata lehele, need seotakse ainult olemasolevate mängudega.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime, timedelta

from .http import FetchError
from .model import TALLINN

log = logging.getLogger(__name__)

NAME = "kava_err"
BY = "ERR"
CHANNELS = ("etv", "etv2")
DAYS = 8  # täna + 7 päeva
URL = "https://www.err.ee/api/tvSchedule/getTimelineSchedule?day={d}&month={m}&year={y}&channel={ch}"
PAGE = "https://jupiter.err.ee/"

# nime algus → ala (pikemad enne: "saalijalgpall" enne "jalgpall")
_SPORT_START = [
    (r"saalijalgpall", "saalijalgpall"), (r"jalgpall", "jalgpall"), (r"korvpall", "korvpall"),
    (r"võrkpall", "vorkpall"), (r"käsipall", "kasipall"), (r"jäähoki", "jaahoki"), (r"saalihoki", "saalihoki"),
    (r"(laskesuusatamis|murdmaasuusatamis|suusatamis|suusahüpp|kahevõistlus)", "suusatamine"),
    (r"kergejõustik", "kergejoustik"), (r"(iluuisutamis|kiiruisutamis|uisutamis)", "uisutamine"),
    (r"(ralli|rally|wrc)", "autosport"), (r"(motokross|mootorratta)", "motosport"),
    (r"(judo|poksi|maadlus)", "voitlusspordid"), (r"(ratsaspordi|takistussõit)", "ratsasport"),
]
_BALL = {"saalijalgpall", "jalgpall", "korvpall", "vorkpall", "kasipall", "jaahoki", "saalihoki"}


def sport_of(name: str) -> str:
    low = name.strip().lower()
    for pattern, sport in _SPORT_START:
        if re.match(pattern, low):
            return sport
    return ""


def _teams(rest: str) -> tuple[str, str] | None:
    rest = re.sub(r"\s*\((otse|kordus|salvestus)\)\s*$", "", rest.strip(), flags=re.I).rstrip("*").strip()
    for sep in (" - ", " – ", " — "):
        if sep in rest:
            home, away = rest.split(sep, 1)
            if home.strip() and away.strip():
                return home.strip(), away.strip()
    return None


def parse(text: str) -> list[dict]:
    """Ühe päeva kava spordiülekanded: {"start", "sport", "home", "away", "url", "by"}."""
    out = []
    for item in json.loads(text) or []:
        name = (item.get("name") or "").strip()
        sport = sport_of(name)
        if not sport or not item.get("startTime"):
            continue
        if name.rstrip().endswith("*"):
            continue  # tärn = kordus (ERR kava tähistus), otseülekanne see pole
        start = datetime.fromtimestamp(int(item["startTime"]), TALLINN)
        url = (item.get("url") or "").strip()
        url = url if url.startswith("https://") else PAGE
        if sport in _BALL:
            teams = _teams(name.split(". ", 1)[1]) if ". " in name else None
            if not teams:
                continue  # nt "Jalgpalli EM-valiksarja loosimine": mängu pole
            home, away = teams
        else:
            home, away = name, ""
        out.append({"start": start, "sport": sport, "home": home, "away": away, "url": url, "by": BY})
    return out


def fetch(fetcher, today: date | None = None) -> list[dict]:
    today = today or datetime.now(TALLINN).date()
    rows: list[dict] = []
    ok = 0
    for i in range(DAYS):
        d = today + timedelta(days=i)
        for ch in CHANNELS:
            try:
                rows.extend(parse(fetcher.get(URL.format(d=d.day, m=d.month, y=d.year, ch=ch))))
                ok += 1
            except (FetchError, ValueError) as exc:
                log.warning("%s: %s %s kava ei saanud: %s", NAME, ch, d, exc)
    if not ok:
        raise FetchError("ERR telekava: ükski päring ei õnnestunud")
    return rows
