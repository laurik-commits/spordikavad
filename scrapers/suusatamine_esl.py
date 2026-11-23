"""Suusatamine: Eesti Suusaliidu võistluskalender (suusaliit.ee/et/voistlused).

robots.txt lubab kõike, nõuab Crawl-delay 15 (me teeme ühe päringu päevas). Leht on serveris renderdatud tabel,
vaikimisi tänasest hooaja lõpuni:
  <tr><td class="date"><strong>12.12-13.12</strong></td>
      <td>Murdmaasuusatamine</td>
      <td class="name"><h3><a href="…?competition_id=1381">Vello Liliumi karikavõistlus 2026</a></h3>…</td>
      <td>Alutaguse Tervisespordikeskus, Pannjärve, <span title="Eesti">Eesti</span></td>
      <td><span title="Eesti muud võistlused">EMS</span></td></tr>
Aastat kuupäevas pole: aasta tuletatakse tänasest (hooaeg ületab aastavahetuse).

Alad: murdmaa- ja mäesuusatamine, kahevõistlus, suusahüpped, freestyle ja lumelaud (kõik Suusaliidu all).
Leht on kohapeal vaatamiseks: tavalist murdmaasõitu vaatama ei minda. Tase lehel:
  - rahvusvahelised võistlused Eestis (MK, MM; ka juunioride MM Otepääl) ja Tartu Maraton → 1
  - showalad (suusahüpped, kahevõistlus, freestyle, lumelaud, big air) → 1, nende noortesari → 4 „Noored“
  - ülejäänud (murdmaa Eesti MV, teised maratonid, karikavõistlused, noortesarjad) → 3 (peidetud)
Peidetud võistlused sobiksid tulevasse „võtan osa“ valikusse (vt docs/uued-alad.md).
Välja jäävad laagrid ja „Muu“ (OTHER) ning välismaa võistlused: riigi nimi on kohas („Trysil, Norra“).
"""

from __future__ import annotations

import html
import re
from datetime import date, datetime, timedelta

from .model import Event, new_event

NAME = "suusatamine_esl"
SPORT = "suusatamine"
URL = "https://www.suusaliit.ee/et/voistlused"

_ROW = re.compile(r"<tr>(.*?)</tr>", re.S)
_CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
_LINK = re.compile(r'<a href="([^"]+)"[^>]*>(.*?)</a>', re.S)
_CATEGORY = re.compile(r'<span title="([^"]*)">([^<]*)</span>')
_COUNTRY = re.compile(r'<option label="([^"]+)" value="\d+">')
_WHEN = re.compile(r"(\d{1,2})\.(\d{1,2})(?:\s*-\s*(\d{1,2})\.(\d{1,2}))?")
_TAGS = re.compile(r"<[^>]+>")

TOP_CATEGORIES = {"MK", "MM", "EM"}
YOUTH_CATEGORIES = {"NoSu", "NS"}
SHOW = re.compile(r"hüpped|kahevõistlus|freestyle|lumelaud|big air", re.I)
HIGHLIGHT = re.compile(r"tartu maraton", re.I)
SKIP_CATEGORIES = {"OTHER"}
SKIP = re.compile(r"laager|koolitus|seminar", re.I)
YOUTH_WORDS = re.compile(r"noor|\bU-?\d{2}\b|laste|juunior", re.I)


def _text(fragment: str) -> str:
    return " ".join(html.unescape(_TAGS.sub(" ", fragment)).split())


def level_of(title: str, category: str, discipline: str = "") -> int:
    if category in TOP_CATEGORIES or HIGHLIGHT.search(title):
        return 1
    if SHOW.search(discipline) or SHOW.search(title):
        return 4 if category in YOUTH_CATEGORIES or YOUTH_WORDS.search(title) else 1
    return 3  # murdmaa EMV, maratonid, karikavõistlused, noortesarjad: osalemiseks, mitte vaatamiseks


def _year_for(month: int, day: int, today: date) -> int:
    """Kalendris on tänasest edasi kuni hooaja lõpuni; varasem kuupäev kui ~2 kuud tagasi kuulub järgmisse aastasse."""
    d = date(today.year, month, day)
    return today.year + 1 if d < today - timedelta(days=60) else today.year


def place_of(cell: str) -> tuple[str, list[str]]:
    """"Tehvandi, Otepää, <span title="Eesti">Eesti</span>" → ("Tehvandi, Otepää", ["Eesti"]).
    Riigi nimi võib olla ka tavalise tekstina ("Tehvandi Spordikeskus, Eesti, Eesti", "Tromsö, Norra, Eesti")."""
    countries = _CATEGORY.findall(cell)
    parts = [p.strip() for p in _text(re.sub(r"<span[^>]*>.*?</span>", "", cell)).split(",")]
    return ", ".join(p for p in parts if p and p != "Eesti"), [title for title, _ in countries]


def parse(page: str, today: date | None = None) -> list[Event]:
    today = today or date.today()
    foreign = [c for c in _COUNTRY.findall(page) if c != "Eesti"]
    body = page[page.find("<tbody>"):page.find("</tbody>")]
    events: list[Event] = []
    for row in _ROW.findall(body):
        cells = _CELL.findall(row)
        if len(cells) < 5:
            continue
        when, discipline, name_cell, place_cell, cat_cell = cells[:5]
        link = _LINK.search(name_cell)
        cat = _CATEGORY.search(cat_cell)
        m = _WHEN.search(_text(when))
        if not link or not m:
            continue
        title = _text(link.group(2))
        category, category_name = (cat.group(2).strip(), cat.group(1)) if cat else ("", "")
        place, countries = place_of(place_cell)
        if category in SKIP_CATEGORIES or SKIP.search(title) or not place:
            continue
        if any(c != "Eesti" for c in countries) or any(
                re.search(rf"(^|,)\s*{re.escape(c)}\s*(,|$)", place) for c in foreign):
            continue  # välismaal (riigi nimi on kohas, mõnikord tavalise tekstina ja Eesti lipuga)
        d1, m1, d2, m2 = m.groups()
        y1 = _year_for(int(m1), int(d1), today)
        start = datetime(y1, int(m1), int(d1))
        end = None
        if d2:
            end = date(y1, int(m2), int(d2))
            if end < start.date():
                end = date(y1 + 1, int(m2), int(d2))  # üle aastavahetuse
        level = level_of(title, category, _text(discipline))
        events.append(new_event(
            source=NAME, sport=SPORT, league=_text(discipline) or category_name, start=start,
            home=title, away="", venue=place, city="", url=html.unescape(link.group(1)),
            time_tbc=True, level=level, end=end,
        ))
    return events


def fetch(fetcher) -> list[Event]:
    return parse(fetcher.get(URL))
