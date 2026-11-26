"""Ujumine: Eesti Ujumisliidu kalender (swimming.ee/kalender/).

robots.txt lubab kõike. Kalender on WordPressi arhiiv; nimekirjavaade `?view=list` annab vaikimisi 16 rida, saidi enda
JavaScript küsib järgmisi lehti parameetritega `swimming_ajax=1&swimming_ppp=N`, nii saab kogu tuleviku ühe päringuga:
  <div class="events-archive__row">
    <span class="… cell--date">28.11.2026 – 30.11.2026</span>
    <span class="… cell--name"><a class="events-archive__row-link" href="…">Nimi</a></span>
    <span class="… cell--location">Tartu, Aura Veekeskus</span>
Kellaaega pole. Ala (basseini-, avavee-, kujundujumine, masters, veepall) real puudub, kõik on „ujumine“.
Nimekirjas on ka koolitused ja välismaa võistlused (koha asemel linn või riik; need jäävad välja geo.foreign kaudu)
ning sama võistlus mõnikord kahel real (erinev koha kirjapilt); duplikaadid liidetakse.

Tase lehel:
  - Eesti meistrivõistlused (ka masters/Supermasters) → 1
  - lahtised võistlused, karikad ja suuremad sarjad (Open, Cup, karikavõistlus) → 2
  - noorte ja laste sarjad (Räimeralli, Kilpkonna Cup, Päkapikuvõistlus, koolinoored) → 4 „Noored“
  - klubide jõulu-, kontroll- ja talvevõistlused ning maakonna MV → 3 (peidetud)
"""

from __future__ import annotations

import html
import re
from datetime import date, datetime

from .model import Event, new_event

NAME = "ujumine_eul"
SPORT = "ujumine"
URL = "https://swimming.ee/kalender/"
LIST_URL = URL + "?view=list&swimming_ajax=1&swimming_ppp=300"

TOP, OPEN, YOUTH, LOCAL = "Eesti MV", "Lahtised võistlused ja karikad", "Noorte võistlused", "Klubide võistlused"

_ROW = re.compile(
    r'cell--date"[^>]*>\s*(.*?)\s*</span>.*?events-archive__row-link" href="([^"]+)">\s*(.*?)\s*</a>'
    r'.*?cell--location"[^>]*>(.*?)</span>', re.S)
_DAY = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")
_TAGS = re.compile(r"<[^>]+>")

SKIP = re.compile(r"koolitus|õpime ujuma|veeohutus|seminar|kursus|kohtunik|koosolek|infopäev", re.I)
YOUTH_WORDS = re.compile(r"\bU-?\d{2}\b|noor|laste|koolinoor|kilpkonna|pardike|päkapiku|ujumistähed|räimeralli", re.I)
NATIONAL = re.compile(r"\beesti\b.*meistrivõistlus|\bEMV\b|supermasters", re.I)
LOCAL_MV = re.compile(r"maakonna|\btartumaa\b|linna|\bMV\b", re.I)
OPEN_WORDS = re.compile(r"\bopen\b|\bcup\b|karikavõistlus|mitmevõistlus", re.I)


def _text(fragment: str) -> str:
    return " ".join(html.unescape(_TAGS.sub(" ", fragment)).split())


def level_of(title: str) -> int:
    if YOUTH_WORDS.search(title):
        return 4
    if NATIONAL.search(title):
        return 1
    if LOCAL_MV.search(title) and not OPEN_WORDS.search(title):
        return 3
    if OPEN_WORDS.search(title):
        return 2
    return 3


def _key(title: str) -> str:
    return re.sub(r"\W+", " ", re.sub(r"\b20\d\d\b", "", title.lower())).strip()


def parse(page: str) -> list[Event]:
    best: dict[tuple, Event] = {}
    for raw_date, link, raw_title, raw_place in _ROW.findall(page):
        title = _text(raw_title)
        days = _DAY.findall(raw_date)
        if not days or SKIP.search(title):
            continue
        d = [date(int(y), int(m), int(dd)) for dd, m, y in days]
        start, end = d[0], (d[-1] if d[-1] > d[0] else None)
        place = _text(raw_place)
        level = level_of(title)
        ev = new_event(
            source=NAME, sport=SPORT, league={1: TOP, 2: OPEN, 4: YOUTH}.get(level, LOCAL),
            start=datetime(start.year, start.month, start.day), home=title, away="", venue=place, city="",
            url=html.unescape(link), time_tbc=True, level=level, end=end,
        )
        key = (start, end, _key(title))
        if key not in best or len(place) > len(best[key].venue):
            best[key] = ev
    return sorted(best.values(), key=lambda e: e.start)


def fetch(fetcher) -> list[Event]:
    return parse(fetcher.get(LIST_URL))
