"""Saalijalgpall (futsal): Eesti saalijalgpalli koondised (jalgpall.ee/koondis/<id>/mangud).

Sama leht ja parser mis jalgpall_koondis.py, ainult ala on saalijalgpall (koondise id 14 ja 18).
"""

from __future__ import annotations

from . import jalgpall_koondis
from .model import Event

NAME = "saalijalgpall_koondis"
SPORT = "saalijalgpall"


def parse(page: str, team_name: str) -> list[Event]:
    return jalgpall_koondis.parse(page, team_name, sport=SPORT, source=NAME)


def fetch(fetcher, source: dict | None = None) -> list[Event]:
    events: list[Event] = []
    for comp in (source or {}).get("competitions", []):
        events.extend(parse(fetcher.get(jalgpall_koondis.url_for(comp["id"])), comp["league"]))
    return events
