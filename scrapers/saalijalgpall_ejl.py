"""Saalijalgpall (futsal): Eesti Jalgpalli Liidu saalijalgpalli liigad (jalgpall.ee).

Sama süsteem ja kalendrileht mis jalgpallil (vt jalgpall_ejl.py), kaks erinevust:
- hooaeg kestab oktoobrist märtsini ja URL-i `season` on hooaja ALGUSaasta (2026 = 2026/27);
- võistkondade nimede ees on "S. " (nt "S. Tallinna FC Bunker Partner"), see eemaldatakse.
Liigad on config.toml-is (`competitions`), meistriliiga id 125.
"""

from __future__ import annotations

from datetime import date, datetime

from . import jalgpall_ejl
from .model import TALLINN, Event

NAME = "saalijalgpall_ejl"
SPORT = "saalijalgpall"


def season_for(day: date) -> int:
    """Hooaja algusaasta: augustist alates uus hooaeg."""
    return day.year if day.month >= 8 else day.year - 1


def parse(page: str, league: str, level: int = 1) -> list[Event]:
    return jalgpall_ejl.parse(page, league, sport=SPORT, source=NAME, team_prefix="S. ", level=level)


def fetch(fetcher, source: dict | None = None, today: date | None = None) -> list[Event]:
    today = today or datetime.now(TALLINN).date()
    events: list[Event] = []
    for comp in (source or {}).get("competitions", []):
        events.extend(parse(fetcher.get(jalgpall_ejl.url_for(comp["id"], season_for(today))), comp["league"],
                            level=comp.get("level", 1)))
    return events
