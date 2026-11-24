"""Tennis: Eesti Tennise Liidu võistluskalender (tennis.ee/kalender/).

robots.txt lubab (keelatud ainult /wp-admin/ ja /galerii/). Leht on serveris renderdatud: iga aasta pealkiri
„VÕISTLUSKALENDER 2027“ ja selle all tabel, kuu kaupa read
  <tr><td>02.01</td><td>04.01</td><td>M,N</td><td>Eesti GP</td><td>Tallinn</td><td>Tallink City SK</td></tr>
(algus, lõpp (võib puududa), kategooria, nimi, linn, klubi). Kellaaega pole.

Kategooria: M, N, „M,N“ = täiskasvanud; T/P + vanus (T18, P12, TP14), NL… (noorteliiga) = noored.
Tase lehel (kohapeal vaatamiseks):
  - täiskasvanute MV, Masters ja rahvusvahelised (Open, ITF, WTA, Davis Cup, Billie Jean King Cup) → 1
  - muud täiskasvanute võistlused (Eesti GP, ratastoolitennise GP) → 2
  - noorte MV ja rahvusvahelised noorteturniirid (Tennis Europe „TE14“, ITF) → 4 „Noored“
  - noorte GP ja noorteliiga → 3 (peidetud, osalemiseks; sobiks tulevasse „võtan osa“ valikusse)
Koht: klubi ja linn kujul „Klubi, Linn“ (venues.toml aliased); „ETL“ (liit, koht pole veel teada) → „Linn, koht
täpsustamisel“.
"""

from __future__ import annotations

import html
import re
from dataclasses import replace
from datetime import date, datetime

from .model import Event, make_id, new_event

NAME = "tennis_etl"
SPORT = "tennis"
URL = "https://tennis.ee/kalender/"

_YEAR = re.compile(r"VÕISTLUSKALENDER\s+(20\d\d)", re.I)
_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
_DAY = re.compile(r"^(\d{1,2})\.(\d{1,2})\.?$")
_TAGS = re.compile(r"<[^>]+>")

ADULT = re.compile(r"^(M|N|M,\s*N|MN|N,\s*M)?$")  # tühi kategooria (ratastoolitennis) = täiskasvanud
TOP = re.compile(r"\bMV\b|meistrivõistlus|masters|\bopen\b|\bitf\b|\bwta\b|\batp\b|davis|billie", re.I)
YOUTH_TOP = re.compile(r"\bMV\b|meistrivõistlus|\bTE\s?\d{2}\b|tennis europe|\bitf\b", re.I)
GENDER = {"M": "mehed", "N": "naised", "T": "tüdrukud", "P": "poisid", "TP": "tüdrukud ja poisid"}


def _text(fragment: str) -> str:
    return " ".join(html.unescape(_TAGS.sub(" ", fragment)).split())


def _day(text: str) -> tuple[int, int] | None:
    m = _DAY.match(text.replace("o", "0").replace("O", "0").strip())  # kalendris on trükiviga „3o.01“
    return (int(m.group(1)), int(m.group(2))) if m else None


def league_of(category: str) -> str:
    """„M,N“ → „Tennis: mehed ja naised“, „T18“ → „Tennis: tüdrukud U18“, „NLII“ → „Tennis: noorteliiga“."""
    c = category.replace(" ", "").upper()
    if not c:
        return "Tennis"
    if c.startswith("NL"):
        return "Tennis: noorteliiga"
    if ADULT.match(c):
        return "Tennis: " + " ja ".join(GENDER[g] for g in c.split(",") if g in GENDER) if "," in c else f"Tennis: {GENDER.get(c, c)}"
    m = re.match(r"^(TP|T|P)(\d{2})$", c)
    if m:
        return f"Tennis: {GENDER[m.group(1)]} U{m.group(2)}"
    return f"Tennis: {category}"


def level_of(title: str, category: str) -> int:
    c = category.replace(" ", "").upper()
    if ADULT.match(c):
        return 1 if TOP.search(title) else 2
    return 4 if YOUTH_TOP.search(title) else 3


def venue_of(club: str, city: str) -> str:
    if not club or club.upper() == "ETL":
        return f"{city}, koht täpsustamisel" if city else ""
    return f"{club}, {city}" if city else club


def parse(page: str, today: date | None = None) -> list[Event]:
    marks = [(m.start(), int(m.group(1))) for m in _YEAR.finditer(page)] + [(len(page), 0)]
    events: list[Event] = []
    seen: set[str] = set()
    for (a, year), (b, _) in zip(marks, marks[1:]):
        for row in _ROW.findall(page[a:b]):
            cells = [_text(c) for c in _CELL.findall(row)]
            if len(cells) < 6:
                continue  # kuu pealkiri (<th>) või muu rida
            first, last = _day(cells[0]), _day(cells[1]) if cells[1] else None
            category, title, city, club = cells[2], cells[3], cells[4], cells[5]
            if not first or not title:
                continue
            start = datetime(year, first[1], first[0])
            end = None
            if last:
                end = date(year + (1 if last[1] < first[1] else 0), last[1], last[0])
            venue = venue_of(club, city)
            e = new_event(source=NAME, sport=SPORT, league=league_of(category), start=start, home=title, away="",
                          venue=venue, city="", url=URL, time_tbc=True, level=level_of(title, category), end=end)
            # sama nimega turniire on samal päeval mitu (eri vanuseklassid, linnad): id kategooria ja koha järgi
            e = replace(e, id=make_id(NAME, start, f"{title}|{category}|{venue}", ""))
            if e.id not in seen:
                seen.add(e.id)
                events.append(e)
    return events


def fetch(fetcher) -> list[Event]:
    return parse(fetcher.get(URL))
