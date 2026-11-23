"""Ratsasport: Eesti Ratsaspordi Liidu võistluskalender (ratsanet.ee/events).

robots.txt lubab /events lehte (keelab hobuste, isikute, ostukorvi jms lehed). Leht on serveris renderdatud tabel,
vaikimisi paar nädalat tagasi kuni ~8 kuud ette. Iga rea lauatelefoni lahtrid:
  <tr data-action="click->events#goToEvent" data-events-url-param="/events/4642" …>
    <td class="hide-Desktop">28. - 29. november 2026</td>
    <td class="hide-Desktop">KS, PKS</td>                    ala (lühend)
    <td class="hide-Desktop"><a href="/events/4642?locale=et">Jõuluootus Toomingal</a></td>
    <td class="hide-Desktop">Toominga tall</td>              koht
    <td class="hide-Desktop">EST</td>                        riik
    <td class="hide-Desktop">ABC-RR</td>                     tase (takistuste kõrgus, koolisõidu klass või RV)
    <td class="hide-Desktop"><span …>Registreerimine kuni 25.11.2026</span></td>

Tase lehel:
  - rahvusvahelised (RV, CSI/CDI/CHI/CEI …), Eesti (sise)meistrivõistlused (MV, SMV; linna MV mitte) ja takistussõit kõrgusega ≥ 130 cm
    (Eesti tipptase, Grand Prix sõidud) → 1
  - ülejäänud klubide ja linnade võistlused → 3 (peidetud tase)
Välja jäävad välismaa (riik pole EST) ja tühistatud võistlused.
"""

from __future__ import annotations

import html
import re
from datetime import date, datetime

from .model import Event, new_event

NAME = "ratsasport_ratsanet"
SPORT = "ratsasport"
BASE = "https://ratsanet.ee"
URL = f"{BASE}/events"

DISCIPLINES = {
    "TS": "Takistussõit", "KS": "Koolisõit", "PKS": "Parakoolisõit", "3V": "Kolmevõistlus",
    "KR": "Kestvusratsutamine", "RS": "Rakendisport", "V": "Voltižeerimine",
}
MONTHS = {m: i for i, m in enumerate(
    ["jaanuar", "veebruar", "märts", "aprill", "mai", "juuni", "juuli", "august", "september", "oktoober",
     "november", "detsember"], start=1)}

_ROW = re.compile(r'data-events-url-param="(/events/\d+)"[^\n]*\n(.*?)</tr>', re.S)
_CELL = re.compile(r'<td[^>]*class="hide-Desktop"[^>]*>(.*?)</td>', re.S)
_DAY = re.compile(r"(\d{1,2})\.\s*(?:([a-zõäöü]+)\s+(\d{4}))?", re.I)
_TAGS = re.compile(r"<[^>]+>")

SKIP_STATUS = re.compile(r"tühistatud|ära jäetud", re.I)
INTERNATIONAL = re.compile(r"\bC(?:SI|DI|HI|EI|CI|VI|AI)|\bRV\b", re.I)
CHAMPIONSHIP = re.compile(r"\bS?MV\b|meistrivõistlused", re.I)
LOCAL_CHAMPIONSHIP = re.compile(r"linna|maakonna|klubi", re.I)


def is_national(title: str) -> bool:
    """Eesti (sise)meistrivõistlused: "… / Seenioride, noorte, juunioride ja laste SMV"; "Tartu linna SMV" ei ole."""
    return any(CHAMPIONSHIP.search(part) and not LOCAL_CHAMPIONSHIP.search(part) for part in title.split("/"))


def _text(fragment: str) -> str:
    return " ".join(html.unescape(_TAGS.sub(" ", fragment)).split())


def parse_dates(text: str) -> tuple[date, date | None] | None:
    """"03. - 08. november 2026" / "30. aprill 2027 - 02. mai 2027" / "16. jaanuar 2027" → (algus, lõpp)."""
    parts = _DAY.findall(text)
    if not parts:
        return None
    month = year = None
    days: list[date] = []
    for d, mon, yr in reversed(parts):  # kuu ja aasta on alati lõpus; esimesel päeval võivad puududa
        if mon:
            if mon.lower() not in MONTHS:
                return None
            month, year = MONTHS[mon.lower()], int(yr)
        if month is None:
            return None
        days.insert(0, date(year, month, int(d)))
    start, last = days[0], days[-1]
    if last < start:  # "28. - 03. jaanuar 2027": esimese päeva kuu puudub, see on eelmine kuu
        start = date(last.year - (last.month == 1), last.month - 1 or 12, start.day)
    return start, (last if last > start else None)


def max_height(grade: str) -> int:
    """Takistussõidu kõrgus: "70-140" → 140, "110 - 155" → 155; koolisõidu klass ("ST-M") → 0."""
    nums = [int(n) for n in re.findall(r"\d{2,3}", grade)]
    return max(nums) if nums else 0


def level_of(title: str, grade: str, codes: list[str]) -> int:
    if INTERNATIONAL.search(title) or INTERNATIONAL.search(grade) or is_national(title):
        return 1
    if "TS" in codes and max_height(grade) >= 130:
        return 1
    return 3


def parse(page: str) -> list[Event]:
    events: list[Event] = []
    for path, row in _ROW.findall(page):
        cells = [_text(c) for c in _CELL.findall(row)]
        if len(cells) < 6:
            continue
        when, codes_text, title, place, country, grade = cells[:6]
        status = cells[6] if len(cells) > 6 else ""
        if country != "EST" or SKIP_STATUS.search(status) or not place:
            continue
        dates = parse_dates(when)
        if not dates:
            continue
        start, end = dates
        codes = [c.strip() for c in codes_text.split(",") if c.strip()]
        league = ", ".join(DISCIPLINES.get(c, c) for c in codes) or "Ratsasport"
        events.append(new_event(
            source=NAME, sport=SPORT, league=league, start=datetime(start.year, start.month, start.day),
            home=title, away="", venue=place, city="", url=f"{BASE}{path}",
            time_tbc=True, level=level_of(title, grade, codes), end=end,
        ))
    return events


def fetch(fetcher) -> list[Event]:
    return parse(fetcher.get(URL))
