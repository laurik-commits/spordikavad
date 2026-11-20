"""Ühtne andmemudel, mille iga adapter tagastab."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

TALLINN = ZoneInfo("Europe/Tallinn")

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
    )
