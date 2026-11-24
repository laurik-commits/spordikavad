"""Ülekannete kava: Delfi TV (tv.delfi.ee/leht/ulekanded-kava).

Kava leht laeb andmed JSON-ina aadressilt
  https://portal-feeds.api.delfi.ee/portal-feeds-proxy/v1/stream-schedule
Kuju: {"attributes": {"data": {"streams": [{"date": {"start": "2026-11-27T17:00:00Z", ...},
  "title": "Audentes/Solarstone - Barrus Võru VK", "label": "Võrkpall", "url": "", "subscribersOnly": false,
  "hidden": false, ...}]}}}
Umbes kaks nädalat ette, sees on ka saated ("Spordisaade", "Otsesaade"): need jäetakse välja (label pole ala).
robots.txt: api hostil puudub (404), tv.delfi.ee lubab (`User-agent: *`, `Allow: /`). Üks päring päevas.

See EI OLE mängude allikas: kava ridu ei lisata lehele mängudena, need seotakse ainult olemasolevate
mängudega (ala + kellaaeg + võistkonnad, vt ulekanded.match).
"""

from __future__ import annotations

import json
from datetime import datetime

from .model import TALLINN

NAME = "kava_delfi"
BY = "Delfi TV"
URL = "https://portal-feeds.api.delfi.ee/portal-feeds-proxy/v1/stream-schedule"
PAGE = "https://tv.delfi.ee/leht/ulekanded-kava"  # link mängu juures, kui kava real oma linki pole

# kava "label" → ala võti (SPORTS)
SPORTS = {
    "võrkpall": "vorkpall", "korvpall": "korvpall", "käsipall": "kasipall", "jalgpall": "jalgpall",
    "jäähoki": "jaahoki", "hoki": "jaahoki", "saalihoki": "saalihoki", "saalijalgpall": "saalijalgpall",
    "tennis": "tennis", "sulgpall": "sulgpall", "lauatennis": "lauatennis",
}


def _teams(title: str) -> tuple[str, str] | None:
    for sep in (" - ", " – ", " — "):
        if sep in title:
            home, away = title.split(sep, 1)
            if home.strip() and away.strip():
                return home.strip(), away.strip()
    return None


def parse(text: str) -> list[dict]:
    """Kava read, mis on mängud: {"start", "sport", "home", "away", "url", "by"}."""
    data = json.loads(text)
    streams = (((data or {}).get("attributes") or {}).get("data") or {}).get("streams") or []
    out = []
    for s in streams:
        if s.get("hidden"):
            continue
        sport = SPORTS.get((s.get("label") or "").strip().lower())
        teams = _teams(s.get("title") or "")
        start = ((s.get("date") or {}).get("start")) or ""
        if not (sport and teams and start):
            continue
        try:
            when = datetime.fromisoformat(start.replace("Z", "+00:00")).astimezone(TALLINN)
        except ValueError:
            continue
        url = (s.get("url") or "").strip()
        out.append({"start": when, "sport": sport, "home": teams[0], "away": teams[1],
                    "url": url if url.startswith("https://") else PAGE, "by": BY})
    return out


def fetch(fetcher) -> list[dict]:
    return parse(fetcher.get(URL))
