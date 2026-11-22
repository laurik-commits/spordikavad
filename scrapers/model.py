"""Ühtne andmemudel, mille iga adapter tagastab."""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

TALLINN = ZoneInfo("Europe/Tallinn")

# tase → nimi valikus, kaust, pealkirja algus, omastav vorm ("tier": "kõrgliigade mänge pole")
LEVELS = {
    1: {"name": "Kõrgliigad", "prefix": "", "title": "Spordimängud", "tier": "kõrgliigade"},
    2: {"name": "Esiliigad", "prefix": "esiliigad/", "title": "Esiliigade mängud", "tier": "esiliigade"},
    3: {"name": "Madalamad liigad", "prefix": "madalamad/", "title": "Madalamate liigade mängud",
        "tier": "madalamate liigade", "hidden": True},  # ajutiselt peidus valikust; lehed ehitatakse edasi
    4: {"name": "Noored", "prefix": "noored/", "title": "Noorte mängud", "tier": "noorteliigade"},
    5: {"name": "Koondised", "prefix": "koondised/", "title": "Koondiste mängud", "tier": "koondiste"},
}

SPORTS = {
    "jalgpall": "Jalgpall",
    "korvpall": "Korvpall",
    "jaahoki": "Jäähoki",
    "vorkpall": "Võrkpall",
    "kasipall": "Käsipall",
    "saalihoki": "Saalihoki",
    "saalijalgpall": "Saalijalgpall",
}


@dataclass(frozen=True)
class Event:
    id: str  # stabiilne räsi (allikas + kuupäev + võistkonnad)
    sport: str  # võti SPORTS sõnastikust
    league: str  # inimloetav liiga nimi
    start: datetime  # ajavööndiga, Europe/Tallinn
    home: str
    away: str
    venue: str  # normaliseeritud saali nimi
    city: str  # "Tallinn"
    url: str  # link allika mängulehele (või liiga kalendrile)
    source: str  # adapteri nimi
    time_tbc: bool = False  # True, kui kellaaeg pole veel kinnitatud
    result: str = ""  # lõppseis "kodu-võõras" (nt "3-0"; jäähokis võib lõpus olla "OT" või "SO"), tühi kuni mäng on mängitud või kui allikas seda ei anna
    level: int = 1 # 1 = kõrgliiga, 2 = esiliiga, 3 = madalamad liigad, 4 = noored, 5 = koondised (igaühel eraldi kalender)

    def __post_init__(self) -> None:
        if self.sport not in SPORTS:
            raise ValueError(f"Tundmatu ala: {self.sport!r}")
        if self.start.tzinfo is None:
            raise ValueError("start peab olema ajavööndiga")

    def to_dict(self) -> dict:
        d = asdict(self)
        d["start"] = self.start.astimezone(TALLINN).isoformat()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Event":
        d = dict(d)
        d["start"] = datetime.fromisoformat(d["start"]).astimezone(TALLINN)
        return cls(**d)


def make_id(source: str, start: datetime, home: str, away: str) -> str:
    """Stabiilne ID: sama mäng saab igal kogumisel sama ID, kui kuupäev ja võistkonnad ei muutu."""
    key = "|".join([source, start.astimezone(TALLINN).date().isoformat(), home.strip().lower(), away.strip().lower()])
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def new_event(
    *,
    source: str,
    sport: str,
    league: str,
    start: datetime,
    home: str,
    away: str,
    venue: str,
    city: str,
    url: str,
    time_tbc: bool = False,
    level: int = 1,
    result: str = "",
) -> Event:
    """Mugav konstruktor adapteritele: arvutab ID ja viib aja Tallinna ajavööndisse."""
    if start.tzinfo is None:
        start = start.replace(tzinfo=TALLINN)
    start = start.astimezone(TALLINN)
    home, away = home.strip(), away.strip()
    return Event(
        id=make_id(source, start, home, away),
        sport=sport,
        league=league,
        start=start,
        home=home,
        away=away,
        venue=venue,
        city=city,
        url=url,
        source=source,
        time_tbc=time_tbc,
        level=level,
        result=result,
    )


_SCORE = re.compile(r"(\d{1,3})\s*[-–:]\s*(\d{1,3})")


def parse_score(text: str) -> str:
    """"3 - 0" → "3-0". Tühi tekst või "-" (mäng pole veel mängitud) → "". """
    m = _SCORE.search(text or "")
    return f"{int(m.group(1))}-{int(m.group(2))}" if m else ""
