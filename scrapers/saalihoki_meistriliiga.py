"""Saalihoki: meeste Meistriliiga ja Eesti-Läti ühisliigad (saalihoki.ee).

Leht https://saalihoki.ee/Ajakavad.aspx on kõigi liigade tulevaste mängude tabel:
"Millal" (DD.MM.YYYY HH:MM), "Üritus" (liiga eesliide + "Kodu - Külalised", link
Uritus.aspx?id=N) ja "Koht". Võetakse ainult LEAGUES sõnastikus olevad liigad.
"""

from __future__ import annotations

import html
import re
from datetime import datetime

from .model import Event, new_event

NAME = "saalihoki_meistriliiga"
SPORT = "saalihoki"
# saalihoki.ee/Ajakavad.aspx suunab siia; lehe suhtelised lingid (Uritus.aspx?id=N)
# kehtivad /Events/ kausta suhtes.
BASE = "https://www.saalihoki.ee/Events/"
URL = BASE + "Uritused.aspx"

# eesliide lehel → (liiga nimi meie lehel, tase: 1 = kõrgliiga, 2 = esiliiga)
LEAGUES = {
    "Meistriliiga M": ("Meistriliiga (mehed)", 1),
    "LAT-EST M": ("Eesti-Läti liiga (mehed)", 1),
    "LAT-EST N": ("Eesti-Läti liiga (naised)", 1),
    "Energialiiga": ("Energialiiga", 2),
}

_ROW = re.compile(
    r'<td class="center"[^>]*>\s*(\d{2}\.\d{2}\.\d{4})[\s&nbsp;]*(\d{1,2}:\d{2})?\s*</td>'
    r'<td>\s*<a [^>]*href="Uritus\.aspx\?id=(\d+)">([^<]*)</a>\s*</td><td[^>]*>([^<]*)</td>'
)


def _split_teams(text: str) -> tuple[str, str] | None:
    parts = text.split(" - ")
    if len(parts) != 2:
        parts = re.split(r"(?<=\S)- ", text, maxsplit=1)  # nt "Jõgeva SK Tähe/Olivia- FBK SĀC"
    if len(parts) != 2:
        return None
    home, away = (p.strip() for p in parts)
    return (home, away) if home and away else None


def parse(page: str) -> list[Event]:
    events: list[Event] = []
    for day, time, uid, title, place in _ROW.findall(page):
        title = html.unescape(title).strip()
        prefix = next((p for p in LEAGUES if title.startswith(p + " ")), None)
        if prefix is None:
            continue
        teams = _split_teams(title[len(prefix):].strip())
        if teams is None:
            continue
        league, level = LEAGUES[prefix]
        events.append(
            new_event(
                source=NAME, sport=SPORT, league=league, level=level,
                start=datetime.strptime(f"{day} {time or '00:00'}", "%d.%m.%Y %H:%M"),
                home=teams[0], away=teams[1], venue=html.unescape(place).strip(), city="",
                url=f"{BASE}Uritus.aspx?id={uid}", time_tbc=not time,
            )
        )
    return events


def fetch(fetcher) -> list[Event]:
    return parse(fetcher.get(URL))
